/**
 * mdToHtmlCore 单元测试：Markdown → HTML 核心转换
 */
import { describe, it, expect } from 'vitest'
import { mdToHtmlCore, removeEmptyListItems } from './mdToHtmlCore.js'

describe('mdToHtmlCore', () => {
  it('空输入返回空字符串', () => {
    expect(mdToHtmlCore('')).toBe('')
    expect(mdToHtmlCore('   ')).toBe('')
    expect(mdToHtmlCore(null)).toBe('')
    expect(mdToHtmlCore(undefined)).toBe('')
  })

  it('非字符串返回空字符串', () => {
    expect(mdToHtmlCore(123)).toBe('')
    expect(mdToHtmlCore({})).toBe('')
  })

  it('普通段落转 p 标签', () => {
    const html = mdToHtmlCore('hello world')
    expect(html).toContain('<p>')
    expect(html).toContain('hello world')
    expect(html).toContain('</p>')
  })

  it('标题正确解析', () => {
    expect(mdToHtmlCore('# 一级')).toContain('<h1>')
    expect(mdToHtmlCore('## 二级')).toContain('<h2>')
    expect(mdToHtmlCore('### 三级')).toContain('<h3>')
    expect(mdToHtmlCore('#### 四级')).toContain('<h4>')
  })

  it('1. 开头解析为有序列表而非标题', () => {
    const html = mdToHtmlCore('1. 从"桌面软件"到"云端能力模块"')
    expect(html).toContain('<ol>')
    expect(html).toContain('<li>')
    expect(html).not.toContain('<h1>')
    expect(html).not.toContain('<h2>')
  })

  it('## 1. 开头解析为标题', () => {
    const html = mdToHtmlCore('## 1. 从"桌面软件"到"云端能力模块"')
    expect(html).toContain('<h2>')
    expect(html).toContain('</h2>')
    // marked 会将 " 转义为 &quot;，检查关键内容即可
    expect(html).toMatch(/1\.\s*从.*桌面软件.*到.*云端能力模块/)
  })

  it('无序列表', () => {
    const html = mdToHtmlCore('- 项目一\n- 项目二')
    expect(html).toContain('<ul>')
    expect(html).toContain('<li>')
    expect(html).toContain('项目一')
    expect(html).toContain('项目二')
  })

  it('粗体与斜体', () => {
    const html = mdToHtmlCore('**粗体** 与 *斜体*')
    expect(html).toContain('<strong>')
    expect(html).toContain('<em>')
  })

  it('链接', () => {
    const html = mdToHtmlCore('[链接](https://example.com)')
    expect(html).toContain('<a ')
    expect(html).toContain('href="https://example.com"')
  })

  it('代码块', () => {
    const html = mdToHtmlCore('```\ncode\n```')
    expect(html).toContain('<pre>')
    expect(html).toContain('<code>')
  })

  it('引用块', () => {
    const html = mdToHtmlCore('> 引用内容')
    expect(html).toContain('<blockquote>')
  })
})

describe('removeEmptyListItems', () => {
  it('移除空 li 标签', () => {
    const html = '<ul><li></li><li>有内容</li><li> </li></ul>'
    const out = removeEmptyListItems(html)
    expect(out).not.toContain('<li></li>')
    expect(out).not.toMatch(/<li[^>]*>\s*<\/li>/)
    expect(out).toContain('<li>有内容</li>')
  })

  it('移除带 style 的空 li', () => {
    const html = '<ul><li style="margin:0"></li><li>有内容</li></ul>'
    const out = removeEmptyListItems(html)
    expect(out).not.toMatch(/<li[^>]*>\s*<\/li>/)
    expect(out).toContain('<li>有内容</li>')
  })

  it('保留有内容的 li', () => {
    const html = '<ul><li>云计算平台提供弹性算力</li><li>专业算法库</li></ul>'
    const out = removeEmptyListItems(html)
    expect(out).toBe(html)
  })

  it('空 bullet 与有内容 bullet 混合', () => {
    const html = '<ul><li></li><li>云计算</li><li> </li><li>算法库</li></ul>'
    const out = removeEmptyListItems(html)
    expect(out).toContain('<li>云计算</li>')
    expect(out).toContain('<li>算法库</li>')
    expect((out.match(/<li/g) || []).length).toBe(2)
  })

  it('非字符串原样返回', () => {
    expect(removeEmptyListItems(null)).toBe(null)
    expect(removeEmptyListItems(undefined)).toBe(undefined)
  })
})

describe('mdToHtmlCore 与 removeEmptyListItems 集成', () => {
  it('含空列表项的 Markdown 转换后无空 bullet', () => {
    const md = `- 
- 云计算平台提供弹性算力
- 
- 专业算法库提供分析能力
`
    const html = mdToHtmlCore(md)
    expect(html).toContain('云计算平台提供弹性算力')
    expect(html).toContain('专业算法库提供分析能力')
    // 不应有空的 li
    expect(html).not.toMatch(/<li[^>]*>\s*<\/li>/)
  })

  it('多段落与列表混合', () => {
    const md = `# 主标题

第一段。

## 二级标题

- 列表一
- 列表二
`
    const html = mdToHtmlCore(md)
    expect(html).toContain('<h1>')
    expect(html).toContain('主标题')
    expect(html).toContain('<h2>')
    expect(html).toContain('二级标题')
    expect(html).toContain('列表一')
    expect(html).toContain('列表二')
  })
})
