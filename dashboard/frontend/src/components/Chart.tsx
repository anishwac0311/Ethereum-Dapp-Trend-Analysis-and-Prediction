import ReactECharts from 'echarts-for-react'

const baseText = '#94a3b8'
const axisLine = '#243049'

export const chartTheme = {
  backgroundColor: 'transparent',
  textStyle: { color: baseText, fontFamily: 'Inter, sans-serif' },
  legend: { textStyle: { color: baseText } },
  tooltip: {
    backgroundColor: '#121a2b',
    borderColor: '#243049',
    textStyle: { color: '#e8eef9' },
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: axisLine } },
    axisLabel: { color: baseText },
    splitLine: { lineStyle: { color: axisLine } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: axisLine } },
    axisLabel: { color: baseText },
    splitLine: { lineStyle: { color: '#1a2438' } },
  },
}

export function Chart({ option, height = 360, onEvents }: {
  option: Record<string, unknown>
  height?: number | string
  onEvents?: Record<string, (params: any) => void>
}) {
  const merged = {
    ...chartTheme,
    ...option,
    grid: { left: 56, right: 24, top: 48, bottom: 48, ...(option.grid as object || {}) },
  }
  return (
    <ReactECharts
      option={merged}
      style={{ height, width: '100%' }}
      notMerge
      lazyUpdate
      onEvents={onEvents}
    />
  )
}

export const COLORS = {
  v1: '#f59e0b',
  v2: '#34d399',
  accent: '#38bdf8',
  accent2: '#a78bfa',
  series: ['#38bdf8', '#a78bfa', '#34d399', '#f59e0b', '#f472b6', '#22d3ee', '#fb923c', '#4ade80'],
}
