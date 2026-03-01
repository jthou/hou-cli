/**
 * 验证公众号正文 HTML 一定带内联 style（mdToHtmlForWechat 输出）。
 * 在 Node 下无 DOMParser，会走正则兜底，输出仍须含 style。
 * 运行：cd frontend/react-app && node scripts/verify-wechat-html.mjs
 */
import { mdToHtmlForWechat, prepareWechatDraftMetadata } from '../src/utils/mdToHtml.js'

const md = `# 主标题

第一段普通文字。

## 二级标题

第二段含 **粗体** 与 _斜体_。

- 列表一
- 列表二
`

function run() {
  const html = mdToHtmlForWechat(md)
  if (!html || typeof html !== 'string') {
    console.error('mdToHtmlForWechat returned falsy or non-string')
    process.exit(1)
  }
  const checks = [
    ['style="', 'output must contain inline style attribute'],
    ['font-size:22px', 'h1 style'],
    ['font-size:16px', 'p style'],
    ['font-size:19px', 'h2 style'],
    ['font-weight:600', 'strong/heading style'],
  ]
  for (const [substr, desc] of checks) {
    if (!html.includes(substr)) {
      console.error('FAIL: missing', desc, '(', substr, ')')
      process.exit(1)
    }
  }
  const prepared = prepareWechatDraftMetadata({ content: md, title: 'Test', author: 'A' })
  if (!prepared.content || !prepared.content.includes('style="')) {
    console.error('FAIL: prepareWechatDraftMetadata content missing inline styles')
    process.exit(1)
  }
  console.log('OK: wechat HTML has required inline styles')
  process.exit(0)
}

run()
