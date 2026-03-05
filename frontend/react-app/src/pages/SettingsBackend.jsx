import PageHeader from '../components/PageHeader'

export default function SettingsBackend() {
  return (
    <div className="flex flex-col h-full">
      <PageHeader title="后端占位" />
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <p className="text-muted">后端配置功能待完善</p>
      </div>
    </div>
  )
}
