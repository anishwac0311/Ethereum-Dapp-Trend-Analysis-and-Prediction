import { useMemo, useState } from 'react'
import { fmtNum } from '../api'

type Rel = { from: string; to: string; on?: string; label?: string }

type NodeDef = {
  id: string
  dataset: 'v1' | 'v2'
  table: string
  internal?: boolean
  col: number
  row: number
}

type Node = NodeDef & { x: number; y: number; rows?: number; description?: string }

const STAGES = [
  'Registry',
  'Discovery',
  'Contract map',
  'Wallet activity',
  'Static',
  'Panel',
  'Derived (v2)',
]

// Lane 'v1' has one row; lane 'v2' has four.
const LAYOUT: NodeDef[] = [
  { id: 'v1.protocols', dataset: 'v1', table: 'protocols', col: 0, row: 0 },
  { id: 'v1.contract_map', dataset: 'v1', table: 'contract_map', col: 2, row: 0 },
  { id: 'v1.activity', dataset: 'v1', table: 'activity', col: 3, row: 0 },
  { id: 'v1.dapp_static', dataset: 'v1', table: 'dapp_static', col: 4, row: 0 },
  { id: 'v1.dapp_panel', dataset: 'v1', table: 'dapp_panel', col: 5, row: 0 },

  { id: 'v2.protocols', dataset: 'v2', table: 'protocols', col: 0, row: 1 },
  { id: 'v2.discovered_raw', dataset: 'v2', table: 'discovered_raw', col: 1, row: 1 },
  { id: 'v2.contract_conflicts', dataset: 'v2', table: 'contract_conflicts', col: 1, row: 2 },
  { id: 'v2.app_contracts', dataset: 'v2', table: 'app_contracts', col: 2, row: 1 },
  { id: 'wallet_month_v2', dataset: 'v2', table: 'wallet_month_v2', internal: true, col: 3, row: 2 },
  { id: 'heavy_wallets', dataset: 'v2', table: 'heavy_wallets', internal: true, col: 3, row: 3 },
  { id: 'wallet_first_seen', dataset: 'v2', table: 'wallet_first_seen', internal: true, col: 3, row: 4 },
  { id: 'v2.dapp_static', dataset: 'v2', table: 'dapp_static', col: 4, row: 1 },
  { id: 'v2.dapp_panel', dataset: 'v2', table: 'dapp_panel', col: 5, row: 1 },
  { id: 'v2.dapp_lifecycle', dataset: 'v2', table: 'dapp_lifecycle', col: 6, row: 1 },
  { id: 'v2.concentration_month', dataset: 'v2', table: 'concentration_month', col: 6, row: 2 },
  { id: 'v2.category_month', dataset: 'v2', table: 'category_month', col: 6, row: 3 },
  { id: 'v2.cohort_retention', dataset: 'v2', table: 'cohort_retention', col: 6, row: 4 },
]

const NODE_W = 150
const NODE_H = 46
const COL_W = 196
const LEFT = 64
const HEADER_H = 40
const ROW_Y = [HEADER_H + 56, HEADER_H + 196, HEADER_H + 270, HEADER_H + 344, HEADER_H + 418]
const WIDTH = LEFT + STAGES.length * COL_W
const HEIGHT = ROW_Y[4] + NODE_H + 24

const STYLE = {
  v1: { fill: '#3a1f05', stroke: '#f59e0b' },
  v2: { fill: '#053d2e', stroke: '#34d399' },
  internal: { fill: '#1e1b4b', stroke: '#818cf8' },
}

function edgePath(a: Node, b: Node, occupied: Set<string>) {
  const ax = a.x, ay = a.y, bx = b.x, by = b.y
  if (a.col === b.col) {
    // Same column: straight down when adjacent, otherwise bracket out to the left
    if (Math.abs(a.row - b.row) === 1) {
      const x = ax + NODE_W / 2
      return { d: `M${x},${ay + NODE_H} L${x},${by}`, lx: x + 6, ly: (ay + NODE_H + by) / 2 }
    }
    const sy = ay + NODE_H / 2, ty = by + NODE_H / 2, x = ax
    return {
      d: `M${x},${sy} C${x - 36},${sy} ${x - 36},${ty} ${x},${ty}`,
      lx: x - 40, ly: (sy + ty) / 2,
    }
  }
  const blocked = a.row === b.row &&
    Array.from({ length: b.col - a.col - 1 }, (_, i) => a.col + i + 1)
      .some(c => occupied.has(`${c}:${a.row}`))
  if (blocked) {
    // Arc over the nodes in between
    const sx = ax + NODE_W / 2, tx = bx + NODE_W / 2, y = ay
    const lift = 26 + 10 * (b.col - a.col)
    return {
      d: `M${sx},${y} C${sx},${y - lift} ${tx},${y - lift} ${tx},${y}`,
      lx: (sx + tx) / 2, ly: y - lift * 0.75,
    }
  }
  const sx = ax + NODE_W, sy = ay + NODE_H / 2, tx = bx, ty = by + NODE_H / 2
  const dx = Math.max(40, (tx - sx) / 2)
  return {
    d: `M${sx},${sy} C${sx + dx},${sy} ${tx - dx},${ty} ${tx},${ty}`,
    lx: (sx + tx) / 2, ly: (sy + ty) / 2,
  }
}

export function ErDiagram({ relationships, tables, internalTables, selectedId, onSelect }: {
  relationships: Rel[]
  tables: any[]
  internalTables: Record<string, { description: string }>
  selectedId?: string
  onSelect: (dataset: string, table: string) => void
}) {
  const [hover, setHover] = useState<string | null>(null)
  const focus = hover

  const { nodes, byId, occupied } = useMemo(() => {
    const rowsByKey = Object.fromEntries(tables.map((t: any) => [`${t.dataset}.${t.table}`, t]))
    const nodes: Node[] = LAYOUT.map(n => {
      const t = rowsByKey[n.id]
      return {
        ...n,
        x: LEFT + n.col * COL_W + (COL_W - NODE_W) / 2,
        y: ROW_Y[n.row],
        rows: t?.rows,
        description: n.internal ? internalTables?.[n.id]?.description : t?.description,
      }
    })
    return {
      nodes,
      byId: Object.fromEntries(nodes.map(n => [n.id, n])),
      occupied: new Set(nodes.map(n => `${n.col}:${n.row}`)),
    }
  }, [tables, internalTables])

  const edges = relationships
    .map(r => ({ r, a: byId[r.from], b: byId[r.to] }))
    .filter(e => e.a && e.b)
    .map(e => ({ ...e, ...edgePath(e.a, e.b, occupied) }))

  const linked = new Set<string>()
  if (focus) {
    linked.add(focus)
    for (const e of edges) {
      if (e.r.from === focus) linked.add(e.r.to)
      if (e.r.to === focus) linked.add(e.r.from)
    }
  }

  const focusNode = focus ? byId[focus] : null
  const focusEdges = focus ? edges.filter(e => e.r.from === focus || e.r.to === focus) : []

  return (
    <div>
      <div style={{ overflowX: 'auto' }}>
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{ width: '100%', minWidth: 1000, display: 'block' }}>
          <defs>
            <marker id="er-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill="#64748b" />
            </marker>
            <marker id="er-arrow-hi" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill="#38bdf8" />
            </marker>
          </defs>

          {STAGES.map((s, i) => (
            <g key={s}>
              {i > 0 && (
                <line x1={LEFT + i * COL_W} y1={HEADER_H - 8} x2={LEFT + i * COL_W} y2={HEIGHT - 8}
                  stroke="#1a2438" strokeDasharray="3 5" />
              )}
              <text x={LEFT + i * COL_W + COL_W / 2} y={22} fill="#64748b" fontSize={11}
                fontWeight={600} textAnchor="middle" style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {s}
              </text>
            </g>
          ))}

          <rect x={8} y={ROW_Y[0] - 34} width={WIDTH - 16} height={NODE_H + 52} rx={12}
            fill="rgba(245,158,11,0.04)" stroke="rgba(245,158,11,0.18)" />
          <rect x={8} y={ROW_Y[1] - 36} width={WIDTH - 16} height={ROW_Y[4] - ROW_Y[1] + NODE_H + 48} rx={12}
            fill="rgba(52,211,153,0.035)" stroke="rgba(52,211,153,0.16)" />
          <text x={36} y={ROW_Y[0] + NODE_H / 2 + 5} fill="#f59e0b" fontSize={14} fontWeight={700} textAnchor="middle">v1</text>
          <text x={36} y={ROW_Y[1] + NODE_H / 2 + 5} fill="#34d399" fontSize={14} fontWeight={700} textAnchor="middle">v2</text>

          {edges.map((e, i) => {
            const hi = focus && (e.r.from === focus || e.r.to === focus)
            const dim = focus && !hi
            return (
              <path key={i} d={e.d} fill="none"
                stroke={hi ? '#38bdf8' : '#475569'}
                strokeWidth={hi ? 2.2 : 1.3}
                opacity={dim ? 0.12 : hi ? 1 : 0.6}
                markerEnd={`url(#${hi ? 'er-arrow-hi' : 'er-arrow'})`} />
            )
          })}

          {nodes.map(n => {
            const st = n.internal ? STYLE.internal : STYLE[n.dataset]
            const isSel = selectedId === n.id
            const dim = focus && !linked.has(n.id)
            return (
              <g key={n.id}
                style={{ cursor: n.internal ? 'help' : 'pointer' }}
                opacity={dim ? 0.35 : 1}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                onClick={() => { if (!n.internal) onSelect(n.dataset, n.table) }}>
                <rect x={n.x} y={n.y} width={NODE_W} height={NODE_H} rx={9}
                  fill={st.fill} stroke={st.stroke} strokeWidth={isSel ? 2.6 : 1.2}
                  strokeDasharray={n.internal ? '4 3' : undefined} />
                <text x={n.x + NODE_W / 2} y={n.y + 19} fill="#e2e8f0" fontSize={12.5}
                  fontWeight={600} textAnchor="middle">
                  {n.table}
                </text>
                <text x={n.x + NODE_W / 2} y={n.y + 35} fill="#94a3b8" fontSize={10.5} textAnchor="middle">
                  {n.internal ? 'pipeline DuckDB' : n.rows != null ? `${fmtNum(n.rows)} rows` : 'not loaded'}
                </text>
              </g>
            )
          })}

          {edges.map((e, i) => {
            const hi = focus && (e.r.from === focus || e.r.to === focus)
            if (!hi || !e.r.on) return null
            const w = Math.max(60, e.r.on.length * 6.2 + 14)
            return (
              <g key={`l${i}`} pointerEvents="none">
                <rect x={e.lx - w / 2} y={e.ly - 10} width={w} height={18} rx={9}
                  fill="#0b1220" stroke="#38bdf8" strokeWidth={0.8} />
                <text x={e.lx} y={e.ly + 3} fill="#bae6fd" fontSize={10.5} textAnchor="middle"
                  fontFamily="ui-monospace, Consolas, monospace">
                  {e.r.on}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start', marginTop: 8 }}>
        <div className="muted" style={{ fontSize: 12, display: 'flex', gap: 14, flexWrap: 'wrap' }}>
          <span><span style={{ color: '#f59e0b' }}>■</span> v1 CSV</span>
          <span><span style={{ color: '#34d399' }}>■</span> v2 CSV</span>
          <span><span style={{ color: '#818cf8' }}>▢</span> pipeline-only DuckDB table</span>
          <span>Hover a table to see its links and join keys · click a CSV table to inspect its columns</span>
        </div>
      </div>

      {focusNode && (
        <div style={{
          marginTop: 10, padding: '10px 12px', borderRadius: 10,
          background: '#0f1729', border: '1px solid var(--border)', fontSize: 13,
        }}>
          <div style={{ fontWeight: 600 }}>
            {focusNode.internal ? focusNode.table : `${focusNode.dataset}.${focusNode.table}`}
          </div>
          {focusNode.description && <div className="muted" style={{ marginTop: 2 }}>{focusNode.description}</div>}
          {focusEdges.length > 0 && (
            <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
              {focusEdges.map((e, i) => {
                const incoming = e.r.to === focusNode.id
                const other = byId[incoming ? e.r.from : e.r.to]
                return (
                  <li key={i}>
                    <span className="muted">{incoming ? 'from' : 'to'}</span>{' '}
                    <b>{other.table}</b>{other.internal ? '' : ` (${other.dataset})`}
                    {' · '}<span className="mono">{e.r.on}</span>
                    {e.r.label && <span className="muted"> · {e.r.label}</span>}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
