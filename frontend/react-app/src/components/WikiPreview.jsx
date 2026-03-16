/**
 * MediaWiki wikitext 预览组件。
 * 仅使用 MediaWiki parse API 将 wikitext 解析为 HTML 渲染，永不转 Markdown。
 * API 失败时显示原始 wikitext（pre 块）。
 */
import { useState, useEffect, useRef } from 'react'
import WechatDraftPreview from './WechatDraftPreview'
import { useToast } from './ToastModal'
import { wikiToMd, wikitextLinksToHtml } from '../utils/wikiMdConvert'
import { parseWikiPageTitleFromUrl } from '../config/mediawiki'
import './WikiPreview.css'

function WikiPreviewFallbackLinks({ html, className, onWikiLinkClick, wikiBaseUrl }) {
  const handleClick = (e) => {
    if (!onWikiLinkClick) return
    const a = e.target?.closest?.('a')
    if (!a?.href) return
    const title = parseWikiPageTitleFromUrl(a.href, wikiBaseUrl)
    if (title) {
      e.preventDefault()
      onWikiLinkClick(title)
    }
  }
  return (
    <div
      className={`min-h-full p-4 text-sm text-muted whitespace-pre-wrap break-words font-mono bg-black/20 rounded overflow-x-auto [&_a]:text-cyan-400 [&_a]:underline [&_a:hover]:text-cyan-300 ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: html }}
      onClick={onWikiLinkClick ? handleClick : undefined}
    />
  )
}

const PARSE_DEBOUNCE_MS = 400

/**
 * @param {Object} props
 * @param {string} [props.wikiText] - MediaWiki wikitext
 * @param {string} [props.className] - 容器额外类名
 * @param {'light'|'dark'} [props.theme='light'] - 预览主题
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考（传入 Markdown）
 * @param {(content: string) => void} [props.onSendToArticle] - 加入写作助手（传入 Markdown）
 * @param {(pageTitle: string) => void} [props.onWikiLinkClick] - 点击本站 Wiki 链接时回调，用于在应用内打开
 * @param {boolean} [props.hideActions=false] - 隐藏底部操作按钮（由父组件提供时使用）
 * @param {boolean} [props.useParseApi=true] - 是否使用 parse API 预览
 * @param {'mediawiki'|'wikipedia'} [props.wikiSource='mediawiki'] - Wiki 来源，wikipedia 时用 /api/wikipedia/parse
 * @param {string} [props.wikiLang='zh'] - Wikipedia 语言（仅 wikiSource=wikipedia 时生效）
 */
export default function WikiPreview({
  wikiText = '',
  className = '',
  theme = 'light',
  onAddToReference,
  onSendToArticle,
  onWikiLinkClick,
  hideActions = false,
  useParseApi = true,
  wikiSource = 'mediawiki',
  wikiLang = 'zh',
}) {
  const toast = useToast()
  const [parsedHtml, setParsedHtml] = useState(null)
  const [parseFailed, setParseFailed] = useState(false)
  const [baseUrl, setBaseUrl] = useState('')
  const abortRef = useRef(null)

  const trimmedWiki = (wikiText || '').trim()
  const mdForActions = trimmedWiki ? wikiToMd(wikiText) : ''
  const hasActions = !hideActions && (onAddToReference || onSendToArticle || trimmedWiki)

  useEffect(() => {
    if (!trimmedWiki) {
      setParsedHtml(null)
      setParseFailed(false)
      return
    }
    if (!useParseApi) {
      setParsedHtml(null)
      setParseFailed(true)
      return
    }
    setParseFailed(false)
    const parseUrl = wikiSource === 'wikipedia' ? '/api/wikipedia/parse' : '/api/mediawiki/parse'
    const parseBody = wikiSource === 'wikipedia'
      ? { wikitext: wikiText, lang: wikiLang }
      : { wikitext: wikiText }
    const baseUrlPath = wikiSource === 'wikipedia' ? '/api/wikipedia/base-url' : '/api/mediawiki/base-url'
    const baseUrlParams = wikiSource === 'wikipedia' ? `?lang=${encodeURIComponent(wikiLang)}` : ''
    const timer = setTimeout(async () => {
      if (abortRef.current) abortRef.current.abort()
      abortRef.current = new AbortController()
      const signal = abortRef.current.signal
      try {
        const res = await fetch(parseUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parseBody),
          signal,
        })
        const data = await res.json().catch(() => ({}))
        if (res.ok && data?.success && data?.html) {
          setParsedHtml(data.html)
          if (data?.base_url) setBaseUrl(data.base_url)
        } else {
          setParsedHtml(null)
          setParseFailed(true)
          const msg = data?.detail || (res.ok ? '解析返回空' : `HTTP ${res.status}`)
          const src = wikiSource === 'wikipedia' ? 'Wikipedia' : 'MediaWiki'
          toast?.warning?.(`${src} 解析失败: ${msg}`)
        }
      } catch (err) {
        if (err?.name !== 'AbortError') {
          setParsedHtml(null)
          setParseFailed(true)
          const src = wikiSource === 'wikipedia' ? 'Wikipedia' : 'MediaWiki'
          toast?.warning?.(`${src} 解析失败: ${err?.message || err}`)
        }
      } finally {
        if (abortRef.current?.signal === signal) {
          abortRef.current = null
        }
      }
    }, PARSE_DEBOUNCE_MS)
    return () => {
      clearTimeout(timer)
      if (abortRef.current) {
        abortRef.current.abort()
      }
    }
  }, [wikiText, useParseApi, toast, wikiSource, wikiLang])

  // parse 失败或未启用时获取 base_url，用于将 [[xxx]] 转为可点击链接
  useEffect(() => {
    const needFallback = parseFailed || !useParseApi
    if (!needFallback || !trimmedWiki || baseUrl) return
    const path = wikiSource === 'wikipedia' ? `/api/wikipedia/base-url?lang=${encodeURIComponent(wikiLang)}` : '/api/mediawiki/base-url'
    fetch(path)
      .then((r) => r.json())
      .then((d) => d?.base_url && setBaseUrl(d.base_url))
      .catch(() => {})
  }, [parseFailed, useParseApi, baseUrl, trimmedWiki, wikiSource, wikiLang])

  const useHtmlPreview = parsedHtml != null && parsedHtml.length > 0

  return (
    <div className="flex flex-col min-h-0">
      {useHtmlPreview ? (
        <div className={`wiki-preview-html min-h-full ${className}`.trim()}>
          <WechatDraftPreview
            html={parsedHtml}
            theme={theme}
            className={className}
            onWikiLinkClick={onWikiLinkClick}
            wikiBaseUrl={baseUrl || undefined}
          />
        </div>
      ) : parseFailed || !useParseApi ? (
        <WikiPreviewFallbackLinks
          html={trimmedWiki ? wikitextLinksToHtml(trimmedWiki, baseUrl) : '(空)'}
          className={className}
          onWikiLinkClick={onWikiLinkClick}
          wikiBaseUrl={baseUrl || undefined}
        />
      ) : (
        <div className={`min-h-full p-4 ${className}`.trim()}>
          <p className="text-xs text-muted animate-pulse">解析中…</p>
        </div>
      )}
      {hasActions && (
        <div className="shrink-0 flex flex-wrap gap-2 mt-2">
          {trimmedWiki && (
            <button
              type="button"
              onClick={() => {
                const copy = (text) => {
                  if (navigator.clipboard?.writeText) {
                    navigator.clipboard.writeText(text).then(
                      () => toast?.info?.('已复制到剪贴板'),
                      () => fallbackCopy(text)
                    )
                  } else {
                    fallbackCopy(text)
                  }
                }
                const fallbackCopy = (text) => {
                  try {
                    const ta = document.createElement('textarea')
                    ta.value = text
                    ta.style.position = 'fixed'
                    ta.style.opacity = '0'
                    document.body.appendChild(ta)
                    ta.select()
                    document.execCommand('copy')
                    document.body.removeChild(ta)
                    toast?.info?.('已复制到剪贴板')
                  } catch {
                    toast?.error?.('复制失败')
                  }
                }
                copy(trimmedWiki)
              }}
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
            >
              复制 Wikitext
            </button>
          )}
          {onSendToArticle && (
            <button
              type="button"
              onClick={() => mdForActions && onSendToArticle(mdForActions)}
              disabled={!mdForActions}
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              加入写作助手
            </button>
          )}
          {onAddToReference && (
            <button
              type="button"
              onClick={() => mdForActions && onAddToReference(mdForActions)}
              disabled={!mdForActions}
              className="px-2.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              添加到参考
            </button>
          )}
        </div>
      )}
    </div>
  )
}
