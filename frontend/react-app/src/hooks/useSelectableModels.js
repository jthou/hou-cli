import { useState, useEffect } from 'react'

/**
 * 获取可选模型列表，按供应商分组
 * @param {{ context?: 'article_writing' | 'work_assistant' }} [options] - context=article_writing 时使用写作助手默认模型
 * @returns {{
 *   models: Array<{value: string, label: string}>,
 *   providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>,
 *   vision_providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>,
 *   vision_default: string,
 *   loading: boolean
 * }}
 */
export function useSelectableModels(options = {}) {
  const { context } = options
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
          const def = context === 'article_writing' && d.article_writing_default_model
            ? d.article_writing_default_model
            : d.default_model
          if (def) setDefaultModel(def)
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
