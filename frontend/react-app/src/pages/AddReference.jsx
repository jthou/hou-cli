/**
 * 统一添加参考：将内容加入写作助手、工作助手或通用对话的会话上下文
 * 从 Wiki、网页阅读、字幕、草稿等页面跳转，选择目标会话后添加并跳转
 *
 * 时间：2026-04-11；理由：今日 AI 热点摘要→公众号写作需摘要进「参考」而非右侧成稿；方法：state.autoCreateArticleWriting 时自动新建 article_writing 会话并跳转写作页
 */
import { useEffect, useState, useRef } from 'react'
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

const HOT_NEWS_DIGEST_REF_TITLE = '【参考·今日 AI 热点深度摘要】'

export default function AddReference() {
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const content = (location.state?.addToReference || '').trim()
  const autoArticleWriting = Boolean(location.state?.autoCreateArticleWriting)

  const [articleSessions, setArticleSessions] = useState([])
  const [workSessions, setWorkSessions] = useState([])
  const [generalSessions, setGeneralSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [autoSeeding, setAutoSeeding] = useState(autoArticleWriting && Boolean(content.trim()))
  const autoArticleStartedRef = useRef(false)

  /** 今日 AI 热点等：一键新建写作会话，摘要写入参考块，跳转写作助手（对齐 MCP hot_news_digest → 参考 + 公众号约束由用户提问补充） */
  useEffect(() => {
    if (!content || !autoArticleWriting || autoArticleStartedRef.current) return
    autoArticleStartedRef.current = true
    let cancelled = false
    ;(async () => {
      setAutoSeeding(true)
      try {
        const newBlock = {
          id: generateReferenceBlockId(),
          title: HOT_NEWS_DIGEST_REF_TITLE,
          content,
        }
        const res = await fetch('/api/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ metadata: { type: ARTICLE_TYPE } }),
        }).then((r) => r.json())
        if (cancelled) return
        if (!res.success || !res.session_id) {
          toast?.error?.(res.error || '创建写作会话失败')
          setAutoSeeding(false)
          autoArticleStartedRef.current = false
          return
        }
        const sessionId = res.session_id
        await saveReferenceBlocks(sessionId, [newBlock], ARTICLE_TYPE)
        try {
          sessionStorage.setItem(ARTICLE_STORAGE_KEY, sessionId)
        } catch (_) {}
        toast?.info?.(
          '已创建写作会话并将热点摘要写入「参考」。请在写作页选择 Qwen3 Max，输入篇幅与角度；泛指请用「智能体」。'
        )
        navigate('/article-writing', {
          replace: true,
          state: { focusSessionId: sessionId },
        })
      } catch (e) {
        if (!cancelled) {
          toast?.error?.(e?.message || '创建失败')
          setAutoSeeding(false)
          autoArticleStartedRef.current = false
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [content, autoArticleWriting, navigate, toast])

  useEffect(() => {
    if (!content) {
      navigate('/', { replace: true })
      return
    }
    if (autoArticleWriting) {
      setLoading(false)
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
  }, [content, navigate, autoArticleWriting])

  if (autoSeeding) {
    return (
      <div className="flex flex-col h-full items-center justify-center p-8 text-muted text-sm">
        正在创建写作会话并写入热点参考…
      </div>
    )
  }

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
      <PageHeader title="添加到参考" />
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
