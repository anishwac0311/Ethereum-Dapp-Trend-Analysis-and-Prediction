import { NavLink, Outlet } from 'react-router-dom'
import { useFilters } from '../context/Filters'
import { fmtNum } from '../api'

const NAV = [
  { to: '/', label: 'Overview' },
  { to: '/compare', label: 'v1 vs v2' },
  { to: '/dapps', label: 'DApps' },
  { to: '/ecosystem', label: 'Ecosystem' },
  { to: '/variations', label: 'Variations' },
  { to: '/schema', label: 'Schema' },
  { to: '/tables', label: 'Tables' },
]

function PipelineBadge() {
  const { pipeline } = useFilters()
  if (!pipeline) return null
  if (pipeline.running) {
    const prog = pipeline.month_i && pipeline.month_n
      ? `${pipeline.month_i}/${pipeline.month_n}`
      : pipeline.step && pipeline.step_total
        ? `step ${pipeline.step}/${pipeline.step_total}`
        : '…'
    const eta = pipeline.eta_seconds
      ? ` · ETA ${Math.round(pipeline.eta_seconds / 60)}m`
      : ''
    return (
      <span className="pill pill-run" title={pipeline.last_line || ''}>
        Pipeline {pipeline.month || 'running'} ({prog}){eta}
      </span>
    )
  }
  if (pipeline.finished) {
    return <span className="pill pill-ok">Last run finished {pipeline.finished_at?.slice(0, 16)}</span>
  }
  if (pipeline.failed) {
    return <span className="pill" style={{ color: 'var(--danger)' }}>Pipeline failed</span>
  }
  return <span className="pill muted">Pipeline idle</span>
}

function FilterBar() {
  const f = useFilters()
  const cats = f.meta?.categories || []
  const metrics = f.meta?.metrics || ['active_wallets', 'tx_count', 'gas_used', 'fees_eth']
  const minM = [f.meta?.monthRanges.v1.min, f.meta?.monthRanges.v2.min].filter(Boolean).sort()[0]?.slice(0, 7) || '2018-01'
  const maxM = [f.meta?.monthRanges.v1.max, f.meta?.monthRanges.v2.max].filter(Boolean).sort().reverse()[0]?.slice(0, 7) || '2026-12'

  return (
    <div className="card" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
      <label className="muted" style={{ fontSize: 12 }}>Dataset
        <select className="select" style={{ marginLeft: 6 }} value={f.dataset} onChange={e => f.setDataset(e.target.value as any)}>
          <option value="both">Both</option>
          <option value="v1">v1 only</option>
          <option value="v2">v2 only</option>
        </select>
      </label>
      <label className="muted" style={{ fontSize: 12 }}>Metric
        <select className="select" style={{ marginLeft: 6 }} value={f.metric} onChange={e => f.setMetric(e.target.value)}>
          {metrics.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>
      <label className="muted" style={{ fontSize: 12 }}>Category
        <select className="select" style={{ marginLeft: 6 }} value={f.category} onChange={e => f.setCategory(e.target.value)}>
          <option value="">All</option>
          {cats.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </label>
      <label className="muted" style={{ fontSize: 12 }}>From
        <input className="input" type="month" style={{ marginLeft: 6 }} value={f.start.slice(0, 7)} min={minM} max={maxM}
          onChange={e => f.setStart(e.target.value ? e.target.value + '-01' : '')} />
      </label>
      <label className="muted" style={{ fontSize: 12 }}>To
        <input className="input" type="month" style={{ marginLeft: 6 }} value={f.end.slice(0, 7)} min={minM} max={maxM}
          onChange={e => f.setEnd(e.target.value ? e.target.value + '-01' : '')} />
      </label>
      <span className="pill">data v{f.dataVersion}</span>
      {f.meta && (
        <span className="muted" style={{ fontSize: 12 }}>
          v1 {f.meta.monthRanges.v1.min?.slice(0, 7)}→{f.meta.monthRanges.v1.max?.slice(0, 7)} ·
          v2 {f.meta.monthRanges.v2.min?.slice(0, 7)}→{f.meta.monthRanges.v2.max?.slice(0, 7)}
        </span>
      )}
    </div>
  )
}

export function Layout() {
  const { toast, meta } = useFilters()
  const v1rows = meta?.tables.find(t => t.key === 'v1_dapp_panel')?.rows
  const v2rows = meta?.tables.find(t => t.key === 'v2_dapp_panel')?.rows

  return (
    <div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
      <header style={{
        borderBottom: '1px solid var(--border)',
        background: 'rgba(11,18,32,0.92)',
        backdropFilter: 'blur(8px)',
        position: 'sticky', top: 0, zIndex: 20,
        padding: '0.75rem 1.25rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontWeight: 700, letterSpacing: '-0.02em' }}>DApp Dataset Dashboard</div>
            <div className="muted" style={{ fontSize: 12 }}>
              v1 vs v2 · panel {fmtNum(v1rows)} / {fmtNum(v2rows)} rows
            </div>
          </div>
          <nav style={{ display: 'flex', gap: 4, flexWrap: 'wrap', flex: 1 }}>
            {NAV.map(n => (
              <NavLink key={n.to} to={n.to} end={n.to === '/'}
                className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <PipelineBadge />
        </div>
      </header>

      <div style={{ padding: '1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
        <FilterBar />
        {toast && (
          <div className="card" style={{ borderColor: 'rgba(52,211,153,0.5)', color: 'var(--v2)' }}>
            {toast}
          </div>
        )}
        <Outlet />
      </div>
    </div>
  )
}
