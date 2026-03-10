/**
 * 统一添加参考：将内容加入写作助手、工作助手或通用对话的会话上下文
 * 从 Wiki、网页阅读、字幕、草稿等页面跳转，选择目标会话后添加并跳转
 */
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import SessionSelectSection from '../components/SessionSelectSection'
import { useToast } from '../components/ToastModal'
import { saveReferenceBlocks, loadReferenceBlocks } from '../utils/articleWritingIndexedDB'
import { deriveRefTitle, generateReferenceBlockId } from '../utils/referenceUtils'

const ARTICLE_TYPE = 'article_writing'
const WORK_TYPE = 'work_assistant'
const GENERAL_TYPE = 'general_chat'
const ARTICLE_STORAGE_KEY = 'article_writing_selected_session_id'
const WORK_STORAGE_KEY = 'work_assistant_selected_session'
const GENERAL_STORAGE_KEY = 'general_chat_selected_session'

const TYPE_CONFIG = {
  [ARTICLE_TYPE]: { label: '写作助手', path: '/article-writing', storageKey: ARTICLE_STORAGE_KEY },
  [WORK_TYPE]: { label: '工作助手', path: '/work-assistant', storageKey: WORK_STORAGE_KEY },
  [GENERAL_TYPE]: { label: '通用对话', path: '/general-chat', storageKey: GENERAL_STORAGE_KEY },
}

export default function AddReference() {
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const content = (location.state?.addToReference || '').trim()

  const [articleSessions, setArticleSessions] = useState([])
  const [workSessions, setWorkSessions] = useState([])
  const [generalSessions, setGeneralSessions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!content) {
      navigate('/', { replace: true })
      return
    }
    Promise.all([
      fetch(`/api/sessions/list?type=${ARTICLE_TYPE}&limit=50`).then((r) => r.json()),
      fetch(`/api/sessions/list?type=${WORK_TYPE}&limit=50`).then((r) => r.json()),
      fetch(`/api/sessions/list?type=${GENERAL_TYPE}&limit=50`).then((r) => r.json()),
    ])
      .then(([a, w, g]) => {
        setArticleSessions(a.sessions || [])
        setWorkSessions(w.sessions || [])
        setGeneralSessions(g.sessions || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [content, navigate])

  const handleSelect = async (sessionType, sessionId) => {
    if (!content) return
    const cfg = TYPE_CONFIG[sessionType]
    if (!cfg) return
    const newBlock = {
      id: generateReferenceBlockId(),
      title: deriveRefTitle(content),
      content,
    }
    let targetSessionId = sessionId
    if (!targetSessionId) {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          metadata: { type: sessionType },
        }),
      }).then((r) => r.json())
      if (!res.success || !res.session_id) {
        toast?.error?.(res.error || '创建会话失败')
        return
      }
      targetSessionId = res.session_id
      await saveReferenceBlocks(targetSessionId, [newBlock], sessionType)
    } else {
      const existing = await loadReferenceBlocks(targetSessionId, sessionType)
      await saveReferenceBlocks(targetSessionId, [...existing, newBlock], sessionType)
    }
    if (!targetSessionId) return
    try {
      sessionStorage.setItem(cfg.storageKey, targetSessionId)
    } catch (_) {}
    toast?.info?.(`已添加到${cfg.label}会话`)
    navigate(-1)
  }

  const handleNewAndAdd = async (sessionType) => {
    if (!content) return
    const cfg = TYPE_CONFIG[sessionType]
    if (!cfg) return
    const newBlock = {
      id: generateReferenceBlockId(),
      title: deriveRefTitle(content),
      content,
    }
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata: { type: sessionType } }),
    }).then((r) => r.json())
    if (!res.success || !res.session_id) {
      toast?.error?.(res.error || '创建会话失败')
      return
    }
    await saveReferenceBlocks(res.session_id, [newBlock], sessionType)
    try {
      sessionStorage.setItem(cfg.storageKey, res.session_id)
    } catch (_) {}
    toast?.info?.(`已创建${cfg.label}会话并添加`)
    navigate(-1)
  }

  if (!content) return null

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="添加到参考" subtitle="选择目标会话，将内容加入写作助手、工作助手或通用对话的参考上下文" />
      <div className="flex-1 overflow-y-auto p-6">
        <p className="text-sm text-muted mb-4 line-clamp-2 max-w-4xl">
          {content.slice(0, 120)}
          {content.length > 120 ? '…' : ''}
        </p>
        {loading ? (
          <p className="text-muted text-sm">加载会话列表…</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl">
            <SessionSelectSection
              title="写作助手"
              typeBadge="写作助手"
              sessions={articleSessions}
              onSelect={(id) => handleSelect(ARTICLE_TYPE, id)}
              onNewAndAdd={() => handleNewAndAdd(ARTICLE_TYPE)}
              emptyMessage="暂无写作助手会话"
            />
            <SessionSelectSection
              title="工作助手"
              typeBadge="工作助手"
              sessions={workSessions}
              onSelect={(id) => handleSelect(WORK_TYPE, id)}
              onNewAndAdd={() => handleNewAndAdd(WORK_TYPE)}
              emptyMessage="暂无工作助手会话"
            />
            <SessionSelectSection
              title="通用对话"
              typeBadge="通用对话"
              sessions={generalSessions}
              onSelect={(id) => handleSelect(GENERAL_TYPE, id)}
              onNewAndAdd={() => handleNewAndAdd(GENERAL_TYPE)}
              emptyMessage="暂无通用对话会话"
            />
          </div>
        )}
      </div>
    </div>
  )
}
