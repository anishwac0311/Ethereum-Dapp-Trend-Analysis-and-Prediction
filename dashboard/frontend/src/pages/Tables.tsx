import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api'
import { useFilters } from '../context/Filters'

export function Tables() {
  const { dataVersion, meta } = useFilters()
  const tables = meta?.tables?.filter(t => t.exists) || []
  const [dataset, setDataset] = useState('v2')
  const [table, setTable] = useState('dapp_panel')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<string | undefined>()
  const [order, setOrder] = useState<'asc' | 'desc'>('asc')
  const [search, setSearch] = useState('')
  const [filterCol, setFilterCol] = useState('')
  const [filterVal, setFilterVal] = useState('')

  const dsTables = tables.filter(t => t.dataset === dataset)

  const q = useQuery({
    queryKey: ['table', dataset, table, page, sort, order, search, filterCol, filterVal, dataVersion],
    queryFn: () => api.table(dataset, table, {
      page,
      page_size: 50,
      ...(sort ? { sort, order } : {}),
      ...(search ? { search } : {}),
      ...(filterCol && filterVal ? { filter_col: filterCol, filter_val: filterVal } : {}),
    }),
    enabled: !!table,
  })

  const totalPages = Math.max(1, Math.ceil((q.data?.total || 0) / 50))

  function toggleSort(col: string) {
    if (sort === col) setOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSort(col); setOrder('asc') }
    setPage(1)
  }

  function exportCsv() {
    if (!q.data?.rows?.length) return
    const cols = q.data.columns
    const lines = [cols.join(',')]
    for (const row of q.data.rows) {
      lines.push(cols.map((c: string) => {
        const v = row[c]
        if (v == null) return ''
        const s = String(v)
        return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s
      }).join(','))
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${dataset}_${table}_page${page}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="card" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
        <select className="select" value={dataset} onChange={e => {
          setDataset(e.target.value)
          const first = tables.find(t => t.dataset === e.target.value)
          if (first) setTable(first.table)
          setPage(1)
        }}>
          <option value="v1">v1</option>
          <option value="v2">v2</option>
        </select>
        <select className="select" value={table} onChange={e => { setTable(e.target.value); setPage(1) }}>
          {dsTables.map(t => (
            <option key={t.key} value={t.table}>{t.table} ({t.rows.toLocaleString()})</option>
          ))}
        </select>
        <input className="input" placeholder="Search all columns…" value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }} style={{ minWidth: 180 }} />
        <select className="select" value={filterCol} onChange={e => setFilterCol(e.target.value)}>
          <option value="">Filter column…</option>
          {(q.data?.columns || dsTables.find(t => t.table === table)?.columns || []).map((c: string) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <input className="input" placeholder="contains…" value={filterVal}
          onChange={e => { setFilterVal(e.target.value); setPage(1) }} disabled={!filterCol} />
        <button className="btn" onClick={exportCsv}>Export page CSV</button>
        <span className="muted" style={{ fontSize: 12 }}>
          {(q.data?.total ?? 0).toLocaleString()} rows · page {page}/{totalPages}
        </span>
      </div>

      <div className="card">
        {q.isLoading && <div className="muted">Loading…</div>}
        {q.error && <div style={{ color: 'var(--danger)' }}>{String(q.error)}</div>}
        {q.data && (
          <>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    {q.data.columns.map((c: string) => (
                      <th key={c} onClick={() => toggleSort(c)} title={q.data.descriptions?.[c] || ''}>
                        {c}{sort === c ? (order === 'asc' ? ' ↑' : ' ↓') : ''}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {q.data.rows.map((row: any, i: number) => (
                    <tr key={i}>
                      {q.data.columns.map((c: string) => (
                        <td key={c} className="mono">{formatCell(row[c])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center' }}>
              <button className="btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
              <button className="btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
              <span className="muted" style={{ fontSize: 12 }}>Hover column headers for descriptions</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function formatCell(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'number') return Number.isInteger(v) ? v.toLocaleString() : v.toPrecision(4)
  if (typeof v === 'boolean') return v ? 'true' : 'false'
  const s = String(v)
  return s.length > 48 ? s.slice(0, 45) + '…' : s
}
