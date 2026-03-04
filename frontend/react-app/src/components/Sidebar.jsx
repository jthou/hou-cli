import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import BackendStatus from './BackendStatus'

// 分组：内容创作、常用工具、管道编排、设置
const navItems = [
  { path: '/tasks', icon: '📋', label: '任务管理', group: 'content' },
  { path: '/wechat-drafts', icon: '✏️', label: '公众号草稿', group: 'content' },
  { path: '/article-writing', icon: '✍️', label: '写文章', group: 'content' },
  { path: '/mediawiki-reader', icon: '📖', label: 'MediaWiki 阅读', group: 'content' },
  { path: '/web-reader', icon: '🌐', label: '网页阅读', group: 'content' },
  { path: '/video-download', icon: '⬇️', label: '视频下载', group: 'tools' },
  { path: '/video-extract-audio', icon: '🎧', label: '视频提取音频', group: 'tools' },
  { path: '/speech-to-text', icon: '🎤', label: '语音转文字', group: 'tools' },
  { path: '/url-to-wiki', icon: '📰', label: '网文抓取', group: 'tools' },
  { path: '/pdf-to-wiki', icon: '📄', label: 'PDF 转 Wiki', group: 'tools' },
  { path: '/pdf-reader', icon: '📘', label: 'PDF 阅读', group: 'tools' },
  { path: '/wiki-directory', icon: '📚', label: 'Wiki 目录刷新', group: 'tools' },
  { path: '/weather-query', icon: '🌤️', label: '天气查询', group: 'tools' },
  { path: '/web-search', icon: '🔍', label: '网页搜索', group: 'tools' },
  { path: '/settings/kanban', icon: '🗂️', label: '看板管理', group: 'settings' },
  { path: '/pipeline', icon: '🔀', label: '管道编排', group: 'pipeline' },
  { path: '/settings/general', icon: '🎨', label: '常规设置', group: 'settings' },
  { path: '/settings/storage', icon: '💾', label: '存储配置', group: 'settings' },
  { path: '/settings/llm-audit', icon: '📜', label: 'LLM 对话审计', group: 'settings' },
  { path: '/settings/system-prompt-audit', icon: '📋', label: '系统提示词审计', group: 'settings' },
  { path: '/settings/model-config-audit', icon: '🤖', label: '模型配置审计', group: 'settings' },
  { path: '/settings/tests', icon: '🧪', label: '测试审计', group: 'settings' },
  { path: '/settings/backend', icon: '🖥️', label: '后端服务', group: 'settings' },
  { path: '/about', icon: 'ℹ️', label: '关于', group: 'settings' },
]

const GROUP_META = {
  content: { label: '内容创作', icon: '✏️', defaultOpen: true },
  tools: { label: '常用工具', icon: '🔧', defaultOpen: true },
  pipeline: { label: '管道编排', icon: '🔀', defaultOpen: true },
  settings: { label: '设置', icon: '⚙️', defaultOpen: true },
}

const GROUP_ORDER = ['content', 'tools', 'pipeline', 'settings']

export default function Sidebar({ open, onToggle }) {
  const [expanded, setExpanded] = useState(() =>
    Object.fromEntries(GROUP_ORDER.map(g => [g, GROUP_META[g]?.defaultOpen ?? true]))
  )

  const toggleGroup = (group) => {
    setExpanded(prev => ({ ...prev, [group]: !prev[group] }))
  }

  const itemsByGroup = GROUP_ORDER.map(groupId => ({
    id: groupId,
    meta: GROUP_META[groupId],
    items: navItems.filter(i => i.group === groupId),
  })).filter(g => g.items.length > 0)

  return (
    <aside
      className={`${open ? 'w-64' : 'w-0'} flex flex-col bg-surface border-r border-border shrink-0 transition-all duration-300 overflow-hidden`}
    >
      <div className="p-4 border-b border-border flex justify-between items-center shrink-0">
        <h2 className="text-lg font-semibold text-white">Hou CLI</h2>
        <button
          onClick={onToggle}
          className="p-1 text-white hover:bg-white/10 rounded lg:hidden"
          aria-label="切换侧边栏"
        >
          ☰
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-2 px-2">
          <li>
            <NavLink
              to="/"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-accent/20 text-accent' : 'text-muted hover:bg-white/5 hover:text-fg'
                }`
              }
            >
              <span>🏠</span>
              <span>首页</span>
            </NavLink>
          </li>
          {itemsByGroup.map(({ id, meta, items }) => (
            <li key={id}>
              <button
                onClick={() => toggleGroup(id)}
                className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm text-muted hover:bg-white/5 hover:text-fg transition-colors"
              >
                <span className="flex items-center gap-3">
                  <span>{meta?.icon ?? '•'}</span>
                  <span>{meta?.label ?? id}</span>
                </span>
                <span className={`transition-transform ${expanded[id] ? 'rotate-180' : ''}`}>▼</span>
              </button>
              {expanded[id] && (
                <ul className="mt-1 ml-4 space-y-0.5 border-l border-border pl-2">
                  {items.map(item => (
                    <li key={item.path}>
                      <NavLink
                        to={item.path}
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                            isActive ? 'bg-accent/20 text-accent' : 'text-muted hover:bg-white/5 hover:text-fg'
                          }`
                        }
                      >
                        <span>{item.icon}</span>
                        <span>{item.label}</span>
                      </NavLink>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </nav>

      <div className="p-3 border-t border-border shrink-0">
        <BackendStatus />
      </div>
    </aside>
  )
}
