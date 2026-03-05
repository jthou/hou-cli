import PageHeader from '../components/PageHeader'

export default function SettingsTests() {
  return (
    <div className="flex flex-col h-full">
      <PageHeader title="测试占位" />
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <p className="text-muted">测试审计功能待实现</p>
      </div>
    </div>
  )
}
