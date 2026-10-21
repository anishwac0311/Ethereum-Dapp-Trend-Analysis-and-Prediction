import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Meta } from '../api'
import { useLiveData } from '../hooks/useLiveData'

export type FiltersState = {
  dataset: 'v1' | 'v2' | 'both'
  metric: string
  category: string
  start: string
  end: string
  setDataset: (d: FiltersState['dataset']) => void
  setMetric: (m: string) => void
  setCategory: (c: string) => void
  setStart: (s: string) => void
  setEnd: (e: string) => void
  meta: Meta | undefined
  dataVersion: number
  pipeline: ReturnType<typeof useLiveData>['pipeline']
  toast: string | null
}

const Ctx = createContext<FiltersState | null>(null)

export function FiltersProvider({ children }: { children: ReactNode }) {
  const live = useLiveData()
  const metaQ = useQuery({
    queryKey: ['meta', live.dataVersion],
    queryFn: api.meta,
    staleTime: 10_000,
  })

  const [dataset, setDataset] = useState<FiltersState['dataset']>('both')
  const [metric, setMetric] = useState('active_wallets')
  const [category, setCategory] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')

  // Initialize range from meta once
  const meta = metaQ.data
  useEffect(() => {
    if (!meta || start) return
    const mins = [meta.monthRanges.v1.min, meta.monthRanges.v2.min].filter(Boolean) as string[]
    const maxs = [meta.monthRanges.v1.max, meta.monthRanges.v2.max].filter(Boolean) as string[]
    if (mins.length) setStart(mins.sort()[0].slice(0, 10))
    if (maxs.length) setEnd(maxs.sort().reverse()[0].slice(0, 10))
  }, [meta, start])

  const value: FiltersState = {
    dataset, metric, category, start, end,
    setDataset, setMetric, setCategory, setStart, setEnd,
    meta,
    dataVersion: live.dataVersion || meta?.dataVersion || 0,
    pipeline: live.pipeline ?? meta?.pipeline ?? null,
    toast: live.toast,
  }

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useFilters() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useFilters outside provider')
  return ctx
}
