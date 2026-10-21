import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { ErDiagram } from '../components/ErDiagram'
import { useFilters } from '../context/Filters'

export function Schema() {
  const { dataVersion } = useFilters()
  const [sel, setSel] = useState<{ dataset: string; table: string } | null>(null)
  const [colFilter, setColFilter] = useState('')
  const { data, isLoading } = useQuery({
    queryKey: ['schema', dataVersion],
    queryFn: () => api.schema(),
  })
  const profileQ = useQuery({
    queryKey: ['schema-profile', sel?.dataset, sel?.table, dataVersion],
    queryFn: () => api.schema({ dataset: sel!.dataset, table: sel!.table, profile: '1' }),
    enabled: !!sel,
  })

  const tables = data?.tables || []
  const selectedBase = tables.find((t: any) => t.dataset === sel?.dataset && t.table === sel?.table) || tables[0]
  const selected = profileQ.data?.tables?.[0] || selectedBase

  useEffect(() => {
    if (!sel && tables.length) {
      setSel({ dataset: tables[0].dataset, table: tables[0].table })
    }
  }, [tables, sel])

  if (isLoading) return <div className="card muted">Loading schema…</div>

  const cols = (selected?.columns || []).filter((c: any) =>
    !colFilter || c.name.toLowerCase().includes(colFilter.toLowerCase()) ||
    (c.description || '').toLowerCase().includes(colFilter.toLowerCase()))

  // column diff between v1 and v2 panels
  const v1panel = tables.find((t: any) => t.dataset === 'v1' && t.table === 'dapp_panel')
  const v2panel = tables.find((t: any) => t.dataset === 'v2' && t.table === 'dapp_panel')
  const v1cols = new Set<string>((v1panel?.columns || []).map((c: any) => c.name as string))
  const v2cols = new Set<string>((v2panel?.columns || []).map((c: any) => c.name as string))
  const shared: string[] = [...v1cols].filter(c => v2cols.has(c))
  const v1only: string[] = [...v1cols].filter(c => !v2cols.has(c))
  const v2only: string[] = [...v2cols].filter(c => !v1cols.has(c))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="card">
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Entity relationships</div>
        <ErDiagram
          relationships={data?.relationships || []}
          tables={tables}
          internalTables={data?.internalTables || {}}
          selectedId={sel ? `${sel.dataset}.${sel.table}` : undefined}
          onSelect={(dataset, table) => setSel({ dataset, table })}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        <DiffCard title="Shared panel columns" items={shared} tone="#38bdf8" />
        <DiffCard title="v1-only panel columns" items={v1only} tone="var(--v1)" />
        <DiffCard title="v2-only panel columns" items={v2only} tone="var(--v2)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '1rem' }}>
        <div className="card" style={{ maxHeight: 560, overflow: 'auto' }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Tables</div>
          {tables.map((t: any) => (
            <button
              key={`${t.dataset}.${t.table}`}
              className="btn"
              style={{
                display: 'block', width: '100%', textAlign: 'left', marginBottom: 4,
                background: selected?.dataset === t.dataset && selected?.table === t.table ? '#1d4ed8' : undefined,
              }}
              onClick={() => setSel({ dataset: t.dataset, table: t.table })}
            >
              <span className={`pill pill-${t.dataset}`}>{t.dataset}</span>{' '}
              {t.table}
              <div className="muted" style={{ fontSize: 11 }}>{t.rows?.toLocaleString()} rows · {t.columns?.length} cols</div>
            </button>
          ))}
        </div>

        <div className="card">
          {selected && (
            <>
              <div style={{ fontWeight: 600 }}>{selected.dataset}.{selected.table}</div>
              <p className="muted" style={{ fontSize: 13 }}>{selected.description}</p>
              <div style={{ fontSize: 12, marginBottom: 8 }}>
                <b>Grain:</b> {selected.grain || '—'} · <b>Keys:</b> {(selected.keys || []).join(', ') || '—'}
              </div>
              <input className="input" placeholder="Filter columns…" value={colFilter}
                onChange={e => setColFilter(e.target.value)} style={{ marginBottom: 8, width: '100%' }} />
              <div className="table-wrap" style={{ maxHeight: 420 }}>
                <table className="data">
                  <thead>
                    <tr>
                      <th>Column</th><th>Type</th><th>Null %</th><th>Unique</th><th>Range / samples</th><th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cols.map((c: any) => (
                      <tr key={c.name}>
                        <td className="mono">{c.name}</td>
                        <td className="muted">{c.dtype}</td>
                        <td>{c.null_pct ?? '—'}</td>
                        <td>{c.nunique?.toLocaleString?.() ?? c.nunique ?? '—'}</td>
                        <td className="mono" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {c.min != null ? `${c.min} → ${c.max}` : (c.samples || []).join(', ')}
                        </td>
                        <td style={{ whiteSpace: 'normal', maxWidth: 360 }}>{c.description || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function DiffCard({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <div className="card">
      <div style={{ fontWeight: 600, color: tone, marginBottom: 6 }}>{title} ({items.length})</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {items.map(c => <span key={c} className="pill mono" style={{ fontSize: 11 }}>{c}</span>)}
        {items.length === 0 && <span className="muted">None</span>}
      </div>
    </div>
  )
}
