/**
 * 生成前步骤：将用户输入扩展为提示词
 * 时间：2025-03-18；理由：图片/漫画页左侧空间大，生成前加一步；方法：调用 expand-prompt API
 * 时间：2025-03-18；理由：扩写不覆盖输入，单独输出区域；方法：expandedValue/onExpandedChange
 * 时间：2025-03-18；理由：统一「先选平台再选模型」UI；方法：ModelSelector + model 参数
 */
import { useState, useEffect } from 'react'
import { useToast } from '../ToastModal'
import ModelSelector from '../ModelSelector'

export default function PromptExpandStep({ taskType, value, expandedValue, onExpandedChange, providers = [], defaultModel = '', loading = false }) {
  const toast = useToast()
  const [expanding, setExpanding] = useState(false)
  const [expandModel, setExpandModel] = useState(defaultModel)
  useEffect(() => {
    if (defaultModel && !expandModel) setExpandModel(defaultModel)
  }, [defaultModel])

  const isImage = taskType === 'image_generation'
  const stepLabel = isImage ? '生成提示词' : '扩写为文章'
  const buttonLabel = isImage ? '生成提示词' : '扩写为文章'

  const handleExpand = async () => {
    const input = (value || '').trim()
    if (!input) {
      toast.warning(isImage ? '请先填写图片描述' : '请先填写故事想法或文章')
      return
    }
    setExpanding(true)
    try {
      const body = { task_type: taskType, input }
      if ((expandModel || '').trim()) body.model = expandModel.trim()
      const res = await fetch('/api/task-queue/expand-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (data.success && data.prompt) {
        onExpandedChange(data.prompt)
        toast.success('已生成，可编辑后提交')
      } else {
        throw new Error(data.detail || data.error || '生成失败')
      }
    } catch (err) {
      toast.error(err?.message || '生成失败')
    } finally {
      setExpanding(false)
    }
  }

  return (
    <div className="mt-4 p-4 rounded-lg border border-border bg-white/[0.02]">
      <h3 className="text-sm font-medium text-white mb-2">步骤 2：{stepLabel}</h3>
      <p className="text-xs text-muted mb-3">
        {isImage ? '将上方描述扩展为详细图片提示词，可编辑后提交。' : '将上方想法扩写成完整故事，可编辑后提交。'}
      </p>
      {providers.length > 0 && (
        <div className="mb-3">
          <ModelSelector
            value={expandModel || defaultModel}
            onChange={setExpandModel}
            providers={providers}
            loading={loading}
          />
        </div>
      )}
      <button
        type="button"
        onClick={handleExpand}
        disabled={expanding}
        className="px-4 py-2 bg-accent/80 hover:bg-accent text-white rounded-lg text-sm font-medium disabled:opacity-50"
      >
        {expanding ? '生成中…' : buttonLabel}
      </button>
      {(expandedValue ?? '').trim() && (
        <div className="mt-4">
          <label className="block text-xs text-muted mb-2">扩写结果（可编辑）</label>
          <textarea
            value={expandedValue ?? ''}
            onChange={e => onExpandedChange(e.target.value)}
            rows={taskType === 'comic' ? 10 : 5}
            className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none resize-y"
            placeholder={isImage ? '扩写后的图片提示词' : '扩写后的故事'}
          />
        </div>
      )}
    </div>
  )
}
