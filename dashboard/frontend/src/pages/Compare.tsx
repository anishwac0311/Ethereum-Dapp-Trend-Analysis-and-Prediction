import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, fmtNum, fmtPct, monthLabel } from '../api'
import { Chart, COLORS } from '../components/Chart'
import { useFilters } from '../context/Filters'

export function Compare() {
  const { dataVersion, metric, start, end, meta } = useFilters()
  const nav = useNavigate()

  const eco = useQuery({
    queryKey: ['eco', metric, start, end, dataVersion],
    queryFn: () => api.ecosystem(metric, start || undefined, end || undefined),
  })
  const scatter = useQuery({
    queryKey: ['scatter', metric, start, end, dataVersion],
    queryFn: () => api.scatter(metric, start || undefined, end || undefined),
  })
  const hist = useQuery({
    queryKey: ['ratio-hist', metric, dataVersion],
    queryFn: () => api.ratioHist(metric),
  })
  const cats = useQuery({ queryKey: ['cats', dataVersion], queryFn: api.categories })
  const disagree = useQuery({
    queryKey: ['disagree', metric, dataVersion],
    queryFn: () => api.disagreements(metric),
  })
  const overlap = useQuery({ queryKey: ['overlap', dataVersion], queryFn: api.overlap })

  const months = Array.from(new Set([
    ...(eco.data?.v1 || []).map((r: any) => r.month),
    ...(eco.data?.v2 || []).map((r: any) => r.month),
  ])).sort()
  const v1m = Object.fromEntries((eco.data?.v1 || []).map((r: any) => [r.month, r.value]))
  const v2m = Object.fromEntries((eco.data?.v2 || []).map((r: any) => [r.month, r.value]))

  const points = (scatter.data?.points || []).filter((p: any) => p.v1 > 0 && p.v2 > 0)

  const lineOpt = {
    title: { text: `Ecosystem total · ${metric}`, textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: ['v1', 'v2'] },
    tooltip: { trigger: 'axis' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18 }],
    xAxis: { type: 'category', data: months.map(monthLabel) },
    yAxis: { type: 'value' },
    series: [
      { name: 'v1', type: 'line', showSymbol: false, data: months.map(m => v1m[m] ?? null), color: COLORS.v1 },
      { name: 'v2', type: 'line', showSymbol: false, data: months.map(m => v2m[m] ?? null), color: COLORS.v2 },
    ],
  }

  const scatterOpt = {
    title: { text: `Per-DApp Σ ${metric} (log–log)`, textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        const d = p.data
        return `<b>${d[3]}</b><br/>v1: ${fmtNum(d[0])}<br/>v2: ${fmtNum(d[1])}<br/>ratio: ${d[2]?.toFixed?.(2) ?? '—'}`
      },
    },
    xAxis: { type: 'log', name: 'v1', nameLocation: 'middle', nameGap: 28 },
    yAxis: { type: 'log', name: 'v2', nameLocation: 'middle', nameGap: 40 },
    series: [{
      type: 'scatter',
      symbolSize: 8,
      data: points.map((p: any) => [p.v1, p.v2, p.ratio, p.name || p.slug, p.slug]),
      itemStyle: { color: COLORS.accent, opacity: 0.7 },
    }],
  }

  const histOpt = {
    title: { text: 'v2 / v1 ratio distribution (log bins)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: (hist.data?.bins || []).map((b: any) => `${b.x0.toFixed(2)}–${b.x1.toFixed(2)}`),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value', name: 'DApps' },
    series: [{
      type: 'bar',
      data: (hist.data?.bins || []).map((b: any) => b.count),
      color: COLORS.accent2,
    }],
  }

  const catGroups = Array.from(new Set([
    ...(cats.data?.v1 || []).map((r: any) => r.category_group),
    ...(cats.data?.v2 || []).map((r: any) => r.category_group),
  ]))
  const catOpt = {
    title: { text: 'Category mix (# DApps)', textStyle: { color: '#e8eef9', fontSize: 14 } },
    legend: { data: ['v1', 'v2'] },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: catGroups },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'v1', type: 'bar', color: COLORS.v1,
        data: catGroups.map(g => (cats.data?.v1 || []).find((r: any) => r.category_group === g)?.n_dapps || 0),
      },
      {
        name: 'v2', type: 'bar', color: COLORS.v2,
        data: catGroups.map(g => (cats.data?.v2 || []).find((r: any) => r.category_group === g)?.n_dapps || 0),
      },
    ],
  }

  const m1 = meta?.methodology?.v1
  const m2 = meta?.methodology?.v2

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <MethodCard m={m1} tone="v1" />
        <MethodCard m={m2} tone="v2" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: '0.75rem' }}>
        <div className="card"><div className="muted" style={{ fontSize: 12 }}>Overlap</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{fmtNum(overlap.data?.both)}</div></div>
        <div className="card"><div className="muted" style={{ fontSize: 12 }}>v1 only</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--v1)' }}>{fmtNum(overlap.data?.v1_only)}</div></div>
        <div className="card"><div className="muted" style={{ fontSize: 12 }}>v2 only</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--v2)' }}>{fmtNum(overlap.data?.v2_only)}</div></div>
        <div className="card"><div className="muted" style={{ fontSize: 12 }}>Zero-activity share</div>
          <div style={{ fontSize: 18 }}>v1 {fmtPct(cats.data?.zero_activity?.v1_zero_share)} · v2 {fmtPct(cats.data?.zero_activity?.v2_zero_share)}</div></div>
        <div className="card"><div className="muted" style={{ fontSize: 12 }}>Median v2/v1 ratio</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{hist.data?.median?.toFixed?.(2) ?? '—'}</div></div>
      </div>

      <div className="card"><Chart option={lineOpt} height={340} /></div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1rem' }}>
        <div className="card">
          <Chart
            option={scatterOpt}
            height={420}
            onEvents={{
              click: (p: any) => {
                const slug = p?.data?.[4]
                if (slug) nav(`/dapps/${slug}`)
              },
            }}
          />
          <div className="muted" style={{ fontSize: 12 }}>Click a point to open the DApp</div>
        </div>
        <div className="card"><Chart option={histOpt} height={420} /></div>
      </div>

      <div className="card"><Chart option={catOpt} height={320} /></div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <DisagreeTable title="Highest v2/v1 ratio" rows={disagree.data?.highest_v2_ratio || []} onClick={s => nav(`/dapps/${s}`)} />
        <DisagreeTable title="Lowest v2/v1 ratio" rows={disagree.data?.lowest_v2_ratio || []} onClick={s => nav(`/dapps/${s}`)} />
      </div>
    </div>
  )
}

function MethodCard({ m, tone }: { m?: any; tone: 'v1' | 'v2' }) {
  if (!m) return <div className="card muted">Loading methodology…</div>
  return (
    <div className="card">
      <div className={`pill pill-${tone}`} style={{ marginBottom: 8 }}>{tone.toUpperCase()}</div>
      <div style={{ fontWeight: 600 }}>{m.title}</div>
      <p className="muted" style={{ fontSize: 13, lineHeight: 1.5 }}>{m.summary}</p>
      <div style={{ fontSize: 12 }}><b>Sources:</b> {m.sources?.join(' · ')}</div>
      <ul className="muted" style={{ fontSize: 12, margin: '6px 0 0', paddingLeft: 18 }}>
        {m.limitations?.map((l: string) => <li key={l}>{l}</li>)}
      </ul>
    </div>
  )
}

function DisagreeTable({ title, rows, onClick }: { title: string; rows: any[]; onClick: (s: string) => void }) {
  return (
    <div className="card">
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{title}</div>
      <div className="table-wrap" style={{ maxHeight: 280 }}>
        <table className="data">
          <thead><tr><th>DApp</th><th>v1</th><th>v2</th><th>ratio</th></tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.slug} style={{ cursor: 'pointer' }} onClick={() => onClick(r.slug)}>
                <td>{r.name || r.slug}</td>
                <td className="mono">{fmtNum(r.v1)}</td>
                <td className="mono">{fmtNum(r.v2)}</td>
                <td className="mono">{r.ratio?.toFixed?.(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
