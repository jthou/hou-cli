/**
 * 模型选择器：先选供应商，再选模型
 * 当 providers 为空时回退为单下拉（兼容加载中或接口异常）
 * @param {{ value: string, onChange: (v: string) => void, providers: Array<{id: string, label: string, models: Array<{value: string, label: string}>}>, models?: Array<{value: string, label: string}>, loading?: boolean, className?: string }} props
 */
export default function ModelSelector({
  value,
  onChange,
  providers,
  models = [],
  loading = false,
  className = '',
}) {
  const isAuto = value === 'auto'
  const selectedProvider = isAuto
    ? 'auto'
    : providers.find((p) => p.models?.some((m) => m.value === value))?.id ?? 'auto'
  const selectedProviderObj = providers.find((p) => p.id === selectedProvider)
  const modelsForProvider = selectedProviderObj?.models ?? []

  const handleProviderChange = (e) => {
    const next = e.target.value
    if (next === 'auto') {
      onChange('auto')
      return
    }
    const p = providers.find((x) => x.id === next)
    if (p?.models?.length) {
      onChange(p.models[0].value)
    }
  }

  const handleModelChange = (e) => {
    onChange(e.target.value)
  }

  const selectClass =
    'text-xs rounded border border-border bg-white/5 px-2 py-1.5 text-fg focus:outline-none focus:ring-1 focus:ring-accent'

  // 无供应商数据时回退为单下拉
  if (providers.length === 0) {
    const flatModels = models.length > 0 ? models : [{ value: 'auto', label: '智能选择' }]
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <label className="text-xs text-muted shrink-0">模型</label>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={selectClass}
          disabled={loading}
        >
          {flatModels.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <label className="text-xs text-muted shrink-0">模型</label>
      <select
        value={selectedProvider}
        onChange={handleProviderChange}
        className={selectClass}
        disabled={loading}
      >
        <option value="auto">智能选择</option>
        {providers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.label}
          </option>
        ))}
      </select>
      {selectedProvider !== 'auto' && modelsForProvider.length > 0 && (
        <select
          value={value}
          onChange={handleModelChange}
          className={selectClass}
          disabled={loading}
        >
          {modelsForProvider.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      )}
    </div>
  )
}
