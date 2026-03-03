import { useState, useEffect } from 'react'

const DARK_STORAGE_KEY = 'hou-cli-dark-mode'

function getDarkFromStorage() {
  // 默认浅色；仅当存储为 '1' 时视为深色
  return localStorage.getItem(DARK_STORAGE_KEY) === '1'
}

export default function SettingsGeneral() {
  const [dark, setDark] = useState(() => getDarkFromStorage())

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark')
      localStorage.setItem(DARK_STORAGE_KEY, '1')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem(DARK_STORAGE_KEY, '0')
    }
  }, [dark])

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-fg">常规设置</h1>
      </header>
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <div className="space-y-6">
          <section>
            <h3 className="text-base font-medium text-fg mb-3">界面设置</h3>
            <label className="flex items-center gap-3 text-muted cursor-pointer">
              <input
                type="checkbox"
                checked={dark}
                onChange={(e) => setDark(e.target.checked)}
                className="rounded"
              />
              深色模式
            </label>
          </section>
        </div>
      </div>
    </div>
  )
}
