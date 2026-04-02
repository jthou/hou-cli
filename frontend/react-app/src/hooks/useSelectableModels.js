import { useState, useEffect } from 'react'

/**
 * 获取可选模型列表，按供应商分组
 * @param {{ context?: 'article_writing' | 'ppt_assistant' | 'work_assistant' }} [options] - 场景默认模型（见 /api/models/selectable）
 * @returns {{
 *   models: Array<{value: string, label: string}>,
 *   providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>,
 *   vision_providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>,
 *   vision_default: string,
 *   reasoningModel: string,
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
  const [reasoningModel, setReasoningModel] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch('/api/models/selectable')
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled && d.success) {
          if (Array.isArray(d.models)) setModels(d.models)
          let def = d.default_model
          if (context === 'article_writing' && d.article_writing_default_model) {
            def = d.article_writing_default_model
          } else if (context === 'ppt_assistant' && d.ppt_assistant_default_model) {
            def = d.ppt_assistant_default_model
          }
          if (def) setDefaultModel(def)
          if (Array.isArray(d.providers)) setProviders(d.providers)
          const vp = d.vision_providers
          if (vp?.providers) setVisionProviders(vp.providers)
          if (vp?.default) setVisionDefault(vp.default)
          if (typeof d.reasoning_model === 'string') setReasoningModel(d.reasoning_model)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setModels([])
          setDefaultModel('')
          setProviders([])
          setVisionProviders([])
          setVisionDefault('')
          setReasoningModel('')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [context])

  return {
    models,
    defaultModel,
    providers,
    vision_providers,
    vision_default,
    reasoningModel,
    loading,
  }
}
