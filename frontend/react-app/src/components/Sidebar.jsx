import { NavLink } from 'react-router-dom'
import BackendStatus from './BackendStatus'

// 分组：智能工具、阅读工具、任务工具、文档、协作、设置、开发
// 时间：2026-03-13；理由：任务中心需紧邻首页便于进入；方法：/tasks 单独插在首页下，不从 navItems 渲染。
const navItems = [
  { path: '/general-chat', icon: '💬', label: '通用对话', group: 'smart_tools' },
  { path: '/work-assistant', icon: '🤖', label: '工作助手', group: 'smart_tools' },
  { path: '/code-assistant', icon: '💻', label: '代码助手', group: 'smart_tools' },
  { path: '/article-writing', icon: '✍️', label: '写作助手', group: 'smart_tools' },
  { path: '/ppt-assistant', icon: '📊', label: 'PPT助手', group: 'smart_tools' },
  { path: '/wechat-drafts', icon: '✏️', label: '公众号草稿', group: 'wiki' },
  { path: '/web-reader', icon: '🌐', label: '网页阅读', group: 'read' },
  { path: '/mediawiki-reader', icon: '📖', label: 'Wiki阅读', group: 'read' },
  { path: '/wikipedia-reader', icon: '📚', label: 'Wikipedia', group: 'read' },
  { path: '/weread-reader', icon: '📱', label: '微信读书', group: 'read' },
  { path: '/pdf-reader', icon: '📘', label: 'PDF阅读', group: 'read' },
  // 时间：2026-04-04；理由：热点摘要为聚合阅读素材，与阅读工具同组；方法：group 由 task_tools 改为 read
  { path: '/ai-hot-news', icon: '🔥', label: '今日 AI 热点', group: 'read' },
  { path: '/pipeline', icon: '🔀', label: '管道编排', group: 'task_tools' },
  { path: '/url-to-wiki', icon: '📰', label: '网文抓取', group: 'task_tools' },
  { path: '/web-search', icon: '🔍', label: '网页搜索', group: 'task_tools' },
  { path: '/video-download', icon: '⬇️', label: '视频下载', group: 'task_tools' },
  { path: '/image-generation', icon: '🖼️', label: '图片生成', group: 'task_tools' },
  { path: '/video-extract-audio', icon: '🎧', label: '音频提取', group: 'task_tools' },
  { path: '/speech-to-text', icon: '🎤', label: '字幕提取', group: 'task_tools' },
  { path: '/pdf-to-wiki', icon: '📄', label: 'PDF转Wiki', group: 'task_tools' },
  { path: '/wiki-directory', icon: '📚', label: 'Wiki目录', group: 'docs' },
  { path: '/settings/kanban', icon: '🗂️', label: 'Wiki看板', group: 'wiki' },
  { path: '/weather-query', icon: '🌤️', label: '天气查询', group: 'task_tools' },
  { path: '/disk-scan', icon: '💾', label: '磁盘扫描', group: 'task_tools' },
  { path: '/settings/general', icon: '🎨', label: '常规设置', group: 'settings' },
  { path: '/settings/writing-profile', icon: '✍️', label: '写作画像', group: 'settings' },
  { path: '/settings/work-config', icon: '📋', label: '工作配置', group: 'settings' },
  { path: '/settings/storage', icon: '💾', label: '存储审计', group: 'settings' },
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
  smart_tools: { label: '智能工具', icon: '🤖' },
  read: { label: '阅读工具', icon: '📖' },
  task_tools: { label: '任务工具', icon: '🛠️' },
  docs: { label: '文档', icon: '📄' },
  wiki: { label: '协作', icon: '🗂️' },
  settings: { label: '设置', icon: '⚙️' },
  dev: { label: '开发', icon: '🧪' },
}

const GROUP_ORDER = ['smart_tools', 'read', 'task_tools', 'docs', 'wiki', 'settings', 'dev']

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
            <div className="flex items-center gap-2">
              <span className="text-xl" title="Hou CLI">🖥️</span>
              <h2 className="text-lg font-semibold text-white">Hou CLI</h2>
            </div>
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
          <li>
            <NavLink
              to="/tasks"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-accent/20 text-accent' : 'text-muted hover:bg-white/5 hover:text-fg'
                }`
              }
            >
              <span>📋</span>
              <span>任务中心</span>
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
        <div className="flex flex-col items-center py-4 gap-2">
          <span className="text-lg" title="Hou CLI">🖥️</span>
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
