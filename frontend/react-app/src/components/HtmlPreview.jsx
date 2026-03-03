/**
 * 通用 HTML 预览组件：统一封装 WechatDraftPreview，便于在各处以相同风格渲染 HTML 正文。
 * - 微信草稿详情、任务结果中的 HTML 内容等都应使用此组件。
 */
import WechatDraftPreview from './WechatDraftPreview'

/**
 * @param {Object} props
 * @param {string} [props.html] - HTML 字符串
 * @param {string} [props.className] - 额外类名
 * @param {'light'|'dark'} [props.theme='light'] - light=固定白底深色字，dark=跟随应用主题
 */
export default function HtmlPreview({ html = '', className = '', theme = 'light' }) {
  return <WechatDraftPreview html={html} className={className} theme={theme} />
}

