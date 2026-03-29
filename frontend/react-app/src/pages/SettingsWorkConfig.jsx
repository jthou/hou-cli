/**
 * 工作配置设置：工作规则、工作上下文、术语表。
 * 工作助手会根据此配置遵循规则、了解工作内容、提示工作建议。
 */
import { useRef, useState } from 'react'
import PageHeader from '../components/PageHeader'
import WorkConfigForm from '../components/WorkConfigForm'

export default function SettingsWorkConfig() {
  const formRef = useRef(null)
  const [saving, setSaving] = useState(false)

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="工作配置"
        actions={
          <button
            type="button"
            onClick={() => formRef.current?.save?.()}
            disabled={saving}
            className="px-4 py-2 rounded bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50"
          >
            {saving ? '保存中…' : '保存'}
          </button>
        }
      />
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
        <WorkConfigForm
          ref={formRef}
          showSaveButton={false}
          onSavingChange={setSaving}
        />
      </div>
    </div>
  )
}
