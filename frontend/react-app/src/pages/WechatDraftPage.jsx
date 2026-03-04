/**
 * 公众号草稿独立页面：草稿列表、详情预览、新建/编辑草稿（通过创建任务）
 */
import { useState, useEffect, useCallback } from 'react'
import { useToast } from '../components/ToastModal'
import { formatWechatMpError } from '../utils/wechatMpError'
import TaskMetadataFormFields from '../components/task/TaskMetadataFormFields'
import HtmlPreview from '../components/HtmlPreview'
import WechatDraftEditor from '../components/WechatDraftEditor'
import WechatOutboundIpHint from '../components/WechatOutboundIpHint'
import WechatMaterialImagePicker from '../components/WechatMaterialImagePicker'
import TaskListByTypePanel from '../components/TaskListByTypePanel'
import { getDefaultMetadata } from '../components/task/taskFormUtils'
import { WECHAT_MP_DRAFT_TASK_TYPE, prepareMetadataForSubmitAsync, htmlToMd } from '../utils/mdToHtml'

const WECHAT_MP_API = {
  drafts: (params = {}) => {
    const q = new URLSearchParams({
      offset: String(params.offset ?? 0),
      count: String(params.count ?? 20),
      no_content: String(params.no_content ?? 1),
    })
    return fetch(`/api/wechat-mp/drafts?${q}`).then((r) => r.json())
  },
  draftDetail: (mediaId) =>
    fetch(`/api/wechat-mp/drafts/detail?media_id=${encodeURIComponent(mediaId)}`).then((r) => r.json()),
  uploadCover: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch('/api/wechat-mp/upload-cover', { method: 'POST', body: form }).then((r) => r.json())
  },
}

export default function WechatDraftPage() {
  const toast = useToast()
  const [drafts, setDrafts] = useState([])
  const [draftsLoading, setDraftsLoading] = useState(false)
  const [draftsError, setDraftsError] = useState(null)
  const [selectedMediaId, setSelectedMediaId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [taskTypeSchema, setTaskTypeSchema] = useState(null)
  const [formModalMode, setFormModalMode] = useState(null)
  const [formMetadata, setFormMetadata] = useState({})
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [coverUploading, setCoverUploading] = useState(false)

  const loadDrafts = useCallback(async () => {
    setDraftsLoading(true)
    setDraftsError(null)
    try {
      const res = await fetch(
        `/api/wechat-mp/drafts?offset=0&count=50&no_content=1`
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setDraftsError(data.detail || data.message || `HTTP ${res.status}`)
        setDrafts([])
        return
      }
      if (data.success === true) {
        const list = Array.isArray(data.item) ? data.item : []
        setDrafts(list)
        setSelectedMediaId((prev) => (prev != null ? prev : (list.length > 0 ? list[0]?.media_id ?? null : null)))
      } else {
        setDraftsError(data.detail || data.message || '获取草稿列表失败')
        setDrafts([])
      }
    } catch (e) {
      setDraftsError(e?.message || '网络错误')
      setDrafts([])
    }
    setDraftsLoading(false)
  }, [])

  /** 刷新列表并同步当前选中草稿的详情（正文、摘要、作者等） */
  const refreshListAndDetail = useCallback(async () => {
    await loadDrafts()
    if (!selectedMediaId) return
    setDetailLoading(true)
    try {
      const d = await WECHAT_MP_API.draftDetail(selectedMediaId)
      if (d?.success && d?.draft) setDetail(d.draft)
      else setDetail(null)
    } catch {
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }, [loadDrafts, selectedMediaId])

  useEffect(() => {
    loadDrafts()
  }, [loadDrafts])

  useEffect(() => {
    fetch('/api/task-queue/task-types')
      .then((r) => r.json())
      .then((d) => {
        const list = d.task_types || []
        const wechat = list.find((t) => t.type === 'wechat_mp_draft')
        if (wechat?.metadata_schema) setTaskTypeSchema(wechat.metadata_schema)
      })
      .catch(() => setTaskTypeSchema(null))
  }, [])

  useEffect(() => {
    if (!selectedMediaId) {
      setDetail(null)
      setDetailLoading(false)
      return
    }
    setDetailLoading(true)
    setDetail(null)
    WECHAT_MP_API.draftDetail(selectedMediaId)
      .then((d) => {
        if (d.success && d.draft) setDetail(d.draft)
        else setDetail(null)
      })
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false))
  }, [selectedMediaId])

  const openAddForm = () => {
    setFormMetadata({ ...(getDefaultMetadata(taskTypeSchema) || {}), operation: 'add' })
    setFormModalMode('add')
  }

  const openEditForm = () => {
    if (!detail) return
    const news = detail?.news_item?.[0]
    const mediaId = (selectedMediaId ?? detail?.media_id ?? '').toString().trim()
    setFormMetadata({
      operation: 'update',
      media_id: mediaId,
      title: news?.title ?? '',
      content: htmlToMd(news?.content ?? ''),
      author: news?.author ?? '',
      digest: news?.digest ?? '',
      content_source_url: news?.content_source_url ?? '',
      thumb_media_id: news?.thumb_media_id ?? '',
    })
    setFormModalMode('update')
  }

  const closeForm = () => {
    setFormModalMode(null)
    setFormMetadata({})
  }

  const handleFormSubmit = async (e) => {
    e.preventDefault()
    const schema = taskTypeSchema || {}
    for (const [key, spec] of Object.entries(schema)) {
      if (spec?.required) {
        const v = formMetadata[key]
        if (v === undefined || v === null || (typeof v === 'string' && !v.trim())) {
          toast.warning(`请填写必填项: ${spec.description || key}`)
          return
        }
      }
    }
    if (formMetadata.operation === 'add' && !(formMetadata.thumb_media_id || '').trim()) {
      toast.warning('新建草稿请先上传封面图')
      return
    }
    setFormSubmitting(true)
    try {
      const metadataToSend = await prepareMetadataForSubmitAsync(WECHAT_MP_DRAFT_TASK_TYPE, formMetadata)
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'wechat_mp_draft',
          priority: 2,
          max_retries: 3,
          metadata: metadataToSend,
        }),
      })
      const data = await res.json()
      if (data.success) {
        toast.info('任务已创建，可在任务管理中查看执行状态')
        closeForm()
        loadDrafts()
      } else {
        throw new Error(data.detail || data.message || '创建失败')
      }
    } catch (err) {
      toast.error('创建任务失败: ' + (err?.message || String(err)))
    }
    setFormSubmitting(false)
  }

  const schema = taskTypeSchema || {}
  const news = detail?.news_item?.[0]

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="shrink-0 px-6 py-4 border-b border-border flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">公众号草稿</h1>
        <button
          onClick={openAddForm}
          className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium"
        >
          + 新建草稿
        </button>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* 左侧：草稿列表 */}
        <div className="w-80 shrink-0 border-r border-border flex flex-col overflow-hidden">
          <div className="px-3 py-2 border-b border-border flex items-center justify-between gap-2">
            <span className="text-xs text-muted">点击条目在右侧预览</span>
            <button
              type="button"
              onClick={refreshListAndDetail}
              disabled={draftsLoading}
              className="shrink-0 p-1.5 rounded border border-border text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50"
              title="从微信公众号同步最新草稿列表；若已选草稿则同步其正文、摘要、作者等详情"
            >
              ↻
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {draftsLoading ? (
              <div className="py-8 text-center text-muted text-sm">加载中...</div>
            ) : draftsError ? (
              <div className="py-6 px-3 text-center">
                <p className="text-sm text-red-400/90 mb-2">加载失败</p>
                <p className="text-xs text-muted break-words">{draftsError}</p>
                <button
                  type="button"
                  onClick={loadDrafts}
                  className="mt-3 px-3 py-1.5 text-xs border border-border rounded text-muted hover:text-fg"
                >
                  重试
                </button>
              </div>
            ) : !drafts.length ? (
              <div className="py-8 text-center text-muted text-sm">暂无草稿</div>
            ) : (
              <div className="space-y-1">
                {drafts.map((item) => {
                  const title =
                    item?.content?.news_item?.[0]?.title || item?.media_id?.slice(0, 12) || '无标题'
                  const isSelected = item?.media_id === selectedMediaId
                  return (
                    <button
                      key={item?.media_id}
                      type="button"
                      onClick={() => setSelectedMediaId(item?.media_id ?? null)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                        isSelected
                          ? 'bg-accent/20 text-accent border border-accent/40'
                          : 'text-muted hover:bg-white/5 hover:text-fg border border-transparent'
                      }`}
                    >
                      <div className="font-medium truncate">{title}</div>
                      <div className="text-xs text-muted truncate mt-0.5">
                        {item?.media_id}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* 中间：详情预览 + 右侧：公众号草稿任务 */}
        <div className="flex-1 flex min-w-0 overflow-hidden">
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-white/[0.02]">
          {!selectedMediaId ? (
            <div className="flex-1 flex items-center justify-center text-muted text-sm">
              请在左侧选择一篇草稿查看预览
            </div>
          ) : detailLoading ? (
            <div className="flex-1 flex items-center justify-center text-muted text-sm">
              加载中...
            </div>
          ) : !detail ? (
            <div className="flex-1 flex items-center justify-center text-red-400/80 text-sm">
              加载失败或草稿不存在
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-2xl mx-auto space-y-6">
                <div className="flex items-center justify-between gap-4">
                  <h2 className="text-lg font-semibold text-white truncate flex-1">
                    {news?.title ?? '无标题'}
                  </h2>
                  <button
                    type="button"
                    onClick={openEditForm}
                    className="shrink-0 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium"
                  >
                    编辑（创建更新任务）
                  </button>
                </div>
                {news?.thumb_media_id && (
                  <div>
                    <div className="text-muted text-xs mb-1">封面</div>
                    <img
                      src={`/api/wechat-mp/cover-image?media_id=${encodeURIComponent(news.thumb_media_id)}`}
                      alt="封面"
                      className="w-full h-auto object-cover rounded-lg border border-border"
                    />
                  </div>
                )}
                {news?.author && (
                  <div>
                    <div className="text-muted text-xs mb-1">作者</div>
                    <div className="rounded-lg p-4 border-2 border-[#d0d7de] shadow-sm bg-[#f6f8fa] text-[#24292f]">
                      {news.author}
                    </div>
                  </div>
                )}
                {news?.digest && (
                  <div>
                    <div className="text-muted text-xs mb-1">摘要</div>
                    <div className="rounded-lg p-4 border-2 border-[#d0d7de] shadow-sm bg-[#f6f8fa] text-[#24292f]">
                      {news.digest}
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-muted text-xs mb-1">正文</div>
                  <HtmlPreview
                    html={news?.content ?? ''}
                    className="rounded-lg p-4 border-2 border-[#d0d7de] shadow-sm"
                  />
                </div>
                <div className="text-xs text-muted">
                  media_id: <code className="text-cyan-400/90">{detail?.media_id}</code>
                </div>
              </div>
            </div>
          )}
          </div>
          <div className="w-80 shrink-0 border-l border-border overflow-y-auto bg-white/[0.02]">
            <TaskListByTypePanel
              taskType="wechat_mp_draft"
              title="公众号草稿任务"
              emptyText="暂无公众号草稿任务"
            />
          </div>
        </div>
      </div>

      {/* 新建/编辑草稿表单弹窗 */}
      {formModalMode && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={closeForm}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-5xl h-[95vh] max-h-[95vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-white">
                {formModalMode === 'add' ? '新建草稿（创建任务）' : '编辑草稿（创建更新任务）'}
              </h3>
              <button
                type="button"
                onClick={closeForm}
                className="text-muted hover:text-fg text-2xl leading-none"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleFormSubmit} className="flex flex-col flex-1 min-h-0 overflow-hidden">
              <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
              <WechatOutboundIpHint />
              <TaskMetadataFormFields
                schema={schema}
                metadata={formMetadata}
                setMetadata={setFormMetadata}
                fieldIdPrefix="wechat-draft-form"
                customFieldRender={(fieldKey, { value, onChange }) => {
                  if (fieldKey === 'content')
                    return (
                      <WechatDraftEditor
                        value={value ?? ''}
                        onChange={onChange}
                        placeholder="支持 **加粗**、# 标题、列表、[链接](url)、![图片](url)"
                      />
                    )
                  if (fieldKey === 'media_id' && formModalMode === 'update') {
                    const mid = (formMetadata?.media_id ?? value ?? '').toString().trim()
                    const title = (formMetadata?.title ?? '').toString().trim()
                    if (!mid) return null
                    return (
                      <div className="space-y-1">
                        <label className="block text-sm text-muted">要更新的草稿</label>
                        <p className="text-sm text-white py-2 px-3 rounded-lg bg-white/5 border border-border">
                          {title ? <span className="font-medium">{title}</span> : null}
                          {title && mid ? ' · ' : null}
                          <code className="text-cyan-300 text-xs break-all">{mid}</code>
                        </p>
                        <p className="text-xs text-muted">media_id 来自当前选中的草稿</p>
                      </div>
                    )
                  }
                  if (fieldKey === 'digest') {
                    const DIGEST_MAX = 120
                    const text = (formMetadata?.digest ?? value ?? '').toString()
                    const len = text.length
                    const over = len > DIGEST_MAX
                    return (
                      <div className="space-y-1">
                        <label className="block text-sm text-muted mb-1">摘要（不超过 120 字，超限接口报 45004）</label>
                        <textarea
                          value={text}
                          onChange={(e) => setFormMetadata((m) => ({ ...m, digest: e.target.value }))}
                          placeholder="选填，不超过 120 字"
                          rows={3}
                          className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none resize-y min-h-[72px]"
                        />
                        <div className="text-xs">
                          <span className={over ? 'text-amber-400' : 'text-muted'}>
                            {len} / {DIGEST_MAX} 字
                            {over && ' · 超过 120 字，接口可能报 45004'}
                          </span>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <div>
                <label className="block text-sm text-muted mb-1">封面{formModalMode === 'add' ? ' *' : ''}</label>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
                  className="w-full text-sm text-muted file:mr-3 file:py-2 file:px-3 file:rounded file:border-0 file:bg-accent file:text-white file:cursor-pointer"
                  disabled={coverUploading}
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    setCoverUploading(true)
                    try {
                      const data = await WECHAT_MP_API.uploadCover(file)
                      if (data.success && data.media_id) {
                        setFormMetadata((m) => ({ ...m, thumb_media_id: data.media_id }))
                        toast.info('封面上传成功')
                      } else throw new Error(data.detail || '上传失败')
                    } catch (err) {
                      toast.error(formatWechatMpError('封面上传失败', err))
                    }
                    setCoverUploading(false)
                    e.target.value = ''
                  }}
                />
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <WechatMaterialImagePicker onSelect={(mediaId) => setFormMetadata((m) => ({ ...m, thumb_media_id: mediaId }))} />
                  <span className="text-xs text-muted">或填写 media_id：</span>
                  <input
                    type="text"
                    value={formMetadata?.thumb_media_id ?? ''}
                    onChange={e => setFormMetadata((m) => ({ ...m, thumb_media_id: e.target.value.trim() || undefined }))}
                    placeholder="粘贴 media_id"
                    className="flex-1 min-w-[120px] px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none text-sm"
                  />
                </div>
                {formMetadata.thumb_media_id && (
                  <div className="mt-2 flex items-start gap-3">
                    <img
                      src={`/api/wechat-mp/cover-image?media_id=${encodeURIComponent(formMetadata.thumb_media_id)}`}
                      alt="封面预览"
                      className="w-20 h-20 object-cover rounded border border-border shrink-0"
                    />
                    <p className="text-xs text-green-400/90 pt-1">
                      封面 media_id: {formMetadata.thumb_media_id}
                    </p>
                  </div>
                )}
                <p className="mt-1 text-xs text-amber-400/90">支持 JPG/PNG，WebP 自动转 PNG；≤2MB；也可直接填已有素材的 media_id{formModalMode === 'update' ? '，可重新上传替换' : ''}</p>
              </div>
              </div>
              <div className="shrink-0 flex gap-3 px-6 py-4 border-t border-border bg-surface">
                <button
                  type="button"
                  onClick={closeForm}
                  className="flex-1 px-4 py-2 border border-border rounded-lg text-muted hover:text-fg"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50"
                >
                  {formSubmitting ? '提交中...' : '创建任务'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
