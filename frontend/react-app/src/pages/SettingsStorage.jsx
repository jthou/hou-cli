import { useEffect, useState, useCallback } from 'react'
import PageHeader from '../components/PageHeader'
import { useToast } from '../components/ToastModal'

function formatMb(sizeBytes) {
  if (sizeBytes == null) return '-'
  return `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`
}

function SizeBadge({ sizeBytes }) {
  return (
    <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 shrink-0 text-right tabular-nums min-w-[6rem] ml-auto">
      {formatMb(sizeBytes)}
    </span>
  )
}

function AuditSection({ audit, onRefresh }) {
  if (!audit) return null
  const { summary, app_data, temp_root, system_temp, outputs, databases, config, chromadb } = audit

  const knownDbs = databases?.known || []
  const tmpDbs = databases?.tmp || []
  const tmpCount = databases?.tmp_count ?? tmpDbs.length

  return (
    <div className="space-y-6">
      {/* 汇总 */}
      <section className="p-4 rounded-lg bg-white/5 border border-border">
        <h2 className="text-sm font-semibold text-fg mb-2">存储汇总</h2>
        <p className="text-2xl font-medium text-cyan-400">{formatMb(summary?.total_bytes) || '0.00 MB'}</p>
        <p className="text-xs text-muted mt-1">应用数据 + 临时 + 输出 + 系统临时目录</p>
      </section>

      {/* 应用数据 */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-fg">应用数据目录</h2>
        <div className="text-xs text-muted space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <code className="break-all text-fg">{app_data?.path}</code>
            <SizeBadge sizeBytes={app_data?.size_bytes} />
          </div>
          {app_data?.subdirs?.length > 0 && (
            <ul className="mt-2 space-y-1 pl-4">
              {app_data.subdirs.map((s) => (
                <li key={s.name} className="flex items-center gap-2">
                  <span className="text-fg">{s.name}</span>
                  <code className="text-[11px] break-all flex-1 text-fg">{s.path}</code>
                  <SizeBadge sizeBytes={s.size_bytes} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* 临时目录 */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-fg">临时文件</h2>
        <div className="text-xs text-muted space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-fg">项目临时根</span>
            <code className="break-all flex-1 text-fg">{temp_root?.path}</code>
            <SizeBadge sizeBytes={temp_root?.size_bytes} />
          </div>
          {system_temp?.items?.length > 0 && (
            <div className="mt-2">
              <span className="text-fg">系统临时（{system_temp.base_path}）</span>
              <ul className="mt-1 space-y-1 pl-4">
                {system_temp.items.map((item) => (
                  <li key={item.name} className="flex items-center gap-2">
                    <span className="text-fg">{item.name}</span>
                    <SizeBadge sizeBytes={item.size_bytes} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      {/* 输出目录 */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-fg">输出文件</h2>
        <div className="text-xs text-muted space-y-1">
          <div className="flex items-center gap-2">
            <code className="break-all flex-1 text-fg">{outputs?.path}</code>
            <SizeBadge sizeBytes={outputs?.size_bytes} />
          </div>
          {outputs?.subdirs?.length > 0 && (
            <ul className="mt-2 space-y-1 pl-4">
              {outputs.subdirs.map((s) => (
                <li key={s.task_type} className="flex items-center gap-2">
                  <span className="text-fg">{s.task_type}</span>
                  <code className="text-[11px] break-all flex-1 text-fg">{s.path}</code>
                  <SizeBadge sizeBytes={s.size_bytes} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* 数据库（分组：已知 + 临时，带清理） */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-fg">数据库</h2>
        <div className="text-xs text-muted">
          <div>目录: <code className="break-all text-fg">{databases?.dir}</code></div>
          <div className="mt-2 space-y-2">
            <div>
              <div className="font-medium text-fg mb-1">已知数据库</div>
              {knownDbs.length > 0 ? (
                <ul className="space-y-1">
                  {knownDbs.map((f) => (
                    <li key={f.path} className="flex items-center gap-2">
                      <span className="text-fg">{f.name}</span>
                      <SizeBadge sizeBytes={f.size_bytes} />
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-fg">无</p>
              )}
            </div>
            <div>
              <div className="font-medium text-fg mb-1 flex items-center gap-2">
                临时数据库（测试残留，可清理）
                {tmpCount > 0 && (
                  <span className="text-amber-400 ml-auto text-right tabular-nums shrink-0">{tmpCount} 个，约 {((databases?.tmp_total_bytes || 0) / (1024 * 1024)).toFixed(2)} MB</span>
                )}
              </div>
              {tmpCount > 0 ? (
                <p className="text-fg">tmp*.db 共 {tmpCount} 个，建议清理以释放空间</p>
              ) : (
                <p className="text-fg">无临时文件</p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 配置 */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-fg">配置数据</h2>
        <div className="text-xs text-muted">
          {config?.files?.length > 0 ? (
            <ul className="space-y-1">
              {config.files.map((f) => (
                <li key={f.path} className="flex items-center gap-2">
                  <span className="text-fg">{f.name}</span>
                  <code className="break-all flex-1 text-fg">{f.path}</code>
                  <SizeBadge sizeBytes={f.size_bytes} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-fg">无配置文件</p>
          )}
        </div>
      </section>

      {/* ChromaDB */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-fg">Chroma 向量库</h2>
        <div className="text-xs text-muted space-y-1">
          <div className="flex items-center gap-2">
            <code className="break-all flex-1 text-fg">{chromadb?.path}</code>
            <SizeBadge sizeBytes={chromadb?.size_bytes} />
          </div>
          {chromadb?.collections?.length > 0 && (
            <ul className="mt-2 space-y-1 pl-4">
              {chromadb.collections.map((c) => (
                <li key={c.name} className="flex items-center gap-2">
                  <span className="text-fg">{c.name}</span>
                  <span className="ml-auto text-muted text-right tabular-nums shrink-0 min-w-[4rem]">{c.count} 条</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}

export default function SettingsStorage() {
  const toast = useToast()
  const [audit, setAudit] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cleaning, setCleaning] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/storage/audit')
      const data = await res.json()
      if (data.success) {
        setAudit(data)
      } else {
        setError(data.error || '获取失败')
      }
    } catch (e) {
      setError(e.message || String(e))
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleCleanupTmpDbs = async () => {
    const tmpCount = audit?.databases?.tmp_count ?? 0
    if (tmpCount === 0) {
      toast.info('暂无临时数据库可清理')
      return
    }
    if (!confirm(`确定清理 ${tmpCount} 个临时数据库（tmp*.db）？此操作不可恢复。`)) return
    setCleaning(true)
    try {
      const res = await fetch('/api/storage/audit/cleanup-tmp-dbs', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        toast.info(`已清理 ${data.deleted_count} 个临时文件，释放 ${data.freed_human || '0 B'}`)
        await load()
      } else {
        toast.error(data.error || '清理失败')
      }
    } catch (e) {
      toast.error(e.message || '清理失败')
    }
    setCleaning(false)
  }

  const tmpCount = audit?.databases?.tmp_count ?? 0

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="存储审计" />
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl">
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg text-sm bg-white/5 text-fg hover:bg-white/10 disabled:opacity-50"
          >
            刷新
          </button>
          {tmpCount > 0 && (
            <button
              type="button"
              onClick={handleCleanupTmpDbs}
              disabled={cleaning}
              className="px-3 py-1.5 rounded-lg text-sm bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 disabled:opacity-50"
            >
              {cleaning ? '清理中…' : `清理临时数据库 (${tmpCount} 个)`}
            </button>
          )}
        </div>

        {loading && <p className="text-fg text-sm">加载中…</p>}
        {error && <p className="text-sm text-red-400">获取失败：{error}</p>}

        {!loading && !error && (
          audit ? <AuditSection audit={audit} onRefresh={load} /> : <p className="text-fg text-sm">暂无审计数据</p>
        )}
      </div>
    </div>
  )
}
