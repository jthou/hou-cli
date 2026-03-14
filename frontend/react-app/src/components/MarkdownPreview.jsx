/**
 * 共用 Markdown 预览：接收 Markdown 文本，用与公众号草稿一致的样式渲染（mdToHtml + WechatDraftPreview）。
 * 写作助手页「文章预览」与公众号草稿「预览」均使用此组件，保证一致。
 */
import { useMemo } from 'react'
import WechatDraftPreview from './WechatDraftPreview'
import { mdToHtml } from '../utils/mdToHtml'

/**
 * @param {Object} props
 * @param {string} [props.markdown] - Markdown 文本
 * @param {string} [props.className] - 容器额外类名
 * @param {'light'|'dark'} [props.theme='light'] - 预览主题，dark 时跟随应用主题
 * @param {Function} [props.onImgClick] - 点击图片时回调，透传给 WechatDraftPreview
 */
export default function MarkdownPreview({ markdown = '', className = '', theme = 'light', onImgClick }) {
  const html = useMemo(() => mdToHtml(markdown || ''), [markdown])
  return <WechatDraftPreview html={html} className={className} theme={theme} onImgClick={onImgClick} />
}
