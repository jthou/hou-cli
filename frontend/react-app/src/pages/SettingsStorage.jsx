import { useEffect, useState } from 'react'

export default function SettingsStorage() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch('/api/storage/config')
        const json = await res.json()
        if (!json.success) {
          throw new Error(json.error || '获取存储配置失败')
        }
        if (!cancelled) setConfig(json)
      } catch (e) {
        if (!cancelled) setError(e.message || String(e))
      }
      if (!cancelled) setLoading(false)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const paths = config?.paths || {}
  const sqlite = config?.sqlite
  const chroma = config?.chromadb

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">存储配置</h1>
      </header>
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl space-y-6">
        {loading && <p className="text-muted text-sm">加载中…</p>}
        {error && <p className="text-sm text-red-400">获取存储配置失败：{error}</p>}

        {!loading && !error && config && (
          <>
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-white">核心路径（统一定义）</h2>
              <div className="space-y-2 text-xs text-muted">
                <div>
                  <span className="font-medium text-white/80 mr-2">应用数据目录（data_dir）</span>
                  <code className="break-all">{paths.data_dir || config.data_dir}</code>
                </div>
                <div>
                  <span className="font-medium text-white/80 mr-2">默认输出目录（default_output_dir）</span>
                  <code className="break-all">
                    {paths.default_output_dir || '(未定义，后端将回退到 ~/hou-cli/outputs)'}
                  </code>
                </div>
                <div>
                  <span className="font-medium text-white/80 mr-2">临时目录根（temp_root_dir）</span>
                  <code className="break-all">
                    {paths.temp_root_dir || '(未定义，后端将回退到应用数据目录下的 tmp 子目录)'}
                  </code>
                </div>
                <div>
                  <span className="font-medium text-white/80 mr-2">LLM 审计数据库目录</span>
                  <code className="break-all">
                    {config.llm_audit_db_path || '未启用 / 未创建'}
                  </code>
                </div>
              </div>
            </section>

            {sqlite && (
              <section className="space-y-3">
                <h2 className="text-sm font-semibold text-white">SQLite 数据库</h2>
                <div className="space-y-2 text-xs text-muted">
                  <div>
                    <span className="font-medium text-white/80 mr-2">数据库目录</span>
                    <code className="break-all">{sqlite.db_dir}</code>
                  </div>
                  <div>
                    <span className="font-medium text-white/80 mr-2">默认数据库</span>
                    <code className="break-all">{sqlite.default_db_path}</code>
                    <span className="ml-2">
                      ({sqlite.default_db_exists ? '已存在' : '不存在'})，大小 {sqlite.default_db_size_mb} MB
                    </span>
                  </div>
                  {sqlite.databases?.length > 0 && (
                    <div>
                      <div className="font-medium text-white/80 mb-1">数据库文件列表</div>
                      <ul className="space-y-1">
                        {sqlite.databases.map((db) => (
                          <li key={db.path} className="flex flex-col sm:flex-row sm:items-baseline gap-2">
                            <code className="text-xs break-all flex-1">{db.path}</code>
                            <span className="text-xs text-muted shrink-0">
                              {db.size_mb} MB
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            )}

            {chroma && (
              <section className="space-y-3">
                <h2 className="text-sm font-semibold text-white">Chroma 向量库</h2>
                <div className="space-y-2 text-xs text-muted">
                  <div>
                    <span className="font-medium text-white/80 mr-2">数据目录</span>
                    <code className="break-all">{chroma.data_dir}</code>
                  </div>
                  <div>
                    <span className="font-medium text-white/80 mr-2">状态</span>
                    <span className="ml-1">
                      {chroma.exists ? '目录已创建' : '目录不存在（将按需创建）'}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-white/80 mr-2">总大小</span>
                    <span>{chroma.size_mb} MB</span>
                  </div>
                  <div>
                    <span className="font-medium text-white/80 mr-2">集合数量</span>
                    <span>{chroma.collection_count}</span>
                  </div>
                  {chroma.collections?.length > 0 && (
                    <div>
                      <div className="font-medium text-white/80 mb-1">集合列表</div>
                      <ul className="space-y-1">
                        {chroma.collections.map((col) => (
                          <li key={col.name} className="flex flex-col sm:flex-row sm:items-baseline gap-2">
                            <span className="text-xs text-white/90">{col.name}</span>
                            <span className="text-xs text-muted shrink-0">
                              {col.count} 条 / {Object.keys(col.metadata || {}).length} 个元数据字段
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  )
}
