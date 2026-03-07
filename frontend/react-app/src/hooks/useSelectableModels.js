import { useState, useEffect } from 'react'

/**
 * 获取可选模型列表，按供应商分组
 * @returns {{
 *   models: Array<{value: string, label: string}>,
 *   providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>,
 *   vision_providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>,
 *   vision_default: string,
 *   loading: boolean
 * }}
 */
export function useSelectableModels() {
  const [models, setModels] = useState([])
  const [defaultModel, setDefaultModel] = useState('')
  const [providers, setProviders] = useState([])
  const [vision_providers, setVisionProviders] = useState([])
  const [vision_default, setVisionDefault] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch('/api/models/selectable')
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled && d.success) {
          if (Array.isArray(d.models)) setModels(d.models)
          if (d.default_model) setDefaultModel(d.default_model)
          if (Array.isArray(d.providers)) setProviders(d.providers)
          const vp = d.vision_providers
          if (vp?.providers) setVisionProviders(vp.providers)
          if (vp?.default) setVisionDefault(vp.default)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setModels([])
          setDefaultModel('')
          setProviders([])
          setVisionProviders([])
          setVisionDefault('')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  return { models, defaultModel, providers, vision_providers, vision_default, loading }
}
