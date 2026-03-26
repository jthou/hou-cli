/**
 * 视觉模型选择器：先选供应商，再选模型（无「智能选择」）
 * @param {{ value: string, onChange: (v: string) => void, providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>, defaultModel?: string, loading?: boolean, className?: string, compact?: boolean }} props
 */
export default function VisionModelSelector({
  value,
  onChange,
  providers,
  defaultModel = '',
  loading = false,
  className = '',
  compact = false,
}) {
  const selectedProvider = providers.find((p) =>
    p.models?.some((m) => m.value === value)
  )?.id
  const selectedProviderObj = providers.find((p) => p.id === selectedProvider)
  const modelsForProvider = selectedProviderObj?.models ?? []
  const fallback = defaultModel || providers[0]?.models?.[0]?.value || ''
  const isValid = providers.some((p) =>
    p.models?.some((m) => m.value === value)
  )
  const displayValue = isValid ? value : fallback

  const handleProviderChange = (e) => {
    const next = e.target.value
    const p = providers.find((x) => x.id === next)
    if (p?.models?.length) {
      onChange(p.models[0].value)
    }
  }

  const handleModelChange = (e) => {
    onChange(e.target.value)
  }

  const selectClass = compact
    ? 'text-[10px] rounded border border-border bg-white/5 px-1.5 py-0.5 text-fg focus:outline-none focus:ring-1 focus:ring-accent'
    : 'text-xs rounded border border-border bg-white/5 px-2 py-1.5 text-fg focus:outline-none focus:ring-1 focus:ring-accent'

  if (providers.length === 0) {
    return null
  }

  const firstProvider = providers[0]
  const currentModels = selectedProviderObj?.models ?? firstProvider?.models ?? []

  return (
    <div className={`flex items-center ${compact ? 'gap-1' : 'gap-2'} min-w-0 ${className}`}>
      {compact ? (
        <span className="sr-only">视觉模型</span>
      ) : (
        <span className="text-xs text-muted shrink-0">视觉模型</span>
      )}
      <select
        value={selectedProvider || firstProvider?.id}
        onChange={handleProviderChange}
        className={`${selectClass} min-w-0 shrink`}
        disabled={loading}
        aria-label={compact ? '视觉模型平台' : undefined}
      >
        {providers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.label}
          </option>
        ))}
      </select>
      <select
        value={
          currentModels.some((m) => m.value === displayValue)
            ? displayValue
            : currentModels[0]?.value
        }
        onChange={handleModelChange}
        className={`${selectClass} min-w-0 ${compact ? 'max-w-[11rem] sm:max-w-[14rem]' : 'flex-1'}`}
        disabled={loading || currentModels.length === 0}
        aria-label={compact ? '视觉模型名称' : undefined}
      >
        {currentModels.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>
    </div>
  )
}
