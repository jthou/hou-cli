import { useState, useEffect } from 'react'

/**
 * 获取可选模型列表（具体模型名）
 * @returns {{ models: Array<{value: string, label: string}>, loading: boolean }}
 */
export function useSelectableModels() {
  const [models, setModels] = useState([
    { value: 'auto', label: '智能选择' },
  ])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch('/api/models/selectable')
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled && d.success && Array.isArray(d.models)) {
          setModels(d.models)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setModels([{ value: 'auto', label: '智能选择' }])
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  return { models, loading }
}
