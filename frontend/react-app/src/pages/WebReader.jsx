import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { htmlToMd } from '../utils/mdToHtml'
import { mdToWiki } from '../utils/wikiMdConvert'
import MarkdownPreview from '../components/MarkdownPreview'
import { useToast } from '../components/ToastModal'

const REQUEST_ID_PREFIX = 'web-reader-'

export default function WebReader() {
  const navigate = useNavigate()
  const toast = useToast()
  const [urlInput, setUrlInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [loadingOcr, setLoadingOcr] = useState(false)
  const [extensionReady, setExtensionReady] = useState(false)
  const [viewMode, setViewMode] = useState('markdown') // 'text' | 'html' | 'markdown'
  const [mdViewMode, setMdViewMode] = useState('preview') // 'preview' | 'edit'（截图场景下右侧 Markdown 的展示模式）
  const [mdContent, setMdContent] = useState('') // 可编辑的 Markdown 内容（截图场景）
  const [mwDialogOpen, setMwDialogOpen] = useState(false)
  const [mwTitle, setMwTitle] = useState('')
  const [mwSummary, setMwSummary] = useState('')
  const [mwSubmitting, setMwSubmitting] = useState(false)
  const timeoutRef = useRef(null)
  const ocrRequestedRef = useRef(null)

  const buildStyledHtml = (d) => {
    const base = d.baseUrl || d.url || ''
    const styles = [
      ...(d.stylesheets || []).map((href) => `<link rel="stylesheet" href="${href.replace(/"/g, '&quot;')}">`),
      ...(d.inlineStyles || []).map((s) => `<style>${s}</style>`),
    ].join('\n')
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><base href="${base.replace(/"/g, '&quot;')}">${styles}</head><body style="margin:1em;max-width:800px;margin-left:auto;margin-right:auto;">${d.html || ''}</body></html>`
  }

  /** 左侧 iframe 用：完整页面或正文，注入链接点击拦截 */
  const buildHtmlForPreviewIframe = (d) => {
    const base = d.fullPageHtml || d.html
    const baseUrl = d.baseUrl || d.url || ''
    let html = base
    if (!html) return ''
    // 确保有 base 标签，便于相对链接解析
    if (baseUrl && !/<\s*base\s+[^>]*href/i.test(html)) {
      html = html.replace(/<head([^>]*)>/i, '<head$1><base href="' + baseUrl.replace(/"/g, '&quot;') + '">')
    }
    const clickScript = `
      <script>
        document.addEventListener('click', function(e) {
          var a = e.target.closest('a');
          if (!a || !a.href) return;
          var raw = a.getAttribute('href') || '';
          if (raw.indexOf('javascript:') === 0 || raw.indexOf('#') === 0) return;
          var href = a.href;
          if (href.indexOf('http://') === 0 || href.indexOf('https://') === 0) {
            e.preventDefault();
            window.parent.postMessage({ type: 'HOU_CLI_IFRAME_LINK_CLICK', href: href }, '*');
          }
        }, true);
      <\/script>
    `
    return html.replace(/<\/body\s*>/i, clickScript + '</body>')
  }

  useEffect(() => {
    const check = () => {
      if (window.__HOU_CLI_EXTENSION_LOADED) {
        setExtensionReady(true)
        return true
      }
      return false
    }
    if (check()) return
    const handler = (e) => {
      if (e.data?.type === 'HOU_CLI_PONG') {
        setExtensionReady(true)
        window.removeEventListener('message', handler)
      }
    }
    window.addEventListener('message', handler)
    const ping = () => {
      if (window.__HOU_CLI_EXTENSION_LOADED) return
      window.postMessage({ type: 'HOU_CLI_PING' }, '*')
    }
    ping()
    const id = setInterval(() => {
      if (check()) {
        clearInterval(id)
        return
      }
      ping()
    }, 600)
    const stop = setTimeout(() => clearInterval(id), 15000)
    return () => {
      clearInterval(id)
      clearTimeout(stop)
      window.removeEventListener('message', handler)
    }
  }, [])

  const doRead = useCallback((url) => {
    const u = (url || '').trim()
    if (!u || (!u.startsWith('http://') && !u.startsWith('https://'))) return
    setUrlInput(u)
    setError(null)
    setData(null)
    setLoadingOcr(false)
    ocrRequestedRef.current = null
    setLoading(true)
    const requestId = REQUEST_ID_PREFIX + Date.now()
    window.postMessage(
      { type: 'HOU_CLI_FETCH', url: u, requestId, apiBase: window.location.origin },
      '*'
    )
    timeoutRef.current = setTimeout(() => {
      timeoutRef.current = null
      setLoading((prev) => {
        if (prev) setError('扩展无响应（60 秒超时），请刷新页面后重试')
        return false
      })
    }, 60000)
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === 'HOU_CLI_IFRAME_LINK_CLICK' && e.data?.href) {
        doRead(e.data.href)
        return
      }
      if (e.data?.type !== 'HOU_CLI_FETCH_RESULT' || !e.data?.requestId?.startsWith(REQUEST_ID_PREFIX)) return
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      setLoading(false)
      if (e.data.success) {
        const d = e.data.data
        const augmented = d
          ? { ...d, markdown: d.html ? htmlToMd(d.html) : (d.content || '') }
          : null
        setData(augmented)
        setError(null)
        if (augmented?.pendingOcr) ocrRequestedRef.current = null
      } else {
        setError(e.data.error || '抓取失败')
        setData(null)
      }
    }
    window.addEventListener('message', handler)
    return () => {
      window.removeEventListener('message', handler)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [doRead])

  useEffect(() => {
    const md = data?.markdown ?? ''
    setMdContent(md)
  }, [data?.markdown])

  useEffect(() => {
    const images = data?.screenshots || []
    if (!images.length || !data?.pendingOcr || ocrRequestedRef.current === images[0]) return
    ocrRequestedRef.current = images[0]
    setLoadingOcr(true)
    const apiBase = window.location.origin
    const ocrUrl = `${apiBase}/api/web-reader/ocr`
    const ocrOne = (img) =>
      fetch(ocrUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: img }),
      }).then((r) => r.json())
    Promise.all(images.map(ocrOne))
      .then((results) => {
        const texts = results.map((r) => (r.success ? (r.text || '').trim() : '')).filter(Boolean)
        const text = texts.join('\n\n')
        const html = text ? text.split(/\n\n+/).map((p) => '<p>' + p.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</p>').join('\n') : ''
        setData((prev) => ({
          ...prev,
          content: text,
          html,
          markdown: text,
          pendingOcr: false,
        }))
      })
      .catch((err) => {
        setError('OCR 识别失败：' + (err?.message || '请确认后端已启动'))
        setData((prev) => ({ ...prev, pendingOcr: false }))
      })
      .finally(() => setLoadingOcr(false))
  }, [data?.screenshots, data?.pendingOcr])

  const handleAddToArticle = () => {
    const content = (mdViewMode === 'edit' ? mdContent : data?.markdown) ?? ''
    if (!content.trim()) {
      toast?.warning?.('当前无内容可加入')
      return
    }
    navigate('/article-writing', { state: { initialMarkdown: content.trim() } })
  }

  const submitMediaWiki = async () => {
    const title = (mwTitle || '').trim()
    if (!title) {
      toast?.warning?.('请输入页面标题')
      return
    }
    const content = (mdViewMode === 'edit' ? mdContent : data?.markdown) ?? ''
    if (!content.trim()) {
      toast?.warning?.('当前无内容可发布')
      return
    }
    setMwSubmitting(true)
    try {
      const wikitext = mdToWiki(content.trim())
      const res = await fetch(`/api/mediawiki/pages/${encodeURIComponent(title)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: wikitext, summary: (mwSummary || '').trim() || undefined }),
      })
      const resData = await res.json().catch(() => ({}))
      if (res.ok && resData.success) {
        toast?.info?.('已发布到 MediaWiki')
        setMwDialogOpen(false)
        setMwTitle('')
        setMwSummary('')
      } else {
        toast?.error?.(resData.detail || resData.message || '发布失败')
      }
    } catch (e) {
      toast?.error?.(e?.message || '发布失败')
    }
    setMwSubmitting(false)
  }

  const handleRead = (e) => {
    e.preventDefault()
    const url = (urlInput || '').trim()
    if (!url) {
      setError('请输入 URL')
      return
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setError('请使用完整的 http:// 或 https:// URL')
      return
    }
    doRead(url)
  }

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">网页阅读</h1>
        <p className="mt-1 text-sm text-muted">
          通过浏览器扩展抓取网页正文，复用当前浏览器的登录态（Cookie）。
          微信读书使用截图 + Qwen-VL OCR 提取，需配置 BAILIAN_API_KEY。
        </p>
      </header>

      <div className="flex-1 overflow-hidden flex">
        <div className="flex flex-col w-[45%] min-w-[320px] max-w-[600px] border-r border-border shrink-0">
          <div className="shrink-0 p-4 space-y-2">
            <form onSubmit={handleRead} className="flex gap-2">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/article"
                className="flex-1 min-w-0 px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-muted focus:border-accent focus:outline-none text-sm"
              />
              <button
                type="submit"
                disabled={loading || loadingOcr || !extensionReady}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 text-sm shrink-0"
              >
                {loading ? '抓取中…' : loadingOcr ? '识别中…' : !extensionReady ? '等待扩展…' : '读取'}
              </button>
            </form>
            {!extensionReady && (
              <div className="text-xs text-amber-400 space-y-1">
                <p>未检测到扩展。请确认：</p>
                <ul className="list-disc list-inside ml-1">
                  <li>已安装 Hou CLI 网页阅读助手扩展（chrome://extensions 加载 <code className="bg-white/5 px-1 rounded">extension</code> 目录）</li>
                  <li>本页通过 <code className="bg-white/5 px-1 rounded">localhost</code> 或 <code className="bg-white/5 px-1 rounded">127.0.0.1</code> 访问（当前：<code className="bg-white/5 px-1 rounded">{window.location.host}</code>）</li>
                  <li>在 Chrome/Edge 中打开，非编辑器内置浏览器</li>
                  <li>安装后<strong>刷新本页面</strong></li>
                </ul>
                <button
                  type="button"
                  onClick={() => window.postMessage({ type: 'HOU_CLI_PING' }, '*')}
                  className="mt-2 px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-amber-300"
                >
                  再次检测
                </button>
              </div>
            )}
            {error && <p className="text-xs text-red-400">{error}</p>}
          </div>
          <div className="flex-1 min-h-0 border-t border-border overflow-auto w-full">
            {data?.screenshots?.length ? (
              <div className="w-full py-2 space-y-2">
                {data.screenshots.map((src, i) => (
                  <img
                    key={i}
                    src={src}
                    alt={`页面截图 ${i + 1}`}
                    className="w-full max-w-full h-auto object-contain bg-white rounded block"
                  />
                ))}
                {data?.pendingOcr && (
                  <p className="text-xs text-muted text-center">
                    共 {data.screenshots.length} 张截图，正在识别…
                  </p>
                )}
              </div>
            ) : (data?.html || data?.fullPageHtml) ? (
              <iframe
                title="原始网页"
                srcDoc={buildHtmlForPreviewIframe(data)}
                sandbox="allow-same-origin allow-scripts"
                className="w-full h-full border-0 bg-white"
              />
            ) : (
              <div className="h-full flex items-center justify-center p-6 text-sm text-muted text-center">
                {loading ? (
                  '正在抓取…'
                ) : (
                  <>
                    读取网页后，原始页面将在此显示。
                    <br />
                    微信读书会显示截图，普通网页显示 HTML 预览。
                  </>
                )}
              </div>
            )}
          </div>
          <div className="shrink-0 p-3 text-xs text-muted border-t border-border space-y-1">
            <p><strong>安装扩展：</strong>chrome://extensions → 开发者模式 → 加载 <code className="bg-white/5 px-1 rounded">extension</code> 目录</p>
            <p>需在 Chrome/Edge 中打开本页，编辑器内置浏览器无法使用扩展。</p>
          </div>
        </div>

        <div className="min-w-0 flex-1 overflow-y-auto bg-white/[0.02] p-6">
          {!data && !loading && !error && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              输入 URL 并点击「读取网页」，正文将在此展示。
            </div>
          )}
          {loading && (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              正在抓取截图…
            </div>
          )}
          {data && !loading && (
            <div className="flex flex-col h-full">
              <div className="shrink-0 flex items-center justify-between gap-4 mb-4">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-white truncate">{data.title || '无标题'}</h2>
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline break-all"
                  >
                    {data.url}
                  </a>
                </div>
                {data.screenshots?.length ? (
                  <div className="flex gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => setMdViewMode('preview')}
                      className={`px-3 py-1.5 rounded-lg text-sm ${mdViewMode === 'preview' ? 'bg-accent text-white' : 'bg-white/5 text-muted hover:text-white'}`}
                    >
                      预览
                    </button>
                    <button
                      type="button"
                      onClick={() => setMdViewMode('edit')}
                      className={`px-3 py-1.5 rounded-lg text-sm ${mdViewMode === 'edit' ? 'bg-accent text-white' : 'bg-white/5 text-muted hover:text-white'}`}
                    >
                      编辑
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => setViewMode('markdown')}
                      className={`px-3 py-1.5 rounded-lg text-sm ${viewMode === 'markdown' ? 'bg-accent text-white' : 'bg-white/5 text-muted hover:text-white'}`}
                    >
                      Markdown 预览
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode('text')}
                      className={`px-3 py-1.5 rounded-lg text-sm ${viewMode === 'text' ? 'bg-accent text-white' : 'bg-white/5 text-muted hover:text-white'}`}
                    >
                      纯文本
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode('html')}
                      className={`px-3 py-1.5 rounded-lg text-sm ${viewMode === 'html' ? 'bg-accent text-white' : 'bg-white/5 text-muted hover:text-white'}`}
                    >
                      原文样式
                    </button>
                  </div>
                )}
              </div>
              <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-border bg-white flex flex-col">
                {loadingOcr ? (
                  <div className="h-full flex items-center justify-center text-sm text-muted">
                    正在识别文字…
                  </div>
                ) : data.screenshots?.length ? (
                  <>
                    <div className="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col">
                      {mdViewMode === 'edit' ? (
                        <textarea
                          value={mdContent}
                          onChange={(e) => setMdContent(e.target.value)}
                          placeholder="在此编辑 Markdown 内容…"
                          className="flex-1 min-h-[200px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-mono leading-relaxed"
                          spellCheck={false}
                        />
                      ) : (
                        <MarkdownPreview markdown={mdContent || ''} className="min-h-full" theme="dark" />
                      )}
                    </div>
                    <div className="shrink-0 flex gap-3 px-4 py-3 border-t border-border bg-white/[0.02]">
                      <button
                        type="button"
                        onClick={handleAddToArticle}
                        className="flex-1 px-4 py-2 rounded-lg border border-border text-muted hover:text-fg hover:bg-white/5"
                      >
                        加入写文章
                      </button>
                      <button
                        type="button"
                        onClick={() => { setMwTitle(''); setMwSummary(''); setMwDialogOpen(true) }}
                        className="flex-1 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90"
                      >
                        写入 MediaWiki
                      </button>
                    </div>
                  </>
                ) : viewMode === 'markdown' ? (
                  <div className="h-full overflow-y-auto p-4">
                    <MarkdownPreview markdown={data.markdown || ''} className="min-h-full" theme="dark" />
                  </div>
                ) : viewMode === 'text' ? (
                  <div className="p-4 text-sm text-muted leading-relaxed whitespace-pre-wrap overflow-y-auto h-full">
                    {data.content || '无内容'}
                  </div>
                ) : data.html ? (
                  <iframe
                    title="原文样式"
                    srcDoc={buildStyledHtml(data)}
                    sandbox="allow-same-origin"
                    className="w-full h-full min-h-[400px] border-0 bg-white"
                  />
                ) : (
                  <div className="p-4 text-sm text-muted">无 HTML 内容，请使用纯文本或 Markdown 预览模式</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 发布到 MediaWiki 弹窗 */}
      {mwDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setMwDialogOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-center px-5 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-white">发布到 MediaWiki</h3>
              <button type="button" onClick={() => setMwDialogOpen(false)} className="text-muted hover:text-fg text-2xl leading-none">×</button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-xs text-muted">将 Markdown 转为 Wikitext 后发布到指定页面，不存在则创建。</p>
              <div>
                <label className="block text-sm text-muted mb-1">页面标题 *</label>
                <input
                  type="text"
                  value={mwTitle}
                  onChange={(e) => setMwTitle(e.target.value)}
                  placeholder="MediaWiki 页面标题"
                  className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">编辑摘要（选填）</label>
                <input
                  type="text"
                  value={mwSummary}
                  onChange={(e) => setMwSummary(e.target.value)}
                  placeholder="本次修改说明"
                  className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>
            <div className="shrink-0 flex gap-3 px-5 py-4 border-t border-border bg-surface">
              <button type="button" onClick={() => setMwDialogOpen(false)} className="flex-1 px-4 py-2 rounded-lg border border-border text-muted hover:text-fg">取消</button>
              <button type="button" onClick={submitMediaWiki} disabled={mwSubmitting || !mwTitle.trim()} className="flex-1 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 disabled:opacity-50">{mwSubmitting ? '发布中…' : '发布'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
