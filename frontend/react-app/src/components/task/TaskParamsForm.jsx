/**
 * 任务参数表单：与「创建任务」/「编辑后重新执行」共用同一套 UI，保证一致性。
 * 含：schema 驱动的 TaskMetadataFormFields、公众号草稿正文+封面上传、MediaWiki 选项、Wiki 分类提示等。
 * 更新草稿时：media_id 用草稿列表选择，而非手输。
 */
import { useState, useEffect } from 'react'
import TaskMetadataFormFields from './TaskMetadataFormFields'
import WikiTitlePreviewHint from './WikiTitlePreviewHint'
import WechatDraftEditor from '../WechatDraftEditor'
import WechatOutboundIpHint from '../WechatOutboundIpHint'
import WechatMaterialImagePicker from '../WechatMaterialImagePicker'
import { useToast } from '../ToastModal'

const inputCls = 'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none'
const labelCls = 'block text-sm text-[#94a3b8] mb-1'

export default function TaskParamsForm({
  taskType,
  schema,
  metadata,
  setMetadata,
  fieldIdPrefix = 'task-params',
  fileUploadFields = undefined,
  isInputFileTask = false,
  inputFileAccept = '*',
  // 任务名称（可选，传入则展示）
  taskName = '',
  onTaskNameChange,
  taskNamePlaceholder = '留空自动生成',
  // 优先级 / 最大重试（可选）
  priority,
  onPriorityChange,
  maxRetries,
  onMaxRetriesChange,
  // 公众号草稿：封面上传回调 (file) => Promise<{ success, media_id? }>
  onCoverUpload,
}) {
  const toast = useToast()
  const [coverUploading, setCoverUploading] = useState(false)
  const [draftList, setDraftList] = useState([])
  const [draftsLoading, setDraftsLoading] = useState(false)

  const isWechatDraft = taskType === 'wechat_mp_draft' && (metadata?.operation === 'add' || !metadata?.operation)
  const isWechatUpdate = taskType === 'wechat_mp_draft' && metadata?.operation === 'update'

  useEffect(() => {
    if (!isWechatUpdate) return
    setDraftsLoading(true)
    fetch('/api/wechat-mp/drafts?offset=0&count=50&no_content=1')
      .then((r) => r.json())
      .then((d) => {
        if (d?.success && Array.isArray(d?.item)) setDraftList(d.item)
        else setDraftList([])
      })
      .catch(() => setDraftList([]))
      .finally(() => setDraftsLoading(false))
  }, [isWechatUpdate])

  const customFieldRender = (fieldKey, { value, onChange }) => {
    if (fieldKey === 'content' && isWechatDraft)
      return <WechatDraftEditor value={value ?? ''} onChange={onChange} />
    if (fieldKey === 'media_id' && isWechatUpdate) {
      const mediaId = (metadata?.media_id ?? value ?? '').trim()
      return (
        <div className="space-y-2">
          <select
            value={mediaId}
            onChange={(e) => {
              const v = e.target.value
              setMetadata((m) => ({ ...m, media_id: v || undefined }))
            }}
            disabled={draftsLoading}
            className={inputCls}
            required
          >
            <option value="">请选择要更新的草稿</option>
            {draftList.map((item) => {
              const mid = item?.media_id ?? ''
              const title = (item?.content?.news_item?.[0]?.title || mid?.slice(0, 16) || '无标题').slice(0, 28)
              return (
                <option key={mid} value={mid}>
                  {title}{mid ? ` · ${mid.slice(0, 12)}` : ''}
                </option>
              )
            })}
          </select>
          {draftsLoading && <p className="text-xs text-[#64748b]">加载草稿列表中…</p>}
          {!draftsLoading && draftList.length === 0 && <p className="text-xs text-amber-400/90">暂无草稿，请先新建草稿或到公众号草稿页查看</p>}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-4">
      {schema && Object.keys(schema).length > 0 && (
        <TaskMetadataFormFields
          schema={schema}
          metadata={metadata}
          setMetadata={setMetadata}
          fieldIdPrefix={fieldIdPrefix}
          isInputFileTask={isInputFileTask}
          inputFileAccept={inputFileAccept}
          fileUploadFields={fileUploadFields}
          customFieldRender={customFieldRender}
        />
      )}

      {isWechatDraft && typeof onCoverUpload === 'function' && (
        <div>
          <label className={labelCls}>封面</label>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
            className="w-full text-sm text-[#94a3b8] file:mr-3 file:py-2 file:px-3 file:rounded file:border-0 file:bg-accent file:text-white file:cursor-pointer"
            disabled={coverUploading}
            onChange={async (e) => {
              const file = e.target.files?.[0]
              if (!file) return
              setCoverUploading(true)
              try {
                const data = await onCoverUpload(file)
                if (data?.success && data?.media_id) {
                  setMetadata(m => ({ ...m, thumb_media_id: data.media_id }))
                  toast.info('封面上传成功')
                } else throw new Error(data?.detail || '上传失败')
              } catch (err) {
                toast.error('封面上传失败: ' + (err?.message || String(err)))
              }
              setCoverUploading(false)
              e.target.value = ''
            }}
          />
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <WechatMaterialImagePicker onSelect={(mediaId) => setMetadata(m => ({ ...m, thumb_media_id: mediaId }))} />
            <span className="text-xs text-[#64748b]">或填写 media_id：</span>
            <input
              type="text"
              value={metadata?.thumb_media_id ?? ''}
              onChange={e => setMetadata(m => ({ ...m, thumb_media_id: e.target.value.trim() || undefined }))}
              placeholder="粘贴 media_id"
              className={`${inputCls} flex-1 min-w-[120px]`}
            />
          </div>
          {metadata?.thumb_media_id && (
            <div className="mt-2 flex items-start gap-3">
              <img
                src={`/api/wechat-mp/cover-image?media_id=${encodeURIComponent(metadata.thumb_media_id)}`}
                alt="封面预览"
                className="w-20 h-20 object-cover rounded border border-border shrink-0"
              />
              <p className="text-xs text-green-400/90 pt-1">封面 media_id: {metadata.thumb_media_id}</p>
            </div>
          )}
          <p className="mt-1 text-xs text-amber-400/90">支持 JPG/PNG，WebP 将自动转为 PNG；≤2MB；也可直接填已有素材的 media_id</p>
        </div>
      )}

      {taskType === 'wechat_mp_draft' && <WechatOutboundIpHint />}

      {taskType === 'mediawiki_write' && (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!metadata?._contentIsMarkdown}
            onChange={e => setMetadata(m => ({ ...m, _contentIsMarkdown: e.target.checked }))}
            className="text-accent focus:ring-accent rounded"
          />
          <span className="text-sm text-[#94a3b8]">正文为 Markdown（提交时转为 Wiki 语法）</span>
        </label>
      )}

      {(taskType === 'url_to_wiki' || taskType === 'pdf_to_wiki') && (
        <>
          <p className="text-xs text-amber-400/90">下方分类即写入 Wiki 的标签，可添加、可删除；日、周、月按执行日期自动追加。</p>
          <WikiTitlePreviewHint taskType={taskType} metadata={metadata} />
        </>
      )}

      {onTaskNameChange != null && (
        <div>
          <label className={labelCls}>任务名称</label>
          <input
            type="text"
            value={taskName}
            onChange={e => onTaskNameChange(e.target.value)}
            placeholder={taskNamePlaceholder}
            className={inputCls}
          />
        </div>
      )}

      {(onPriorityChange != null || onMaxRetriesChange != null) && (
        <div className="grid grid-cols-2 gap-4">
          {onPriorityChange != null && (
            <div>
              <label className={labelCls}>优先级</label>
              <select
                value={priority ?? 2}
                onChange={e => onPriorityChange(Number(e.target.value))}
                className={inputCls}
              >
                <option value={1}>低 (1)</option>
                <option value={2}>普通 (2)</option>
                <option value={3}>高 (3)</option>
                <option value={4}>紧急 (4)</option>
              </select>
            </div>
          )}
          {onMaxRetriesChange != null && (
            <div>
              <label className={labelCls}>最大重试次数</label>
              <input
                type="number"
                min={0}
                max={99}
                value={maxRetries ?? 3}
                onChange={e => onMaxRetriesChange(Number(e.target.value) || 0)}
                className={inputCls}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
