import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, fmtNum, fmtPct, monthLabel } from '../api'
import { Chart, COLORS } from '../components/Chart'
import { useFilters } from '../context/Filters'

export function Variations() {
  const { dataVersion, metric, dataset } = useFilters()
  const ds = dataset === 'both' ? 'v2' : dataset
  const nav = useNavigate()

  const dist = useQuery({
    queryKey: ['vardist', ds, metric, dataVersion],
    queryFn: () => api.variationsDist(ds, metric),
  })
  const vol = useQuery({
    queryKey: ['vol', ds, metric, dataVersion],
    queryFn: () => api.volatility(ds, metric),
  })
  const heavy = useQuery({
    queryKey: ['heavy', dataVersion],
    queryFn: api.heavyImpact,
  })
  const attr = useQuery({
    queryKey: ['attr', dataVersion],
    queryFn: api.attribution,
  })

  const boxOpt = {
    title: { text: `${metric} by category (positive months)`, textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: (dist.data?.rows || []).map((r: any) => r.grp), axisLabel: { rotate: 20 } },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'boxplot',
        color: COLORS.accent,
        data: (dist.data?.rows || []).map((r: any) => [r.min, r.q25, r.median, r.q75, r.max]),
      },
    ],
  }

  const volOpt = {
    title: { text: 'MoM growth volatility (top)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 120 },
    yAxis: { type: 'category', data: (vol.data?.rows || []).slice(0, 20).map((r: any) => r.name || r.slug).reverse() },
    xAxis: { type: 'value', name: 'stddev(growth)' },
    series: [{
      type: 'bar',
      color: COLORS.accent2,
      data: (vol.data?.rows || []).slice(0, 20).map((r: any) => r.growth_vol).reverse(),
    }],
  }

  const heavyOpt = {
    title: { text: 'Heavy-wallet share of activity (v2)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: {
      formatter: (p: any) => `${p.name}<br/>heavy share ${fmtPct(p.value)}`,
    },
    grid: { left: 120 },
    yAxis: { type: 'category', data: (heavy.data?.rows || []).slice(0, 20).map((r: any) => r.name || r.slug).reverse() },
    xAxis: { type: 'value', max: 1 },
    series: [{
      type: 'bar',
      color: COLORS.v1,
      data: (heavy.data?.rows || []).slice(0, 20).map((r: any) => r.heavy_share).reverse(),
    }],
  }

  const attrMonthly = attr.data?.monthly || []
  const attrOpt = {
    title: { text: 'Avg protocols credited per tx (v2)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: ['mean', 'median'] },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: attrMonthly.map((r: any) => monthLabel(r.month)) },
    yAxis: { type: 'value', min: 1 },
    series: [
      { name: 'mean', type: 'line', showSymbol: false, data: attrMonthly.map((r: any) => r.avg_n), color: COLORS.accent },
      { name: 'median', type: 'line', showSymbol: false, data: attrMonthly.map((r: any) => r.median_n), color: COLORS.v2 },
    ],
  }

  const whaleOpt = {
    title: { text: 'DApps with highest multi-protocol attribution', textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 120 },
    yAxis: {
      type: 'category',
      data: (attr.data?.by_dapp || []).slice(0, 20).map((r: any) => r.name || r.slug).reverse(),
    },
    xAxis: { type: 'value', name: 'avg n_protocols_in_tx' },
    series: [{
      type: 'bar',
      color: COLORS.accent,
      data: (attr.data?.by_dapp || []).slice(0, 20).map((r: any) => r.avg_n).reverse(),
    }],
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="muted" style={{ fontSize: 13 }}>
        Showing variations for <b>{ds}</b> · metric <b>{metric}</b>. Switch dataset/metric in the filter bar.
      </div>
      <div className="card"><Chart option={boxOpt} height={360} /></div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card"><Chart option={volOpt} height={420} /></div>
        <div className="card"><Chart option={heavyOpt} height={420} /></div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card"><Chart option={attrOpt} height={340} /></div>
        <div className="card"><Chart option={whaleOpt} height={340} /></div>
      </div>

      <div className="card">
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Heavy impact detail</div>
        <div className="table-wrap" style={{ maxHeight: 280 }}>
          <table className="data">
            <thead><tr><th>DApp</th><th>Total wallets</th><th>Ex-heavy</th><th>Heavy share</th></tr></thead>
            <tbody>
              {(heavy.data?.rows || []).map((r: any) => (
                <tr key={r.slug} style={{ cursor: 'pointer' }} onClick={() => nav(`/dapps/${r.slug}`)}>
                  <td>{r.name || r.slug}</td>
                  <td className="mono">{fmtNum(r.total)}</td>
                  <td className="mono">{fmtNum(r.ex_heavy)}</td>
                  <td className="mono">{fmtPct(r.heavy_share)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
