/**
 * MediaWiki wikitext 预览组件。
 * 内部通过 wikiToMd 将 wikitext 转为 Markdown，再复用通用 MarkdownPreview 进行渲染，
 * 这样可与其它 Markdown 源的预览风格保持一致。
 */
import { useMemo } from 'react'
import MarkdownPreview from './MarkdownPreview'
import { wikiToMd } from '../utils/wikiMdConvert'

/**
 * @param {Object} props
 * @param {string} [props.wikiText] - MediaWiki wikitext
 * @param {string} [props.className] - 容器额外类名
 * @param {'light'|'dark'} [props.theme='light'] - 预览主题
 */
export default function WikiPreview({ wikiText = '', className = '', theme = 'light' }) {
  const markdown = useMemo(
    () => (wikiText ? wikiToMd(wikiText) : ''),
    [wikiText],
  )

  return <MarkdownPreview markdown={markdown} className={className} theme={theme} />
}

