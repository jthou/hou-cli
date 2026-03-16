/**
 * 写作反馈：从接受的修改中抽样章节，请用户打分，据此改进写作画像
 * 时间：2025-03-15；理由：持续改进写作；方法：抽样→打分→学习
 */
import { useState, useEffect, useCallback } from 'react'
import MarkdownPreview from './MarkdownPreview'
import { useToast } from './ToastModal'

const SCORE_LABELS = { 1: '很差', 2: '较差', 3: '一般', 4: '较好', 5: '很好' }

export default function WritingRatingSection({ onLearnComplete }) {
  const toast = useToast()
  const [records, setRecords] = useState([])
  const [selectedRecordId, setSelectedRecordId] = useState(null)
  const [sections, setSections] = useState([])
  const [loading, setLoading] = useState(false)
  const [sectionsLoading, setSectionsLoading] = useState(false)
  const [ratings, setRatings] = useState({}) // section_index -> score
  const [submitting, setSubmitting] = useState(false)
  const [learnLoading, setLearnLoading] = useState(false)
  const [expandRating, setExpandRating] = useState(false)

  const loadRecords = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch('/api/settings/writing-profile/acceptance-records?limit=20')
      const d = await r.json()
      if (d.success && Array.isArray(d.records)) {
        setRecords(d.records)
        setSelectedRecordId((prev) => (prev == null && d.records.length > 0 ? d.records[0].id : prev))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  useEffect(() => {
    if (!selectedRecordId) {
      setSections([])
      return
    }
    setSectionsLoading(true)
    fetch(`/api/settings/writing-profile/acceptance-records/${selectedRecordId}/sections?max_sections=5`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.sections)) {
          setSections(d.sections)
          setRatings({})
        }
      })
      .catch(console.error)
      .finally(() => setSectionsLoading(false))
  }, [selectedRecordId])

  const handleRate = async (sectionIndex, score) => {
    setRatings((prev) => ({ ...prev, [sectionIndex]: score }))
    setSubmitting(true)
    try {
      const section = sections.find((s) => s.section_index === sectionIndex)
      await fetch('/api/settings/writing-profile/rate-section', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          record_id: selectedRecordId,
          section_index: sectionIndex,
          score,
          section_text: section?.section_text,
        }),
      })
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  const handleLearn = async () => {
    setLearnLoading(true)
    try {
      const r = await fetch('/api/settings/writing-profile/learn-from-ratings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_score: 4, limit: 10 }),
      })
      const d = await r.json()
      if (d.success) {
        if (d.updated) {
          toast?.success?.('写作画像已根据高分章节更新')
          onLearnComplete?.()
        } else {
          toast?.info?.(d.message || '暂无高分章节可学习')
        }
      } else {
        toast?.error?.(d.error || '学习失败')
      }
    } catch (e) {
      console.error(e)
      toast?.error?.(e?.message || '学习失败')
    } finally {
      setLearnLoading(false)
    }
  }

  const hasHighScores = Object.values(ratings).some((s) => s >= 4)

  if (records.length === 0 && !loading) {
    return null
  }

  return (
    <div className="mt-8 pt-6 border-t border-border">
      <button
        type="button"
        onClick={() => setExpandRating(!expandRating)}
        className="flex items-center gap-2 text-sm font-medium text-muted hover:text-fg"
      >
        {expandRating ? '▼' : '▶'} 参与改进：为已接受的章节打分
      </button>
      {expandRating && (
        <div className="mt-4 space-y-4">
          <p className="text-xs text-muted">
            你点击「接受修改」的内容会被记录。在此为部分章节打分（1–5），系统会根据高分内容持续改进写作画像。
          </p>
          {loading ? (
            <p className="text-xs text-muted">加载中…</p>
          ) : (
            <>
              <div>
                <label className="block text-xs text-muted mb-1">选择一条接受记录</label>
                <select
                  value={selectedRecordId ?? ''}
                  onChange={(e) => setSelectedRecordId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full max-w-md rounded border border-border bg-black/20 px-3 py-2 text-sm text-fg"
                >
                  {records.map((rec) => (
                    <option key={rec.id} value={rec.id}>
                      {rec.created_at?.slice(0, 19).replace('T', ' ')} · 已打分 {rec.rated_count ?? 0} 节
                    </option>
                  ))}
                </select>
              </div>
              {sectionsLoading ? (
                <p className="text-xs text-muted">加载章节中…</p>
              ) : sections.length === 0 ? (
                <p className="text-xs text-muted">该记录无可用章节或内容过短。</p>
              ) : (
                <div className="space-y-4">
                  {sections.map((sec) => (
                    <div
                      key={sec.section_index}
                      className="rounded-lg border border-border bg-white/5 p-4 space-y-3"
                    >
                      <div className="text-xs text-muted">
                        章节 {sec.section_index + 1}
                        {sec.rated && ' · 已打分'}
                      </div>
                      <div className="text-sm max-h-48 overflow-y-auto prose prose-invert prose-sm max-w-none">
                        <MarkdownPreview markdown={sec.section_text || ''} theme="dark" className="text-sm" />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted">打分：</span>
                        {[1, 2, 3, 4, 5].map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => handleRate(sec.section_index, s)}
                            disabled={submitting}
                            className={`px-2 py-1 text-xs rounded border ${
                              ratings[sec.section_index] === s
                                ? 'border-accent bg-accent/20 text-accent'
                                : 'border-border text-muted hover:bg-white/5'
                            }`}
                            title={SCORE_LABELS[s]}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {hasHighScores && (
                    <button
                      type="button"
                      onClick={handleLearn}
                      disabled={learnLoading}
                      className="px-4 py-2 rounded bg-accent text-white text-sm hover:bg-accent/90 disabled:opacity-50"
                    >
                      {learnLoading ? '学习中…' : '根据高分章节更新写作画像'}
                    </button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
