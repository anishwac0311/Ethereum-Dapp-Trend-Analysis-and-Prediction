import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, fmtNum, monthLabel } from '../api'
import { Chart, COLORS } from '../components/Chart'
import { useFilters } from '../context/Filters'

export function Overview() {
  const { dataVersion, metric, start, end, pipeline, meta } = useFilters()
  const coverage = useQuery({ queryKey: ['coverage', dataVersion], queryFn: api.coverage })
  const overlap = useQuery({ queryKey: ['overlap', dataVersion], queryFn: api.overlap })
  const topV2 = useQuery({
    queryKey: ['top', 'v2', metric, dataVersion],
    queryFn: () => api.top('v2', metric),
  })
  const topV1 = useQuery({
    queryKey: ['top', 'v1', metric, dataVersion],
    queryFn: () => api.top('v1', metric),
  })

  const v1 = (coverage.data?.v1 || []).filter((r: any) =>
    (!start || r.month >= start) && (!end || r.month <= end))
  const v2 = (coverage.data?.v2 || []).filter((r: any) =>
    (!start || r.month >= start) && (!end || r.month <= end))

  const months = Array.from(new Set([...v1.map((r: any) => r.month), ...v2.map((r: any) => r.month)])).sort()
  const v1map = Object.fromEntries(v1.map((r: any) => [r.month, r]))
  const v2map = Object.fromEntries(v2.map((r: any) => [r.month, r]))

  const lineOpt = {
    title: { text: `Ecosystem ${metric}`, left: 0, textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: ['v1', 'v2'], top: 0, right: 0 },
    tooltip: { trigger: 'axis' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18 }],
    xAxis: { type: 'category', data: months.map(monthLabel) },
    yAxis: { type: 'value', scale: true },
    series: [
      { name: 'v1', type: 'line', showSymbol: false, data: months.map(m => v1map[m]?.[metric === 'tx_count' ? 'tx_count' : 'active_wallets'] ?? null), color: COLORS.v1 },
      { name: 'v2', type: 'line', showSymbol: false, data: months.map(m => v2map[m]?.[metric === 'tx_count' ? 'tx_count' : 'active_wallets'] ?? null), color: COLORS.v2 },
    ],
  }

  const coverOpt = {
    title: { text: 'Month coverage (active DApps)', left: 0, textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: ['v1', 'v2'], top: 0, right: 0 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: months.map(monthLabel) },
    yAxis: { type: 'value' },
    series: [
      { name: 'v1', type: 'bar', data: months.map(m => v1map[m]?.active_dapps ?? 0), color: COLORS.v1, barMaxWidth: 10 },
      { name: 'v2', type: 'bar', data: months.map(m => v2map[m]?.active_dapps ?? 0), color: COLORS.v2, barMaxWidth: 10 },
    ],
  }

  const o = overlap.data || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: '0.75rem' }}>
        <Stat label="v1 DApps" value={fmtNum(o.v1_count)} sub="seed-contract panel" color="var(--v1)" />
        <Stat label="v2 DApps" value={fmtNum(o.v2_count)} sub="app-contract panel" color="var(--v2)" />
        <Stat label="In both" value={fmtNum(o.both)} sub="comparable slugs" />
        <Stat label="v1 only" value={fmtNum(o.v1_only)} />
        <Stat label="v2 only" value={fmtNum(o.v2_only)} />
        <Stat label="Data version" value={String(meta?.dataVersion ?? '—')} sub={pipeline?.running ? 'pipeline running' : 'idle'} />
      </div>

      {pipeline?.running && (
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Pipeline live</div>
          <div className="muted" style={{ fontSize: 13 }}>
            {pipeline.step_message || pipeline.command}
          </div>
          {pipeline.month && (
            <div style={{ marginTop: 8 }}>
              Processing <span className="mono">{pipeline.month}</span>{' '}
              ({pipeline.month_i}/{pipeline.month_n}) · {fmtNum(pipeline.month_rows)} wallet rows ·{' '}
              {pipeline.month_dapps} DApps · {pipeline.month_duration}
              {pipeline.eta_seconds != null && <> · ETA ~{Math.round(pipeline.eta_seconds / 60)} min</>}
            </div>
          )}
          {pipeline.month_n && pipeline.month_i != null && (
            <div style={{ marginTop: 10, height: 8, background: '#1a2438', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{
                width: `${(100 * pipeline.month_i) / pipeline.month_n}%`,
                height: '100%', background: 'linear-gradient(90deg,#fbbf24,#34d399)',
              }} />
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1rem' }}>
        <div className="card"><Chart option={lineOpt} height={360} /></div>
        <div className="card"><Chart option={coverOpt} height={360} /></div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <TopList title={`Top v2 by Σ ${metric}`} rows={topV2.data?.rows || []} color="var(--v2)" />
        <TopList title={`Top v1 by Σ ${metric}`} rows={topV1.data?.rows || []} color="var(--v1)" />
      </div>
    </div>
  )
}

function Stat({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="card">
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color, letterSpacing: '-0.03em' }}>{value}</div>
      {sub && <div className="muted" style={{ fontSize: 11 }}>{sub}</div>}
    </div>
  )
}

function TopList({ title, rows, color }: { title: string; rows: any[]; color: string }) {
  return (
    <div className="card">
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{title}</div>
      <div className="table-wrap" style={{ maxHeight: 320 }}>
        <table className="data">
          <thead><tr><th>#</th><th>DApp</th><th>Category</th><th>Value</th></tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.slug}>
                <td className="muted">{i + 1}</td>
                <td><Link to={`/dapps/${r.slug}`} style={{ color }}>{r.name || r.slug}</Link></td>
                <td className="muted">{r.category_group}</td>
                <td className="mono">{fmtNum(r.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
