export default function SettingsGeneral() {
  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">常规设置</h1>
      </header>
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <div className="space-y-6">
          <section>
            <h3 className="text-base font-medium text-white mb-3">界面设置</h3>
            <label className="flex items-center gap-3 text-[#94a3b8]">
              <input type="checkbox" defaultChecked className="rounded" />
              深色模式
            </label>
          </section>
        </div>
      </div>
    </div>
  )
}
