export type PipelineStatus = {
  running: boolean
  finished: boolean
  failed: boolean
  started_at?: string | null
  finished_at?: string | null
  command?: string | null
  start?: string | null
  end?: string | null
  step?: number | null
  step_total?: number | null
  step_message?: string | null
  month?: string | null
  month_i?: number | null
  month_n?: number | null
  month_rows?: number | null
  month_dapps?: number | null
  month_duration?: string | null
  months_total?: number | null
  months_cached?: number | null
  months_todo?: number | null
  duration?: string | null
  eta_seconds?: number | null
  last_line?: string | null
  recent_months?: Array<Record<string, unknown>>
}

export type Meta = {
  dataVersion: number
  loadedAt: number
  monthRanges: { v1: { min: string | null; max: string | null }; v2: { min: string | null; max: string | null } }
  categories: string[]
  metrics: string[]
  tables: Array<{
    key: string
    dataset: string
    table: string
    rows: number
    columns: string[]
    size_bytes: number
    exists: boolean
  }>
  methodology: Record<string, { title: string; summary: string; sources: string[]; limitations: string[] }>
  pipeline: PipelineStatus
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${path}: ${text.slice(0, 200)}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  meta: () => get<Meta>('/api/meta'),
  schema: (params?: { dataset?: string; table?: string; profile?: string }) => {
    const q = new URLSearchParams()
    if (params?.dataset) q.set('dataset', params.dataset)
    if (params?.table) q.set('table', params.table)
    if (params?.profile) q.set('profile', params.profile)
    const s = q.toString()
    return get<any>(`/api/schema${s ? `?${s}` : ''}`)
  },
  table: (dataset: string, name: string, params: Record<string, string | number>) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => q.set(k, String(v)))
    return get<any>(`/api/table/${dataset}/${name}?${q}`)
  },
  dapps: (params: Record<string, string | number>) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== '' && v != null) q.set(k, String(v)) })
    return get<{ dapps: any[] }>(`/api/dapps?${q}`)
  },
  dapp: (slug: string) => get<any>(`/api/dapp/${encodeURIComponent(slug)}`),
  overlap: () => get<any>('/api/compare/overlap'),
  ecosystem: (metric: string, start?: string, end?: string) => {
    const q = new URLSearchParams({ metric })
    if (start) q.set('start', start)
    if (end) q.set('end', end)
    return get<any>(`/api/compare/ecosystem?${q}`)
  },
  scatter: (metric: string, start?: string, end?: string) => {
    const q = new URLSearchParams({ metric })
    if (start) q.set('start', start)
    if (end) q.set('end', end)
    return get<any>(`/api/compare/scatter?${q}`)
  },
  ratioHist: (metric: string) => get<any>(`/api/compare/ratio-hist?metric=${metric}`),
  categories: () => get<any>('/api/compare/categories'),
  disagreements: (metric: string) => get<any>(`/api/compare/disagreements?metric=${metric}`),
  coverage: () => get<any>('/api/compare/coverage'),
  categoryMonth: (start?: string, end?: string) => {
    const q = new URLSearchParams()
    if (start) q.set('start', start)
    if (end) q.set('end', end)
    return get<any>(`/api/ecosystem/category-month?${q}`)
  },
  concentration: (scope: string, metric: string, category_group?: string) => {
    const q = new URLSearchParams({ scope, metric })
    if (category_group) q.set('category_group', category_group)
    return get<any>(`/api/ecosystem/concentration?${q}`)
  },
  lifecycle: () => get<any>('/api/ecosystem/lifecycle'),
  top: (dataset: string, metric: string, month?: string) => {
    const q = new URLSearchParams({ dataset, metric })
    if (month) q.set('month', month)
    return get<any>(`/api/ecosystem/top?${q}`)
  },
  variationsDist: (dataset: string, metric: string, group_by = 'category_group') =>
    get<any>(`/api/variations/distributions?dataset=${dataset}&metric=${metric}&group_by=${group_by}`),
  volatility: (dataset: string, metric: string) =>
    get<any>(`/api/variations/volatility?dataset=${dataset}&metric=${metric}`),
  heavyImpact: () => get<any>('/api/variations/heavy-impact'),
  attribution: () => get<any>('/api/variations/attribution'),
  pipeline: () => get<PipelineStatus>('/api/pipeline'),
}

export function fmtNum(n: number | null | undefined, digits = 0): string {
  if (n == null || Number.isNaN(n)) return '—'
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B'
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'k'
  return n.toLocaleString(undefined, { maximumFractionDigits: digits })
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  return (n * 100).toFixed(1) + '%'
}

export function monthLabel(m: string | number | Date | null | undefined): string {
  if (m == null || m === '') return ''
  const s = typeof m === 'string' ? m : m instanceof Date ? m.toISOString() : String(m)
  return s.slice(0, 7)
}
