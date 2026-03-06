import { NavLink } from 'react-router-dom'
import BackendStatus from './BackendStatus'

// 分组：任务、创作、阅读、抓取、媒体、文档、协作、管道、工具、设置、开发
const navItems = [
  { path: '/work-assistant', icon: '🤖', label: '工作助手', group: 'tasks' },
  { path: '/tasks', icon: '📋', label: '任务中心', group: 'tasks' },
  { path: '/wechat-drafts', icon: '✏️', label: '公众号草稿', group: 'create' },
  { path: '/article-writing', icon: '✍️', label: '公众号写作', group: 'create' },
  { path: '/mediawiki-reader', icon: '📖', label: 'Wiki阅读', group: 'read' },
  { path: '/web-reader', icon: '🌐', label: '网页阅读', group: 'read' },
  { path: '/pdf-reader', icon: '📘', label: 'PDF阅读', group: 'read' },
  { path: '/url-to-wiki', icon: '📰', label: '网文抓取', group: 'scrape' },
  { path: '/web-search', icon: '🔍', label: '网页搜索', group: 'scrape' },
  { path: '/video-download', icon: '⬇️', label: '视频下载', group: 'media' },
  { path: '/image-generation', icon: '🖼️', label: '图片生成', group: 'media' },
  { path: '/video-extract-audio', icon: '🎧', label: '音频提取', group: 'media' },
  { path: '/speech-to-text', icon: '🎤', label: '字幕提取', group: 'media' },
  { path: '/pdf-to-wiki', icon: '📄', label: 'PDF转Wiki', group: 'docs' },
  { path: '/wiki-directory', icon: '📚', label: 'Wiki目录', group: 'docs' },
  { path: '/settings/kanban', icon: '🗂️', label: 'Wiki看板', group: 'wiki' },
  { path: '/pipeline', icon: '🔀', label: '管道编排', group: 'pipeline' },
  { path: '/weather-query', icon: '🌤️', label: '天气查询', group: 'tools' },
  { path: '/settings/general', icon: '🎨', label: '常规设置', group: 'settings' },
  { path: '/settings/storage', icon: '💾', label: '存储配置', group: 'settings' },
  { path: '/settings/llm-audit', icon: '📜', label: 'LLM审计', group: 'settings' },
  { path: '/settings/network-audit', icon: '🌐', label: '网络审计', group: 'settings' },
  { path: '/settings/system-prompt-audit', icon: '📋', label: '提示词审计', group: 'settings' },
  { path: '/settings/model-config-audit', icon: '🤖', label: '模型审计', group: 'settings' },
  { path: '/about', icon: 'ℹ️', label: '关于系统', group: 'settings' },
  { path: '/settings/tests', icon: '🧪', label: '测试占位', group: 'dev' },
  { path: '/settings/backend', icon: '🖥️', label: '后端占位', group: 'dev' },
  { path: '/settings/dev-audit', icon: '📊', label: '开发审计', group: 'dev' },
]

const GROUP_META = {
  tasks: { label: '任务', icon: '📋' },
  create: { label: '创作', icon: '✏️' },
  read: { label: '阅读', icon: '📖' },
  scrape: { label: '抓取', icon: '🔍' },
  media: { label: '媒体', icon: '🎬' },
  docs: { label: '文档', icon: '📄' },
  wiki: { label: '协作', icon: '🗂️' },
  pipeline: { label: '管道', icon: '🔀' },
  tools: { label: '工具', icon: '🔧' },
  settings: { label: '设置', icon: '⚙️' },
  dev: { label: '开发', icon: '🧪' },
}

const GROUP_ORDER = ['tasks', 'create', 'read', 'scrape', 'media', 'docs', 'wiki', 'pipeline', 'tools', 'settings', 'dev']

export default function Sidebar({ open, onToggle }) {
  const itemsByGroup = GROUP_ORDER.map(groupId => ({
    id: groupId,
    meta: GROUP_META[groupId],
    items: navItems.filter(i => i.group === groupId),
  })).filter(g => g.items.length > 0)

  return (
    <aside
      className={`${open ? 'w-64' : 'w-10'} flex flex-col bg-surface border-r border-border shrink-0 transition-all duration-300 overflow-hidden`}
    >
      {open ? (
        <>
          <div className="p-4 border-b border-border flex justify-between items-center shrink-0">
            <h2 className="text-lg font-semibold text-white">Hou CLI</h2>
            <button
              onClick={onToggle}
              className="p-1.5 text-muted hover:text-fg hover:bg-white/10 rounded"
              aria-label="收起菜单"
              title="收起菜单"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              </svg>
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
              <div className="flex items-center gap-3 px-3 py-2 text-xs font-medium text-muted/80 uppercase tracking-wider">
                <span>{meta?.icon ?? '•'}</span>
                <span>{meta?.label ?? id}</span>
              </div>
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
            </li>
          ))}
        </ul>
      </nav>

          <div className="p-3 border-t border-border shrink-0">
            <BackendStatus />
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center py-4">
          <button
            onClick={onToggle}
            className="p-2 text-muted hover:text-fg hover:bg-white/10 rounded"
            aria-label="展开菜单"
            title="展开菜单"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}
    </aside>
  )
}
