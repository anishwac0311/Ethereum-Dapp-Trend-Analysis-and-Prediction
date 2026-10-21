import { useEffect, useRef, useState } from 'react'
import type { PipelineStatus } from '../api'

export function useLiveData(onVersionChange?: (v: number) => void) {
  const [dataVersion, setDataVersion] = useState(0)
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const cb = useRef(onVersionChange)
  cb.current = onVersionChange

  useEffect(() => {
    const es = new EventSource('/api/events')
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        if (data.type === 'hello' || data.type === 'ping') {
          if (data.dataVersion != null) setDataVersion(data.dataVersion)
          if (data.status) setPipeline(data.status)
        } else if (data.type === 'dataVersion') {
          setDataVersion(data.dataVersion)
          setToast(`Data reloaded (v${data.dataVersion})`)
          cb.current?.(data.dataVersion)
          setTimeout(() => setToast(null), 4000)
        } else if (data.type === 'pipelineStatus') {
          setPipeline(data.status)
          if (data.dataVersion != null) setDataVersion(data.dataVersion)
        }
      } catch { /* ignore */ }
    }
    es.onerror = () => { /* browser auto-reconnects */ }
    return () => es.close()
  }, [])

  return { dataVersion, pipeline, toast, clearToast: () => setToast(null) }
}
