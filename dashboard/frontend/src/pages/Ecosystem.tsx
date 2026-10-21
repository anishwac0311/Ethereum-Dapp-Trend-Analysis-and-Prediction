import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, monthLabel } from '../api'
import { Chart, COLORS } from '../components/Chart'
import { useFilters } from '../context/Filters'

export function Ecosystem() {
  const { dataVersion, start, end } = useFilters()
  const [scope, setScope] = useState('ecosystem')
  const [concMetric, setConcMetric] = useState('active_wallets')
  const nav = useNavigate()

  const cat = useQuery({
    queryKey: ['cat-month', start, end, dataVersion],
    queryFn: () => api.categoryMonth(start || undefined, end || undefined),
  })
  const conc = useQuery({
    queryKey: ['conc', scope, concMetric, dataVersion],
    queryFn: () => api.concentration(scope, concMetric),
  })
  const life = useQuery({
    queryKey: ['lifecycle', dataVersion],
    queryFn: api.lifecycle,
  })

  const rows = cat.data?.rows || []
  const groups = Array.from(new Set(rows.map((r: any) => r.category_group))) as string[]
  const months = Array.from(new Set(rows.map((r: any) => r.month))).sort() as string[]

  const stacked = {
    title: { text: 'Category active wallets (deduped)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: groups, type: 'scroll', top: 0 },
    tooltip: { trigger: 'axis' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18 }],
    xAxis: { type: 'category', data: months.map(monthLabel) },
    yAxis: { type: 'value' },
    series: groups.map((g, i) => ({
      name: g,
      type: 'line',
      stack: 'total',
      areaStyle: { opacity: 0.35 },
      showSymbol: false,
      color: COLORS.series[i % COLORS.series.length],
      data: months.map(m => rows.find((r: any) => r.month === m && r.category_group === g)?.active_wallets ?? 0),
    })),
  }

  const concRows = (conc.data?.rows || []).filter((r: any) =>
    scope === 'ecosystem' ? r.category_group === 'ALL' : true)
  // if category scope, pick one series per category for HHI
  const concCats = scope === 'category'
    ? Array.from(new Set(concRows.map((r: any) => r.category_group))) as string[]
    : ['ALL']
  const concMonths = Array.from(new Set(concRows.map((r: any) => r.month))).sort() as string[]

  const concOpt = {
    title: { text: `Concentration · ${scope} · ${concMetric}`, textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: ['HHI', 'Gini', 'Top1', 'Top5', 'Top10'] },
    tooltip: { trigger: 'axis' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18 }],
    xAxis: { type: 'category', data: concMonths.map(monthLabel) },
    yAxis: { type: 'value', max: 1 },
    series: scope === 'ecosystem' ? [
      { name: 'HHI', type: 'line', showSymbol: false, data: concMonths.map(m => concRows.find((r: any) => r.month === m)?.hhi), color: COLORS.accent },
      { name: 'Gini', type: 'line', showSymbol: false, data: concMonths.map(m => concRows.find((r: any) => r.month === m)?.gini), color: COLORS.accent2 },
      { name: 'Top1', type: 'line', showSymbol: false, data: concMonths.map(m => concRows.find((r: any) => r.month === m)?.top1_share), color: COLORS.v1 },
      { name: 'Top5', type: 'line', showSymbol: false, data: concMonths.map(m => concRows.find((r: any) => r.month === m)?.top5_share), color: COLORS.v2 },
      { name: 'Top10', type: 'line', showSymbol: false, data: concMonths.map(m => concRows.find((r: any) => r.month === m)?.top10_share), color: '#f472b6' },
    ] : concCats.slice(0, 6).map((g, i) => ({
      name: g,
      type: 'line',
      showSymbol: false,
      color: COLORS.series[i % COLORS.series.length],
      data: concMonths.map(m => concRows.find((r: any) => r.month === m && r.category_group === g)?.hhi),
    })),
  }

  // lifecycle distribution
  const labels = Array.from(new Set((life.data?.distribution || []).map((r: any) => r.lifecycle_label))) as string[]
  const lifeCats = Array.from(new Set((life.data?.distribution || []).map((r: any) => r.category_group))) as string[]
  const lifeOpt = {
    title: { text: 'Lifecycle labels by category', textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: labels },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: lifeCats },
    yAxis: { type: 'value' },
    series: labels.map((lab, i) => ({
      name: lab,
      type: 'bar',
      stack: 'l',
      color: COLORS.series[i % COLORS.series.length],
      data: lifeCats.map(c =>
        (life.data?.distribution || []).find((r: any) => r.lifecycle_label === lab && r.category_group === c)?.n || 0),
    })),
  }

  const scatterPts = (life.data?.scatter || []).filter((p: any) => p.early_retention != null && p.decay_ratio != null)
  const lifeScatter = {
    title: { text: 'Early retention vs decay (by lifecycle)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: {
      formatter: (p: any) => `${p.data[3]}<br/>retention ${p.data[0]?.toFixed?.(2)}<br/>decay ${p.data[1]?.toFixed?.(2)}<br/>${p.data[2]}`,
    },
    legend: { data: labels },
    xAxis: { type: 'value', name: 'early_retention', min: 0, max: 1 },
    yAxis: { type: 'value', name: 'decay_ratio', min: 0, max: 1.5 },
    series: labels.map((lab, i) => ({
      name: lab,
      type: 'scatter',
      symbolSize: (d: any) => Math.max(6, Math.min(24, Math.log10((d[4] || 1) + 1) * 6)),
      itemStyle: { color: COLORS.series[i % COLORS.series.length], opacity: 0.75 },
      data: scatterPts.filter((p: any) => p.lifecycle_label === lab)
        .map((p: any) => [p.early_retention, p.decay_ratio, p.lifecycle_label, p.name || p.slug, p.peak_wallets, p.slug]),
    })),
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="card"><Chart option={stacked} height={380} /></div>

      <div className="card">
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <select className="select" value={scope} onChange={e => setScope(e.target.value)}>
            <option value="ecosystem">Ecosystem</option>
            <option value="category">By category (HHI)</option>
          </select>
          <select className="select" value={concMetric} onChange={e => setConcMetric(e.target.value)}>
            <option value="active_wallets">active_wallets</option>
            <option value="tx_count">tx_count</option>
            <option value="gas_used">gas_used</option>
          </select>
        </div>
        <Chart option={concOpt} height={340} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card"><Chart option={lifeOpt} height={340} /></div>
        <div className="card">
          <Chart
            option={lifeScatter}
            height={340}
            onEvents={{
              click: (p: any) => {
                const slug = p?.data?.[5]
                if (slug) nav(`/dapps/${slug}`)
              },
            }}
          />
        </div>
      </div>
    </div>
  )
}
