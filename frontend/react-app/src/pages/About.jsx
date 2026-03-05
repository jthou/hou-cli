export default function About() {
  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">关于系统</h1>
      </header>
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <p className="text-muted mb-4">Hou CLI 是一个基于 LLM 的智能助手系统。</p>
        <p className="text-sm text-muted">版本: 1.0.0</p>
      </div>
    </div>
  )
}
