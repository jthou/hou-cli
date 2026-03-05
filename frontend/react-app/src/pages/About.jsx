import PageHeader from '../components/PageHeader'

export default function About() {
  return (
    <div className="flex flex-col h-full">
      <PageHeader title="关于系统" />
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <p className="text-muted mb-4">Hou CLI 是一个基于 LLM 的智能助手系统。</p>
        <p className="text-sm text-muted">版本: 1.0.0</p>
      </div>
    </div>
  )
}
