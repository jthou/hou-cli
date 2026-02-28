import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import BackendStatus from './BackendStatus'

const navItems = [
  { path: '/', icon: '📦', label: '任务管理' },
  { path: '/pipeline', icon: '🔀', label: '管道编排' },
  { path: '/video-download', icon: '🎬', label: '视频下载' },
  { path: '/video-extract-audio', icon: '🎵', label: '视频提取音频' },
  { path: '/speech-to-text', icon: '🎤', label: '语音转文字' },
  { path: '/weather-query', icon: '🌤️', label: '天气查询' },
  { path: '/wechat-drafts', icon: '📝', label: '公众号草稿' },
  { path: '/settings/general', icon: '🎨', label: '常规设置', group: 'settings' },
  { path: '/settings/storage', icon: '💾', label: '存储配置', group: 'settings' },
  { path: '/settings/tests', icon: '🧪', label: '测试审计', group: 'settings' },
  { path: '/settings/backend', icon: '🔧', label: '后端服务', group: 'settings' },
  { path: '/about', icon: 'ℹ️', label: '关于', group: 'settings' },
]

export default function Sidebar({ open, onToggle }) {
  const [settingsExpanded, setSettingsExpanded] = useState(true)

  const settingsItems = navItems.filter(i => i.group === 'settings')
  const otherItems = navItems.filter(i => !i.group)

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
        <ul className="space-y-1 px-2">
          {otherItems.map(item => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive ? 'bg-accent/20 text-accent' : 'text-[#94a3b8] hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
          <li>
            <button
              onClick={() => setSettingsExpanded(!settingsExpanded)}
              className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm text-[#94a3b8] hover:bg-white/5 hover:text-white transition-colors"
            >
              <span className="flex items-center gap-3">
                <span>⚙️</span>
                <span>设置</span>
              </span>
              <span className={`transition-transform ${settingsExpanded ? 'rotate-180' : ''}`}>▼</span>
            </button>
            {settingsExpanded && (
              <ul className="mt-1 ml-4 space-y-1 border-l border-border pl-2">
                {settingsItems.map(item => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                          isActive ? 'bg-accent/20 text-accent' : 'text-[#94a3b8] hover:bg-white/5 hover:text-white'
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
        </ul>
      </nav>

      <div className="p-3 border-t border-border shrink-0">
        <BackendStatus />
      </div>
    </aside>
  )
}
