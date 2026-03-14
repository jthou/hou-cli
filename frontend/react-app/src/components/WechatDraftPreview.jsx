/**
 * 公众号草稿正文 HTML 预览组件
 * 按 HTML 渲染正文内容，明亮风格；用内联样式固定背景与文字色，避免被全局/深色主题覆盖。
 * 支持 LaTeX 公式预览：$...$ 行内、$$...$$ 行间，由 KaTeX 渲染。
 */
import { useEffect, useRef } from 'react'
import { parseWikiPageTitleFromUrl } from '../config/mediawiki'
import renderMathInElement from 'katex/contrib/auto-render'
import 'katex/dist/katex.min.css'
import './WechatDraftPreview.css'

/** 根容器明亮风格（公众号预览用），不被全局 color/background 覆盖 */
const LIGHT_ROOT_STYLE = {
  backgroundColor: '#ffffff',
  color: '#24292f',
}

/** 深色主题时跟随应用主题，不强制白底 */
const DARK_ROOT_STYLE = {}

const KATEX_OPTIONS = {
  delimiters: [
    { left: '$$', right: '$$', display: true },
    { left: '$', right: '$', display: false },
  ],
  throwOnError: false,
}

/**
 * 从 Special:FilePath URL 解析出文件名。时间：2025-03-14；理由：Markdown 预览点击图片需区分已上传/未上传。
 */
function parseWikiFileNameFromFilePathUrl(src) {
  if (!src || typeof src !== 'string') return null
  const m = src.match(/Special:FilePath\/([^?#]+)/i)
  return m ? decodeURIComponent(m[1]) : null
}

/**
 * @param {Object} props
 * @param {string} [props.html] - 正文 HTML 字符串
 * @param {string} [props.className] - 容器额外类名
 * @param {'light'|'dark'} [props.theme='light'] - light=白底深色字（公众号风格），dark=跟随应用主题
 * @param {(pageTitle: string) => void} [props.onWikiLinkClick] - 点击本站 Wiki 链接时回调，传入页面标题；不传则按默认行为（新标签打开）
 * @param {string} [props.wikiBaseUrl] - Wiki 基础 URL，用于判断是否本站链接
 * @param {(e: Event, data: { src: string, srcRaw?: string, width: number, height: number, isWikiFile: boolean, wikiFileName?: string }) => void} [props.onImgClick] - 点击图片时回调；isWikiFile 表示已是 [[File:xxx]]
 */
export default function WechatDraftPreview({ html = '', className = '', theme = 'light', onWikiLinkClick, wikiBaseUrl, onImgClick }) {
  const containerRef = useRef(null)
  const trimmed = typeof html === 'string' ? html.trim() : ''
  const isDark = theme === 'dark'
  const rootStyle = isDark ? DARK_ROOT_STYLE : LIGHT_ROOT_STYLE
  const themeClass = isDark ? ' wechat-draft-preview--dark' : ''

  useEffect(() => {
    if (!containerRef.current || !trimmed) return
    renderMathInElement(containerRef.current, KATEX_OPTIONS)
  }, [trimmed])

  const handleClick = (e) => {
    const img = e.target?.closest?.('img')
    if (img?.src && onImgClick) {
      const src = img.src
      const srcRaw = img.getAttribute('src') || src
      const wikiFileName = parseWikiFileNameFromFilePathUrl(src)
      const isWikiFile = !!wikiFileName
      const w = img.offsetWidth || img.naturalWidth || 0
      const h = img.offsetHeight || img.naturalHeight || 0
      e.preventDefault()
      e.stopPropagation()
      onImgClick(e, { src, srcRaw, width: w, height: h, isWikiFile, wikiFileName: wikiFileName || undefined })
      return
    }
    if (!onWikiLinkClick) return
    const a = e.target?.closest?.('a')
    if (!a?.href) return
    const title = parseWikiPageTitleFromUrl(a.href, wikiBaseUrl)
    if (title) {
      e.preventDefault()
      onWikiLinkClick(title)
    }
  }

  if (!trimmed) {
    return (
      <div
        className={`wechat-draft-preview wechat-draft-preview--empty${themeClass} ${className}`.trim()}
        style={rootStyle}
      >
        <span className="wechat-draft-preview__placeholder">暂无正文</span>
      </div>
    )
  }
  return (
    <div
      ref={containerRef}
      className={`wechat-draft-preview${themeClass} ${onImgClick ? ' wechat-draft-preview--img-clickable' : ''} ${className}`.trim()}
      style={rootStyle}
      dangerouslySetInnerHTML={{ __html: trimmed }}
      onClick={onWikiLinkClick || onImgClick ? handleClick : undefined}
    />
  )
}
