import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fmtNum, fmtPct, monthLabel } from '../api'
import { Chart, COLORS } from '../components/Chart'
import { useFilters } from '../context/Filters'

export function DappsList() {
  const { dataVersion, category, dataset } = useFilters()
  const [q, setQ] = useState('')
  const ds = dataset === 'both' ? 'both' : dataset
  const { data, isLoading } = useQuery({
    queryKey: ['dapps', q, category, ds, dataVersion],
    queryFn: () => api.dapps({ q, category, dataset: ds, limit: 500 }),
  })

  return (
    <div className="card">
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <input className="input" placeholder="Search DApps…" value={q} onChange={e => setQ(e.target.value)} style={{ flex: 1 }} />
        <span className="muted" style={{ fontSize: 12 }}>{data?.dapps?.length ?? 0} shown</span>
      </div>
      {isLoading ? <div className="muted">Loading…</div> : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Name</th><th>Slug</th><th>Category</th><th>TVL</th><th>Contracts</th><th>In</th>
              </tr>
            </thead>
            <tbody>
              {(data?.dapps || []).map((d: any) => (
                <tr key={d.slug}>
                  <td><Link to={`/dapps/${d.slug}`} style={{ color: 'var(--accent)' }}>{d.name || d.slug}</Link></td>
                  <td className="mono muted">{d.slug}</td>
                  <td>{d.category_group}</td>
                  <td className="mono">{fmtNum(d.tvl)}</td>
                  <td className="mono">{fmtNum(d.n_contracts)}</td>
                  <td>
                    {d.in_v1 && <span className="pill pill-v1">v1</span>}{' '}
                    {d.in_v2 && <span className="pill pill-v2">v2</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function DappDetail() {
  const { slug = '' } = useParams()
  const { dataVersion, metric } = useFilters()
  const nav = useNavigate()
  const { data, isLoading, error } = useQuery({
    queryKey: ['dapp', slug, dataVersion],
    queryFn: () => api.dapp(slug),
    enabled: !!slug,
  })

  const v1s = data?.v1?.series || []
  const v2s = data?.v2?.series || []
  const months = useMemo(() => Array.from(new Set([
    ...v1s.map((r: any) => r.month), ...v2s.map((r: any) => r.month),
  ])).sort(), [v1s, v2s])
  const v1m = Object.fromEntries(v1s.map((r: any) => [r.month, r]))
  const v2m = Object.fromEntries(v2s.map((r: any) => [r.month, r]))

  const inV1 = v1s.length > 0 && metric in v1s[0]
  const inV2 = v2s.length > 0 && metric in v2s[0]
  const metricKey = inV1 || inV2 ? metric : 'active_wallets'
  const baseKey = metricKey.replace(/_ex_heavy$/, '')
  const exHeavyKey = `${baseKey}_ex_heavy`
  const showExHeavy = metricKey === baseKey && v2s.some((r: any) => r[exHeavyKey] != null)

  const seriesOpt = {
    title: {
      text: metricKey,
      subtext: !inV1 && v1s.length > 0 ? 'not available in v1' : undefined,
      textStyle: { color: '#e8eef9', fontSize: 14 },
    },
    legend: { data: ['v1', 'v2', ...(showExHeavy ? ['v2 ex-heavy'] : [])] },
    tooltip: { trigger: 'axis' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18 }],
    xAxis: { type: 'category', data: months.map(monthLabel) },
    yAxis: { type: 'value' },
    series: [
      { name: 'v1', type: 'line', showSymbol: false, color: COLORS.v1,
        data: months.map(m => v1m[m]?.[metricKey] ?? null) },
      { name: 'v2', type: 'line', showSymbol: false, color: COLORS.v2,
        data: months.map(m => v2m[m]?.[metricKey] ?? null) },
      ...(showExHeavy ? [{
        name: 'v2 ex-heavy', type: 'line', showSymbol: false, color: COLORS.accent2, lineStyle: { type: 'dashed' },
        data: months.map(m => v2m[m]?.[exHeavyKey] ?? null),
      }] : []),
    ],
  }

  const retentionOpt = {
    title: { text: 'New vs returning (v2)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: ['new', 'returning', 'retention'] },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: v2s.map((r: any) => monthLabel(r.month)) },
    yAxis: [{ type: 'value' }, { type: 'value', max: 1, axisLabel: { formatter: (v: number) => (v * 100).toFixed(0) + '%' } }],
    series: [
      { name: 'new', type: 'bar', stack: 'w', data: v2s.map((r: any) => r.new_wallets), color: COLORS.accent },
      { name: 'returning', type: 'bar', stack: 'w', data: v2s.map((r: any) => r.returning_wallets), color: COLORS.v2 },
      { name: 'retention', type: 'line', yAxisIndex: 1, data: v2s.map((r: any) => r.retention_prev_month), color: COLORS.v1 },
    ],
  }

  // cohort heatmap
  const cohorts = data?.v2?.cohorts || []
  const cohortMonths = Array.from(new Set(cohorts.map((c: any) => c.cohort_month))).sort() as string[]
  const maxSince = Math.min(24, Math.max(0, ...cohorts.map((c: any) => c.months_since)))
  const heatData: any[] = []
  for (const c of cohorts) {
    if (c.months_since > maxSince) continue
    heatData.push([c.months_since, cohortMonths.indexOf(c.cohort_month), c.retention_rate])
  }
  const heatOpt = {
    title: { text: 'Cohort retention', textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: {
      formatter: (p: any) => {
        const cm = cohortMonths[p.data[1]]
        return `${monthLabel(cm)} +${p.data[0]}m<br/>retention ${(p.data[2] * 100).toFixed(1)}%`
      },
    },
    grid: { left: 80, right: 40, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: Array.from({ length: maxSince + 1 }, (_, i) => String(i)), name: 'months since' },
    yAxis: { type: 'category', data: cohortMonths.map(monthLabel) },
    visualMap: {
      min: 0, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
      inRange: { color: ['#0b1220', '#1d4ed8', '#34d399'] },
      textStyle: { color: '#94a3b8' },
    },
    series: [{ type: 'heatmap', data: heatData, emphasis: { itemStyle: { borderColor: '#fff', borderWidth: 1 } } }],
  }

  if (isLoading) return <div className="card muted">Loading {slug}…</div>
  if (error) return <div className="card" style={{ color: 'var(--danger)' }}>{String(error)}</div>
  if (!data) return null

  const name = data.v2?.static?.name || data.v1?.static?.name || slug
  const life = data.v2?.lifecycle

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <button className="btn" onClick={() => nav('/dapps')} style={{ marginBottom: 8 }}>← All DApps</button>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{name}</div>
          <div className="mono muted">{slug}</div>
          <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
            {data.v1?.static && <span className="pill pill-v1">v1</span>}
            {data.v2?.static && <span className="pill pill-v2">v2</span>}
            <span className="pill">{data.v2?.static?.category_group || data.v1?.static?.category_group}</span>
            {life && <span className="pill">{life.lifecycle_label}</span>}
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
          <div><span className="muted">TVL</span> {fmtNum(data.v2?.static?.tvl ?? data.v1?.static?.tvl)}</div>
          <div><span className="muted">Contracts</span> v1 {data.v1?.static?.n_contracts ?? '—'} / v2 {data.v2?.static?.n_contracts ?? '—'}</div>
          {life && <>
            <div><span className="muted">Peak wallets</span> {fmtNum(life.peak_wallets)}</div>
            <div><span className="muted">Decay</span> {life.decay_ratio?.toFixed?.(2)}</div>
            <div><span className="muted">Months to 1k</span> {life.months_to_1k ?? '—'}</div>
            <div><span className="muted">Months to peak</span> {life.months_to_peak}</div>
          </>}
        </div>
      </div>

      <div className="card"><Chart option={seriesOpt} height={360} /></div>

      {v2s.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="card"><Chart option={retentionOpt} height={320} /></div>
          {cohorts.length > 0 && <div className="card"><Chart option={heatOpt} height={320} /></div>}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        {data.v1?.contracts_by_source?.length > 0 && (
          <div className="card">
            <div style={{ fontWeight: 600, marginBottom: 8 }}>v1 contracts by source</div>
            <table className="data">
              <thead><tr><th>Source</th><th>Count</th></tr></thead>
              <tbody>
                {data.v1.contracts_by_source.map((r: any) => (
                  <tr key={r.source}><td>{r.source}</td><td className="mono">{fmtNum(r.n)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.v2?.contracts_breakdown?.length > 0 && (
          <div className="card">
            <div style={{ fontWeight: 600, marginBottom: 8 }}>v2 contracts by role / source</div>
            <div className="table-wrap" style={{ maxHeight: 260 }}>
              <table className="data">
                <thead><tr><th>Role</th><th>Source</th><th>Conf.</th><th>N</th></tr></thead>
                <tbody>
                  {data.v2.contracts_breakdown.map((r: any, i: number) => (
                    <tr key={i}><td>{r.role}</td><td>{r.source}</td><td>{r.confidence}</td><td className="mono">{fmtNum(r.n)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {life && (
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Lifecycle features</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 8, fontSize: 13 }}>
            {[
              ['Launch', monthLabel(life.launch_month)],
              ['Peak month', monthLabel(life.peak_month)],
              ['Wallets m3', fmtNum(life.wallets_m3)],
              ['Wallets m6', fmtNum(life.wallets_m6)],
              ['Wallets m12', fmtNum(life.wallets_m12)],
              ['Early retention', fmtPct(life.early_retention)],
              ['Early whale share', fmtPct(life.early_whale_share)],
              ['Prior app share', fmtPct(life.early_prior_app_share)],
              ['Months active', life.months_active],
            ].map(([k, v]) => (
              <div key={String(k)}><div className="muted" style={{ fontSize: 11 }}>{k}</div><div className="mono">{v}</div></div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
