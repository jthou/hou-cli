/**
 * 写作画像设置：用户喜好、表述习惯、范文。
 * 写作助手会根据此配置在生成时遵循并模仿用户风格。
 */
import { useRef, useState } from 'react'
import PageHeader from '../components/PageHeader'
import WritingProfileForm from '../components/WritingProfileForm'

export default function SettingsWritingProfile() {
  const formRef = useRef(null)
  const [saving, setSaving] = useState(false)

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="写作画像"
        subtitle="写作助手会根据你的喜好、表述习惯和范文，在生成文章时尽量贴合你的风格"
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
        <WritingProfileForm
          ref={formRef}
          showSaveButton={false}
          onSavingChange={setSaving}
        />
      </div>
    </div>
  )
}
