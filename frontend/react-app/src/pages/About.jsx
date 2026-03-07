import { useEffect, useState } from 'react'
import PageHeader from '../components/PageHeader'

export default function About() {
  const [version, setVersion] = useState(null)
  const [versionError, setVersionError] = useState(null)

  useEffect(() => {
    fetch('/api/version')
      .then((res) => res.json())
      .then((data) => setVersion(data.version ?? '—'))
      .catch(() => setVersionError(true))
  }, [])

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="关于系统" />
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <p className="text-muted mb-4">Hou CLI 是一个基于 LLM 的智能助手系统。</p>
        <p className="text-sm text-muted">
          版本: {versionError ? '—' : version ?? '加载中...'}
        </p>
      </div>
    </div>
  )
}
