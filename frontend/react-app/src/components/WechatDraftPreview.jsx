/**
 * 公众号草稿正文 HTML 预览组件
 * 按 HTML 渲染正文内容，明亮风格；用内联样式固定背景与文字色，避免被全局/深色主题覆盖。
 * 支持 LaTeX 公式预览：$...$ 行内、$$...$$ 行间，由 KaTeX 渲染。
 */
import { useEffect, useRef } from 'react'
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
 * @param {Object} props
 * @param {string} [props.html] - 正文 HTML 字符串
 * @param {string} [props.className] - 容器额外类名
 * @param {'light'|'dark'} [props.theme='light'] - light=白底深色字（公众号风格），dark=跟随应用主题
 */
export default function WechatDraftPreview({ html = '', className = '', theme = 'light' }) {
  const containerRef = useRef(null)
  const trimmed = typeof html === 'string' ? html.trim() : ''
  const isDark = theme === 'dark'
  const rootStyle = isDark ? DARK_ROOT_STYLE : LIGHT_ROOT_STYLE
  const themeClass = isDark ? ' wechat-draft-preview--dark' : ''

  useEffect(() => {
    if (!containerRef.current || !trimmed) return
    renderMathInElement(containerRef.current, KATEX_OPTIONS)
  }, [trimmed])

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
      className={`wechat-draft-preview${themeClass} ${className}`.trim()}
      style={rootStyle}
      dangerouslySetInnerHTML={{ __html: trimmed }}
    />
  )
}
