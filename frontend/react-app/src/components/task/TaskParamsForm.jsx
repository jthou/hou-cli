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
import { formatWechatMpError } from '../../utils/wechatMpError'
import { prepareWechatCoverFile } from '../../utils/wechatCoverCompress'
import { mdToHtmlForWechat } from '../../utils/mdToHtml'

const inputCls = 'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none'
const labelCls = 'block text-sm text-muted mb-1'

/** 复制按钮，用于公众号表单各字段旁 */
function CopyBtn({ text, asHtml = false, label = '复制', toast }) {
  const handleCopy = () => {
    if (!text) {
      toast?.warning?.('暂无内容')
      return
    }
    const doCopy = () => {
      if (asHtml && typeof text === 'string' && text.includes('<')) {
        // 包裹为完整 HTML 文档，部分编辑器（如公众号）解析粘贴时更易保留样式
        const wrapped = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>${text}</body></html>`
        return navigator.clipboard.write([
          new ClipboardItem({
            'text/html': new Blob([wrapped], { type: 'text/html' }),
            'text/plain': new Blob([text.replace(/<[^>]+>/g, '')], { type: 'text/plain' }),
          }),
        ])
      }
      return navigator.clipboard.writeText(text)
    }
    doCopy().then(
      () => toast?.info?.(`已复制${label}，可粘贴到公众号对应位置`),
      () => toast?.error?.('复制失败')
    )
  }
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="shrink-0 px-2.5 py-1.5 text-xs rounded border border-border text-muted hover:bg-white/10 hover:text-fg"
      title={`复制${label}`}
    >
      复制
    </button>
  )
}

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
  // 写作助手场景：各字段旁的生成按钮 { title?: ReactNode, digest?: ReactNode }；封面前的三步流程 coverBeforeContent
  fieldActions,
  coverBeforeContent,
  // 不渲染的字段（如写作助手场景隐藏 author，默认老猴）
  fieldsToHide,
}) {
  const toast = useToast()
  const [coverUploading, setCoverUploading] = useState(false)
  const [draftList, setDraftList] = useState([])
  const [draftsLoading, setDraftsLoading] = useState(false)
  const [materialItems, setMaterialItems] = useState([])
  const [materialsLoading, setMaterialsLoading] = useState(false)

  const isWechatDraft = taskType === 'wechat_mp_draft' && (metadata?.operation === 'add' || !metadata?.operation)
  const isWechatUpdate = taskType === 'wechat_mp_draft' && metadata?.operation === 'update'

  useEffect(() => {
    if (!isWechatDraft) return
    setMaterialsLoading(true)
    fetch('/api/wechat-mp/materials/images?offset=0&count=12')
      .then((r) => r.json())
      .then((d) => {
        if (d?.success && Array.isArray(d?.item)) setMaterialItems(d.item)
        else setMaterialItems([])
      })
      .catch(() => setMaterialItems([]))
      .finally(() => setMaterialsLoading(false))
  }, [isWechatDraft])

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

  const customFieldRender = (fieldKey, { value, onChange, label, required: fieldRequired }) => {
    if (fieldKey === 'title' && isWechatDraft) {
      const text = (metadata?.title ?? value ?? '').toString()
      return (
        <div>
          <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
            <label className={labelCls + ' mb-0'}>
              {label || '标题'}
              {fieldRequired ? ' *' : '（选填，留空则草稿箱内显示为「未命名草稿」）'}
            </label>
            <div className="flex items-center gap-2">
              {fieldActions?.title}
              <CopyBtn text={text} label="标题" toast={toast} />
            </div>
          </div>
          <input
            value={text}
            onChange={(e) => setMetadata((m) => ({ ...m, title: e.target.value }))}
            placeholder="公众号图文标题"
            className={inputCls}
          />
        </div>
      )
    }
    if (fieldKey === 'author' && isWechatDraft) {
      const text = (metadata?.author ?? value ?? '').toString()
      return (
        <div>
          <div className="flex items-center justify-between gap-2 mb-1">
            <label className={labelCls + ' mb-0'}>{label || '作者'}</label>
            <CopyBtn text={text} label="作者" toast={toast} />
          </div>
          <input
            value={text}
            onChange={(e) => setMetadata((m) => ({ ...m, author: e.target.value }))}
            placeholder="选填"
            className={inputCls}
          />
        </div>
      )
    }
    if (fieldKey === 'content' && taskType === 'wechat_mp_draft') {
      const md = value ?? ''
      const html = md ? mdToHtmlForWechat(md) : ''
      return (
        <div>
          <div className="flex items-center justify-between gap-2 mb-1">
            <label className={labelCls + ' mb-0'}>正文（Markdown）</label>
            <CopyBtn text={html} asHtml label="正文" toast={toast} />
          </div>
          <WechatDraftEditor value={md} onChange={onChange} hideLabel />
        </div>
      )
    }
    if (fieldKey === 'digest' && taskType === 'wechat_mp_draft') {
      const DIGEST_MAX = 120
      const text = (metadata?.digest ?? value ?? '').toString()
      const len = text.length
      const over = len > DIGEST_MAX
      return (
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
            <label className="block text-sm text-muted mb-0">摘要（不超过 120 字，超限接口报 45004）</label>
            <div className="flex items-center gap-2">
              {fieldActions?.digest}
              <CopyBtn text={text} label="摘要" toast={toast} />
            </div>
          </div>
          <textarea
            value={text}
            onChange={(e) => setMetadata((m) => ({ ...m, digest: e.target.value }))}
            placeholder="选填，不超过 120 字"
            rows={3}
            className={`${inputCls} resize-y min-h-[72px]`}
          />
          <div className="flex items-center justify-between text-xs">
            <span className={over ? 'text-amber-400' : 'text-muted'}>
              {len} / {DIGEST_MAX} 字
              {over && ' · 超过 120 字，接口可能报 45004'}
            </span>
          </div>
        </div>
      )
    }
    if (fieldKey === 'media_id' && isWechatUpdate) {
      const mediaId = (metadata?.media_id ?? value ?? '').trim()
      const title = (metadata?.title ?? '').toString().trim()
      // 已有 media_id（从列表点击条目进入编辑）：只读展示，作为上下文输入
      if (mediaId) {
        return (
          <div className="space-y-1">
            <label className="block text-sm text-muted">要更新的草稿</label>
            <p className="text-sm text-white py-2 px-3 rounded-lg bg-white/5 border border-border">
              {title ? <span className="font-medium">{title}</span> : null}
              {title && mediaId ? ' · ' : null}
              <code className="text-cyan-300 text-xs break-all">{mediaId}</code>
            </p>
            <p className="text-xs text-muted">media_id 来自当前选中的草稿，无需选择或填写</p>
          </div>
        )
      }
      // 无 media_id（如从「创建任务」选更新草稿）：从草稿列表选择
      return (
        <div className="space-y-2">
          <label className="block text-sm text-muted mb-1">选择要更新的草稿 *</label>
          <p className="text-xs text-muted mb-1">从当前草稿列表选择</p>
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
            <option value="">请选择…</option>
            {draftList.map((item) => {
              const mid = item?.media_id ?? ''
              const itemTitle = (item?.content?.news_item?.[0]?.title || mid?.slice(0, 16) || '无标题').slice(0, 28)
              return (
                <option key={mid} value={mid}>
                  {itemTitle}{mid ? ` · ${mid.slice(0, 12)}` : ''}
                </option>
              )
            })}
          </select>
          {draftsLoading && <p className="text-xs text-muted">加载草稿列表中…</p>}
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
          fieldsToHide={fieldsToHide ?? (taskType === 'url_to_wiki' && !metadata?.translate ? ['language'] : [])}
          enableMediaWikiPasteImage={taskType === 'mediawiki_write'}
        />
      )}

      {isWechatDraft && typeof onCoverUpload === 'function' && (
        <div>
          <label className={labelCls}>封面（选填，同步到草稿箱后可在微信后台再补）</label>
          {coverBeforeContent}
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
                const toSend = await prepareWechatCoverFile(file)
                const data = await onCoverUpload(toSend)
                if (data?.success && data?.media_id) {
                  setMetadata(m => ({ ...m, thumb_media_id: data.media_id }))
                  toast.info('封面上传成功')
                } else throw new Error(data?.detail || '上传失败')
              } catch (err) {
                toast.error(formatWechatMpError('封面上传失败', err))
              }
              setCoverUploading(false)
              e.target.value = ''
            }}
          />
          <div className="mt-2 space-y-2">
            {(materialsLoading || materialItems.length > 0) && (
              <>
                <div className="text-xs text-muted">已有素材（点击选择）：</div>
                {materialsLoading ? (
                  <p className="text-xs text-muted">加载中…</p>
                ) : (
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
                {materialItems.map((it) => (
                  <button
                    key={it.media_id}
                    type="button"
                    onClick={() => setMetadata(m => ({ ...m, thumb_media_id: it.media_id }))}
                    className={`rounded-lg border-2 overflow-hidden hover:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-colors ${(metadata?.thumb_media_id || '') === it.media_id ? 'border-accent ring-1 ring-accent' : 'border-border'}`}
                  >
                    <img
                      src={`/api/wechat-mp/cover-image?media_id=${encodeURIComponent(it.media_id)}`}
                      alt={it.name || it.media_id}
                      className="w-full aspect-square object-cover"
                    />
                  </button>
                ))}
              </div>
                )}
              </>
            )}
            <div className="flex items-center gap-2 flex-wrap">
              <WechatMaterialImagePicker onSelect={(mediaId) => setMetadata(m => ({ ...m, thumb_media_id: mediaId }))} />
              <span className="text-xs text-muted">或填写 media_id：</span>
              <input
                type="text"
                value={metadata?.thumb_media_id ?? ''}
                onChange={e => setMetadata(m => ({ ...m, thumb_media_id: e.target.value.trim() || undefined }))}
                placeholder="粘贴 media_id"
                className={`${inputCls} flex-1 min-w-[120px]`}
              />
            </div>
          </div>
          {metadata?.thumb_media_id && (
            <div className="mt-2 flex items-start gap-3">
              <img
                src={`/api/wechat-mp/cover-image?media_id=${encodeURIComponent(metadata.thumb_media_id)}`}
                alt="封面预览"
                className="w-20 h-20 object-cover rounded border border-border shrink-0"
              />
              <div className="flex flex-col gap-1">
                <p className="text-xs text-green-400/90">封面 media_id: {metadata.thumb_media_id}</p>
                <a
                  href={`/api/wechat-mp/cover-image?media_id=${encodeURIComponent(metadata.thumb_media_id)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-accent hover:underline"
                >
                  下载封面
                </a>
              </div>
            </div>
          )}
          <p className="mt-1 text-xs text-amber-400/90">支持 JPG/PNG/WebP；微信封面限 2MB，超出将自动压缩后再传；也可直接填已有素材的 media_id</p>
        </div>
      )}

      {taskType === 'wechat_mp_draft' && <WechatOutboundIpHint />}

      {taskType === 'video_download' && (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!metadata?.cookies_from_extension}
            onChange={e => setMetadata(m => ({ ...m, cookies_from_extension: e.target.checked }))}
            className="text-accent focus:ring-accent rounded"
          />
          <span className="text-sm text-muted">使用扩展获取 cookies（YouTube/Bilibili 需登录时勾选，需安装 Hou CLI 扩展）</span>
        </label>
      )}

      {taskType === 'mediawiki_write' && (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!metadata?._contentIsMarkdown}
            onChange={e => setMetadata(m => ({ ...m, _contentIsMarkdown: e.target.checked }))}
            className="text-accent focus:ring-accent rounded"
          />
          <span className="text-sm text-muted">正文为 Markdown（提交时转为 Wiki 语法）</span>
        </label>
      )}

      {(taskType === 'url_to_wiki' || taskType === 'pdf_to_wiki') && (
        <>
          <p className="text-xs text-amber-400/90">下方分类即写入 Wiki 的标签，可添加、可删除；日、周、月按执行日期自动追加。</p>
          {taskType === 'pdf_to_wiki' && metadata?.extract_mode === 'vision' && (
            <p className="text-xs text-amber-300/95 mt-1">
              页图识别：按页调用视觉模型，耗时长、费用高；插图一般以文字描述为主，不会自动生成 Wiki 图片文件。
            </p>
          )}
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
