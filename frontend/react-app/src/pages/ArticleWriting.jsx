/**
 * 写文章 - 与公众号草稿一致：左侧会话列表，中间对话，右侧文章预览（Markdown 预览与微信草稿一致）。
 */
import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useToast } from '../components/ToastModal'
import MarkdownPreview from '../components/MarkdownPreview'
import MarkdownActionButtons from '../components/MarkdownActionButtons'
import ChatInput from '../components/ChatInput'
import ArticleDiffView from '../components/ArticleDiffView'
import { prepareMetadataForSubmitAsync, WECHAT_MP_DRAFT_TASK_TYPE } from '../utils/mdToHtml'
import { formatWechatMpError } from '../utils/wechatMpError'
import TaskParamsForm from '../components/task/TaskParamsForm'
import { getDefaultMetadata } from '../components/task/taskFormUtils'

const WECHAT_MP_API = {
  uploadCover: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch('/api/wechat-mp/upload-cover', { method: 'POST', body: form }).then((r) => r.json())
  },
}

const ARTICLE_SESSION_TYPE = 'article_writing'
const STORAGE_KEY_SELECTED_SESSION = 'article_writing_selected_session_id'
const STORAGE_KEY_REFERENCE_BLOCKS = 'article_writing_reference_blocks'

/** 从内容推导参考块标题：取首行或前 80 字，截断至 50 字 */
function deriveRefTitle(content) {
  const trimmed = (content || '').trim()
  if (!trimmed) return ''
  const firstLine = trimmed.split('\n')[0].trim()
  const candidate = firstLine || trimmed.slice(0, 80)
  return candidate.slice(0, 50)
}

export default function ArticleWriting() {
  const toast = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const [sessions, setSessions] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [selectedSessionId, setSelectedSessionId] = useState(() => {
    try {
      return sessionStorage.getItem(STORAGE_KEY_SELECTED_SESSION) || null
    } catch {
      return null
    }
  })
  const [messages, setMessages] = useState([])
  const [article, setArticle] = useState('')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [editDialog, setEditDialog] = useState(null) // { sessionId, title, mwTitles } 或 null
  const [editDialogMwInput, setEditDialogMwInput] = useState('')
  const [editDialogSearchQuery, setEditDialogSearchQuery] = useState('')
  const [editDialogSearchResults, setEditDialogSearchResults] = useState([])
  const [editDialogSaving, setEditDialogSaving] = useState(false)
  const [listSort, setListSort] = useState('updated_at') // 'updated_at' | 'created_at'
  const [revisions, setRevisions] = useState([])
  const [showRevisions, setShowRevisions] = useState(false)
  const [revisionsLoading, setRevisionsLoading] = useState(false)
  /** 当前在预览的历史版本 id，null 表示预览当前文章 */
  const [previewRevisionId, setPreviewRevisionId] = useState(null)
  /** 查看历史版本时是否显示与当前的差异对比 */
  const [showDiffView, setShowDiffView] = useState(false)
  /** 预览区是否为编辑模式；编辑时的草稿内容 */
  const [editMode, setEditMode] = useState(false)
  const [editDraft, setEditDraft] = useState('')
  /** 流式输出时当前已接收的助手回复内容（未结束时累积显示） */
  const [streamingContent, setStreamingContent] = useState('')
  /** 局部插入弹窗 */
  const [patchDialogOpen, setPatchDialogOpen] = useState(false)
  const [patchAnchor, setPatchAnchor] = useState('')
  const [patchContent, setPatchContent] = useState('')
  const [patchSubmitting, setPatchSubmitting] = useState(false)
  /** 输出弹窗：'mediawiki' | 'wechat' | null */
  const [outputDialog, setOutputDialog] = useState(null)
  /** 同步到公众号草稿：复用 TaskParamsForm，schema 来自 task-types，metadata 含 content（当前文章 Markdown，提交时转公众号 HTML） */
  const [wechatOutputSchema, setWechatOutputSchema] = useState({})
  const [wechatOutputMetadata, setWechatOutputMetadata] = useState({})
  const [wechatOutputSubmitting, setWechatOutputSubmitting] = useState(false)
  const [referenceBlocks, setReferenceBlocks] = useState(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY_REFERENCE_BLOCKS)
      const parsed = raw ? JSON.parse(raw) : []
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  })
  const [referencePanelOpen, setReferencePanelOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)
  const streamingContentRef = useRef('')

  const handleAddReferenceBlock = () => {
    setReferencePanelOpen(true)
    setReferenceBlocks((prev) => [
      ...prev,
      { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, title: '', content: '' },
    ])
  }

  const handleUpdateReferenceBlock = (id, field, value) => {
    setReferenceBlocks((prev) =>
      prev.map((b) => (b.id === id ? { ...b, [field]: value } : b))
    )
  }

  const handleRemoveReferenceBlock = (id) => {
    setReferenceBlocks((prev) => prev.filter((b) => b.id !== id))
  }

  const handleAddToReference = (content) => {
    if (!content || typeof content !== 'string' || !content.trim()) return
    const trimmed = content.trim()
    setReferencePanelOpen(true)
    setReferenceBlocks((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        title: deriveRefTitle(trimmed),
        content: trimmed,
      },
    ])
  }

  const loadRevisions = useCallback(() => {
    if (!selectedSessionId) {
      setRevisions([])
      return
    }
    setRevisionsLoading(true)
    fetch(`/api/chat/article/revisions?session_id=${encodeURIComponent(selectedSessionId)}&limit=30`)
      .then((r) => r.json())
      .then((d) => {
        setRevisions(Array.isArray(d.revisions) ? d.revisions : [])
      })
      .catch(() => setRevisions([]))
      .finally(() => setRevisionsLoading(false))
  }, [selectedSessionId])

  const loadSessions = useCallback(() => {
    setSessionsLoading(true)
    const sort = listSort === 'created_at' ? 'created_at' : 'updated_at'
    const order = 'desc'
    fetch(`/api/sessions/list?limit=50&type=${encodeURIComponent(ARTICLE_SESSION_TYPE)}&sort=${sort}&order=${order}`)
      .then((r) => r.json())
      .then((d) => {
        const list = Array.isArray(d.sessions) ? d.sessions : []
        setSessions(list)
      })
      .catch(() => setSessions([]))
      .finally(() => setSessionsLoading(false))
  }, [listSort])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  /** 参考信息持久化到 sessionStorage，实现跨页面、跨 session 共享与累积 */
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY_REFERENCE_BLOCKS, JSON.stringify(referenceBlocks))
    } catch (_) {}
  }, [referenceBlocks])

  /** 接收来自 url_to_wiki 等「发送到写文章」的 initialMarkdown，创建新会话并填入 */
  useEffect(() => {
    const state = location.state
    const initialMarkdown = state?.initialMarkdown
    if (!initialMarkdown || typeof initialMarkdown !== 'string' || !initialMarkdown.trim()) return
    navigate(location.pathname + location.search, { replace: true, state: {} })
    fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata: { type: ARTICLE_SESSION_TYPE } }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (!d.success || !d.session_id) {
          toast?.error?.(d.error || '创建会话失败')
          return
        }
        const sessionId = d.session_id
        const suggestTitle = (location.search && new URLSearchParams(location.search).get('suggest_title')) || state?.suggestTitle
        const title = (suggestTitle || '').trim().slice(0, 50) || '来自网文抓取的草稿'
        return fetch('/api/chat/article', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, content: initialMarkdown.trim() }),
        })
          .then((r) => r.json())
          .then(() => {
            loadSessions()
            setSelectedSessionId(sessionId)
            if (title && title !== '来自网文抓取的草稿') {
              fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title }),
              }).then((r) => r.json()).then((res) => { if (res.success) loadSessions() })
            }
          })
      })
      .catch((e) => toast?.error?.(e?.message || '创建会话失败'))
  // eslint-disable-next-line react-hooks/exhaustive-deps -- 仅在有 initialMarkdown 时执行一次
  }, [])

  /** 接收来自 Markdown/MediaWiki 预览等「添加到参考信息」的导航，将内容追加到参考块末尾 */
  useEffect(() => {
    const addToRef = location.state?.addToReference
    if (!addToRef || typeof addToRef !== 'string' || !addToRef.trim()) return
    navigate(location.pathname + location.search, { replace: true, state: {} })
    const trimmed = addToRef.trim()
    setReferencePanelOpen(true)
    setReferenceBlocks((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        title: deriveRefTitle(trimmed),
        content: trimmed,
      },
    ])
  }, [location.state?.addToReference])

  useEffect(() => {
    if (sessions.length === 0) return
    const ids = new Set(sessions.map((s) => s.session_id))
    if (!selectedSessionId || !ids.has(selectedSessionId)) {
      const first = sessions[0].session_id
      setSelectedSessionId(first)
      try {
        sessionStorage.setItem(STORAGE_KEY_SELECTED_SESSION, first)
      } catch (_) {}
    }
  }, [sessions, selectedSessionId])

  useEffect(() => {
    try {
      if (selectedSessionId) {
        sessionStorage.setItem(STORAGE_KEY_SELECTED_SESSION, selectedSessionId)
      } else {
        sessionStorage.removeItem(STORAGE_KEY_SELECTED_SESSION)
      }
    } catch (_) {}
  }, [selectedSessionId])

  useEffect(() => {
    if (!selectedSessionId) {
      setMessages([])
      setArticle('')
      setPreviewRevisionId(null)
      setDetailLoading(false)
      return
    }
    setDetailLoading(true)
    setMessages([])
    setArticle('')
    setPreviewRevisionId(null)
    Promise.all([
      fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`).then((r) => r.json()),
      fetch(`/api/chat/article?session_id=${encodeURIComponent(selectedSessionId)}`).then((r) => r.json()),
    ])
      .then(([sessionRes, articleRes]) => {
        if (sessionRes.success && Array.isArray(sessionRes.messages)) {
          setMessages(
            sessionRes.messages.map((m) => ({ role: m.role, content: m.content }))
          )
        }
        if (articleRes.status === 'success' && articleRes.article != null) {
          setArticle(articleRes.article)
        }
      })
      .catch(() => {})
      .finally(() => setDetailLoading(false))
    loadRevisions()
  }, [selectedSessionId, loadRevisions])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent])

  const handleNewSession = () => {
    fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata: { type: ARTICLE_SESSION_TYPE } }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.session_id) {
          loadSessions()
          setSelectedSessionId(d.session_id)
        } else {
          toast?.error?.(d.error || '创建会话失败')
        }
      })
      .catch((e) => toast?.error?.(e?.message || '创建会话失败'))
  }

  const handleStop = () => {
    abortControllerRef.current?.abort()
  }

  const handleSubmit = async (e) => {
    e?.preventDefault?.()
    if (!selectedSessionId) return
    const text = (input || '').trim()
    if (!text) return

    const trimmedBlocks = referenceBlocks
      .map((b) => ({ ...b, content: (b.content || '').trim() }))
      .filter((b) => b.content)

    const referenceContext =
      trimmedBlocks.length === 0
        ? ''
        : `以下是用户提供的参考资料，请在回答时充分利用，并根据用户的最新指令进行综合判断：\n\n${trimmedBlocks
            .map((b, idx) => {
              const title = (b.title || '').trim()
              const header = title ? `【参考${idx + 1}：${title}】` : `【参考${idx + 1}】`
              return `${header}\n${b.content}`
            })
            .join('\n\n')}\n\n---\n\n`

    const messageForModel = referenceContext ? `${referenceContext}【用户本次提问】\n${text}` : text

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setStreamingContent('')
    setLoading(true)
    const ac = new AbortController()
    abortControllerRef.current = ac
    const isFirstMessage = messages.length === 0
    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageForModel,
          session_id: selectedSessionId,
          current_article: article || undefined,
          context_type: 'article_writing',
        }),
        signal: ac.signal,
      })
      if (!res.ok) {
        const err = res.statusText || `服务器返回 ${res.status}`
        setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${err}` }])
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''
        for (const block of parts) {
          const dataLines = block.split('\n').filter((l) => l.startsWith('data: '))
          for (const dataLine of dataLines) {
            try {
              const obj = JSON.parse(dataLine.slice(6))
              if (obj.status === 'streaming' && obj.content != null) {
                const raw = String(obj.content)
                if (raw.startsWith('__DEBUG__:') || raw.startsWith('__TOOL__:') || raw.startsWith('__STATUS__:')) continue
                fullContent += raw
                streamingContentRef.current = fullContent
                setStreamingContent(fullContent)
              } else if (obj.status === 'done') {
                const finalContent = fullContent.trim() || '（助手未返回内容，可能仍在处理或匹配技能，请稍后重试或换一种说法。）'
                setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
                setStreamingContent('')
                streamingContentRef.current = ''
                if (isFirstMessage && text) {
                  fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: text.slice(0, 30).trim() || text.slice(0, 30) }),
                  })
                    .then((r) => r.json())
                    .then((d) => { if (d.success) loadSessions() })
                    .catch(() => {})
                }
                fullContent = ''
              } else if (obj.status === 'error') {
                const err = obj.error || '请求失败'
                toast?.error?.(err)
                setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${err}` }])
                setStreamingContent('')
                streamingContentRef.current = ''
                fullContent = ''
              }
            } catch (_) {}
          }
        }
      }
      if (buffer.trim()) {
        try {
          const dataLines = buffer.split('\n').filter((l) => l.startsWith('data: '))
          for (const dataLine of dataLines) {
            const obj = JSON.parse(dataLine.slice(6))
            if (obj.status === 'streaming' && obj.content != null) {
              const raw = String(obj.content)
              if (!raw.startsWith('__DEBUG__:') && !raw.startsWith('__TOOL__:') && !raw.startsWith('__STATUS__:')) {
                fullContent += raw
                streamingContentRef.current = fullContent
                setStreamingContent(fullContent)
              }
            }
          }
          if (dataLines.length > 0) {
            const lastObj = (() => { try { return JSON.parse(dataLines[dataLines.length - 1].slice(6)) } catch { return null } })()
            if (lastObj?.status === 'done') {
              const finalContent = fullContent.trim() || '（助手未返回内容，可能仍在处理或匹配技能，请稍后重试或换一种说法。）'
              setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
              setStreamingContent('')
              streamingContentRef.current = ''
              fullContent = ''
              if (isFirstMessage && text) {
                fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`, {
                  method: 'PATCH',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ title: text.slice(0, 30).trim() || text.slice(0, 30) }),
                })
                  .then((r) => r.json())
                  .then((d) => { if (d.success) loadSessions() })
                  .catch(() => {})
              }
            } else if (lastObj?.status === 'error') {
              const err = lastObj.error || '请求失败'
              toast?.error?.(err)
              setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${err}` }])
              setStreamingContent('')
              streamingContentRef.current = ''
            }
          }
        } catch (_) {}
        setStreamingContent('')
      }
      if (fullContent.trim()) {
        const finalContent = fullContent.trim()
        setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
      }
      abortControllerRef.current = null
    } catch (err) {
      abortControllerRef.current = null
      if (err.name === 'AbortError') {
        const stoppedContent = streamingContentRef.current
        setMessages((prev) => [...prev, { role: 'assistant', content: stoppedContent ? `[已停止]\n\n${stoppedContent}` : '[已停止]' }])
        setStreamingContent('')
        streamingContentRef.current = ''
        return
      }
      const isNetworkError = err?.message === 'Failed to fetch' || err?.name === 'TypeError'
      const msg = isNetworkError
        ? '无法连接后端。请确认后端已启动（默认端口 8081）。'
        : (err?.message || '网络错误')
      toast?.error?.(msg) || console.error(err)
      setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${msg}` }])
      setStreamingContent('')
    } finally {
      setLoading(false)
    }
  }

  const displayLabel = (s) => {
    const t = (s?.title || s?.metadata?.title || '').trim()
    if (t) return t.length > 28 ? t.slice(0, 28) + '…' : t
    const p = (s?.preview || '').trim()
    return p ? (p.length > 28 ? p.slice(0, 28) + '…' : p) : '新会话'
  }

  const handleDeleteSession = async (sessionId, e) => {
    e?.stopPropagation?.()
    if (!sessionId) return
    const ok = await toast?.confirm?.('确定删除该会话？删除后不可恢复。')
    if (!ok) return
    try {
      const r = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
      const d = await r.json()
      if (d.success) {
        loadSessions()
        if (selectedSessionId === sessionId) {
          setSelectedSessionId(null)
          setMessages([])
          setArticle('')
        }
      } else {
        toast?.error?.(d.error || '删除失败')
      }
    } catch (err) {
      toast?.error?.(err?.message || '删除失败')
    }
  }

  const handleClearSession = async (sessionId, e) => {
    e?.stopPropagation?.()
    if (!sessionId) return
    const ok = await toast?.confirm?.('确定清空该会话的消息与文章草稿？')
    if (!ok) return
    try {
      const r = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/clear`, { method: 'POST' })
      const d = await r.json()
      if (d.success) {
        if (selectedSessionId === sessionId) {
          setMessages([])
          setArticle('')
          setDetailLoading(true)
          try {
            const [sessionRes, articleRes] = await Promise.all([
              fetch(`/api/sessions/${encodeURIComponent(sessionId)}`).then((res) => res.json()),
              fetch(`/api/chat/article?session_id=${encodeURIComponent(sessionId)}`).then((res) => res.json()),
            ])
            if (sessionRes.success && Array.isArray(sessionRes.messages)) {
              setMessages(sessionRes.messages.map((m) => ({ role: m.role, content: m.content })))
            }
            if (articleRes.status === 'success' && articleRes.article != null) {
              setArticle(articleRes.article)
            }
          } finally {
            setDetailLoading(false)
          }
        }
        loadSessions()
      } else {
        toast?.error?.(d.error || '清空失败')
      }
    } catch (err) {
      toast?.error?.(err?.message || '清空失败')
    }
  }

  const openEditDialog = (sessionId, currentTitle, e) => {
    e?.stopPropagation?.()
    if (!sessionId) return
    setEditDialogSearchResults([])
    setEditDialogSearchQuery('')
    setEditDialogMwInput('')
    // 从服务端拉取最新会话标题与参考页，避免刷新后或列表未刷新时显示陈旧数据
    Promise.all([
      fetch(`/api/sessions/${encodeURIComponent(sessionId)}`).then((r) => r.json()),
      fetch(`/api/chat/mw-sources?session_id=${encodeURIComponent(sessionId)}`).then((r) => r.json()),
    ])
      .then(([sessionRes, mwRes]) => {
        const titleFromServer = sessionRes?.session?.metadata?.title
        const title = (titleFromServer ?? currentTitle ?? '').toString().trim() || '新会话'
        const titles = Array.isArray(mwRes?.titles) ? mwRes.titles : []
        setEditDialog({ sessionId, title, mwTitles: titles })
      })
      .catch(() => {
        setEditDialog({
          sessionId,
          title: (currentTitle || '').trim() || '新会话',
          mwTitles: [],
        })
      })
  }

  const closeEditDialog = () => {
    setEditDialog(null)
    setEditDialogSearchResults([])
    setEditDialogSearchQuery('')
    setEditDialogMwInput('')
  }

  const addMwTitle = (title) => {
    const t = (title || '').trim()
    if (!t || !editDialog) return
    if (editDialog.mwTitles.includes(t)) return
    setEditDialog((prev) => ({ ...prev, mwTitles: [...prev.mwTitles, t] }))
    setEditDialogMwInput('')
  }

  const removeMwTitle = (index) => {
    if (!editDialog) return
    setEditDialog((prev) => ({
      ...prev,
      mwTitles: prev.mwTitles.filter((_, i) => i !== index),
    }))
  }

  const searchMediaWiki = () => {
    const q = (editDialogSearchQuery || '').trim()
    if (!q) return
    fetch(`/api/mediawiki/search?query=${encodeURIComponent(q)}&limit=10`)
      .then((r) => r.json())
      .then((d) => {
        const list = (d.results || []).map((r) => r.title)
        setEditDialogSearchResults(list)
      })
      .catch(() => setEditDialogSearchResults([]))
  }

  const handleWriteToPreview = (content) => {
    if (!selectedSessionId || content == null) return
    fetch('/api/chat/article', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: selectedSessionId, content: content || '' }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.status === 'success' && d.article != null) {
          setArticle(d.article)
          loadRevisions()
        } else {
          toast?.error?.(d.error || '写入失败')
        }
      })
      .catch((e) => toast?.error?.(e?.message || '写入失败'))
  }

  const enterEditMode = () => {
    setEditDraft(previewContent ?? '')
    setEditMode(true)
  }
  const exitEditMode = () => {
    setEditMode(false)
  }
  const saveEditAndExit = () => {
    if (!selectedSessionId) return
    fetch('/api/chat/article', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: selectedSessionId, content: editDraft || '' }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.status === 'success' && d.article != null) {
          setArticle(d.article)
          setPreviewRevisionId(null)
          setShowDiffView(false)
          setEditMode(false)
          loadRevisions()
        } else {
          toast?.error?.(d.error || '保存失败')
        }
      })
      .catch((e) => {
        toast?.error?.(e?.message || '保存失败')
      })
  }

  const submitWechatOutputTask = async (e) => {
    e?.preventDefault?.()
    const title = (wechatOutputMetadata?.title || '').trim()
    if (!title) {
      toast?.warning?.('请输入标题')
      return
    }
    if (!(wechatOutputMetadata?.thumb_media_id || '').trim()) {
      toast?.warning?.('请上传封面或填写 thumb_media_id')
      return
    }
    setWechatOutputSubmitting(true)
    try {
      const payload = { ...wechatOutputMetadata, operation: 'add' }
      const meta = await prepareMetadataForSubmitAsync(WECHAT_MP_DRAFT_TASK_TYPE, payload)
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'wechat_mp_draft',
          priority: 2,
          max_retries: 3,
          metadata: meta,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (data.success) {
        toast?.info?.('任务已创建，可在任务管理中查看执行状态')
        setOutputDialog(null)
        navigate('/tasks', { state: data.task_id ? { detailTaskId: data.task_id } : {} })
      } else {
        toast?.error?.(formatWechatMpError('创建任务失败', new Error(data.detail || data.message || '创建任务失败')))
      }
    } catch (err) {
      toast?.error?.(formatWechatMpError('创建任务失败', err))
    }
    setWechatOutputSubmitting(false)
  }

  const handleCopyContent = (content) => {
    if (!content) return
    navigator.clipboard.writeText(content).then(
      () => toast?.info?.('已复制到剪贴板'),
      () => toast?.error?.('复制失败')
    )
  }

  const handleAddContentToInput = (content) => {
    if (!content) return
    setInput((prev) => (prev ? prev + '\n\n' + content : content))
  }

  /** 从助手回复中解析 ```patch ... ``` 代码块，用于「应用此 patch」 */
  const extractPatchBlock = (text) => {
    if (!text || typeof text !== 'string') return null
    const m = text.match(/```patch\s*\n([\s\S]*?)```/)
    return m ? m[1].trim() : null
  }

  const [applyingPatch, setApplyingPatch] = useState(false)
  const handleApplyPatch = async (patchText) => {
    if (!selectedSessionId || !patchText?.trim()) return
    setApplyingPatch(true)
    try {
      const res = await fetch('/api/chat/article/apply-patch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedSessionId, patch: patchText.trim() }),
      })
      const d = await res.json()
      if (d.status === 'success' && d.article != null) {
        setArticle(d.article)
        setPreviewRevisionId(null)
        loadRevisions()
      } else {
        toast?.error?.(d.error || 'patch 应用失败')
      }
    } catch (e) {
      toast?.error?.(e?.message || '应用失败')
    } finally {
      setApplyingPatch(false)
    }
  }

  /** 当前在预览区显示的内容：当前文章或选中的历史版本 */
  const previewContent = useMemo(() => {
    if (previewRevisionId == null) return article ?? ''
    const rev = revisions.find((r) => r.id === previewRevisionId)
    return rev?.content ?? article ?? ''
  }, [article, previewRevisionId, revisions])

  /** 打开「同步到公众号草稿」时拉取 schema 并用当前文章（Markdown）预填 content，提交时由 prepareMetadataForSubmitAsync 转为公众号 HTML */
  useEffect(() => {
    if (outputDialog !== 'wechat' || !previewContent) return
    fetch('/api/task-queue/task-types')
      .then((r) => r.json())
      .then((d) => {
        const list = d.task_types || []
        const wechat = list.find((t) => t.type === 'wechat_mp_draft')
        const schema = wechat?.metadata_schema || {}
        setWechatOutputSchema(schema)
        const defaults = getDefaultMetadata(schema)
        const { operation: _o, ...restDefaults } = defaults
        setWechatOutputMetadata({
          ...restDefaults,
          operation: 'add',
          content: previewContent,
        })
      })
      .catch(() => {
        setWechatOutputSchema({})
        setWechatOutputMetadata({ operation: 'add', content: previewContent })
      })
  }, [outputDialog, previewContent])

  /** 写文章场景固定为「新增草稿」，不展示「操作类型」；更新草稿需在任务管理里选定已有草稿（media_id） */
  const wechatOutputSchemaForForm = useMemo(() => {
    const { operation: _o, ...rest } = wechatOutputSchema
    return rest
  }, [wechatOutputSchema])

  const handlePatchSubmit = async () => {
    if (!selectedSessionId || !patchAnchor.trim()) return
    setPatchSubmitting(true)
    try {
      const res = await fetch('/api/chat/article/patch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: selectedSessionId,
          op: 'insert_after',
          anchor: patchAnchor.trim(),
          content: patchContent.trim(),
        }),
      })
      const d = await res.json()
      if (d.status === 'success' && d.article != null) {
        setArticle(d.article)
        setPreviewRevisionId(null)
        loadRevisions()
        setPatchDialogOpen(false)
        setPatchAnchor('')
        setPatchContent('')
      } else {
        toast?.error?.(d.error || '插入失败')
      }
    } catch (e) {
      toast?.error?.(e?.message || '请求失败')
    } finally {
      setPatchSubmitting(false)
    }
  }

  const handleRestoreRevision = (revisionId) => {
    if (!selectedSessionId) return
    fetch('/api/chat/article/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: selectedSessionId, revision_id: revisionId }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.status === 'success' && d.article != null) {
          setArticle(d.article)
          loadRevisions()
          toast?.info?.('已恢复该版本')
        } else {
          toast?.error?.(d.error || '恢复失败')
        }
      })
      .catch((e) => toast?.error?.(e?.message || '恢复失败'))
  }

  const saveEditDialog = () => {
    if (!editDialog) return
    setEditDialogSaving(true)
    const { sessionId, title, mwTitles } = editDialog
    Promise.all([
      fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: (title || '').trim() || null }),
      }).then((r) => r.json()),
      fetch('/api/chat/mw-sources', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, titles: mwTitles || [] }),
      }).then((r) => r.json()),
    ])
      .then(([patchRes, mwRes]) => {
        if (patchRes.success && (mwRes.status === 'success' || mwRes.success)) {
          loadSessions()
          closeEditDialog()
        } else {
          toast?.error?.(patchRes.error || mwRes.error || '保存失败')
        }
      })
      .catch((e) => toast?.error?.(e?.message || '保存失败'))
      .finally(() => setEditDialogSaving(false))
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">AI写作</h1>
        <p className="text-sm text-muted mt-1">
          左侧为写文章会话列表，中间对话、右侧为文章预览；会遵循写作画像。
        </p>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* 左侧：写文章会话列表（与公众号草稿左侧一致） */}
        <div
          className={`shrink-0 border-r border-border bg-white/[0.02] overflow-hidden transition-all duration-200 ${
            sidebarCollapsed ? 'w-8' : 'w-72 flex flex-col'
          }`}
        >
          {sidebarCollapsed ? (
            <div className="h-full flex flex-col items-center justify-start pt-3">
              <button
                type="button"
                onClick={() => setSidebarCollapsed(false)}
                className="px-1.5 py-1 rounded border border-border text-[11px] text-muted hover:bg-white/5"
                title="展开写文章会话列表"
              >
                展开
              </button>
            </div>
          ) : (
            <>
              <div className="shrink-0 p-3 border-b border-border space-y-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleNewSession}
                    className="flex-1 py-2.5 rounded-lg bg-accent hover:opacity-90 text-white text-sm font-medium"
                  >
                    新建会话
                  </button>
                  <button
                    type="button"
                    onClick={() => setSidebarCollapsed(true)}
                    className="px-2 py-2 rounded-lg border border-border text-xs text-muted hover:text-fg hover:bg-white/5"
                    title="收起写文章会话列表"
                  >
                    收起
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted">排序：</span>
                  <select
                    value={listSort}
                    onChange={(e) => setListSort(e.target.value)}
                    className="flex-1 min-w-0 rounded border border-border bg-white/5 text-[#e2e8f0] text-xs px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    <option value="updated_at">最近更新</option>
                    <option value="created_at">最近创建</option>
                  </select>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto">
                {sessionsLoading ? (
                  <div className="p-4 text-center text-muted text-sm">加载中…</div>
                ) : sessions.length === 0 ? (
                  <div className="p-4 text-muted text-sm">暂无写文章会话，点击上方新建</div>
                ) : (
                  <ul className="p-2 space-y-1">
                    {sessions.map((s) => (
                      <li key={s.session_id} className="group flex items-center gap-1 rounded-lg overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setSelectedSessionId(s.session_id)}
                          className={`flex-1 min-w-0 text-left px-3 py-2.5 rounded-lg text-sm truncate transition-colors ${
                            selectedSessionId === s.session_id
                              ? 'bg-accent/20 text-accent'
                              : 'text-muted hover:bg-white/5 hover:text-fg'
                          }`}
                          title={s.title || s.preview || s.session_id}
                        >
                          {displayLabel(s)}
                        </button>
                        <div className="shrink-0 flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            type="button"
                            onClick={(e) => openEditDialog(s.session_id, s.title || s.preview, e)}
                            className="p-1.5 rounded text-muted hover:bg-white/10 hover:text-fg"
                            title="编辑会话（重命名与参考文章）"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleClearSession(s.session_id, e)}
                            className="p-1.5 rounded text-muted hover:bg-white/10 hover:text-fg"
                            title="清空消息与文章草稿"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                              />
                            </svg>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleDeleteSession(s.session_id, e)}
                            className="p-1.5 rounded text-muted hover:bg-red-500/20 hover:text-red-400"
                            title="删除会话"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>

        {/* 中间：对话 */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0 border-r border-border">
          {!selectedSessionId ? (
            <div className="flex-1 flex items-center justify-center text-muted text-sm">
              请在左侧选择或新建一个写文章会话
            </div>
          ) : detailLoading ? (
            <div className="flex-1 flex items-center justify-center text-muted text-sm">
              加载中…
            </div>
          ) : (
            <>
              <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-3">
                {messages.length === 0 && (
                  <div className="text-muted text-sm rounded-lg bg-white/5 p-4 border border-border">
                    <p className="font-medium text-muted mb-2">示例开场：</p>
                    <ul className="list-disc list-inside space-y-1 text-muted">
                      <li>帮我写一篇文章，主题是「如何用 Python 做数据分析」</li>
                      <li>我想写一篇技术教程，读者是初学者，长度中等</li>
                    </ul>
                  </div>
                )}
                {messages.map((m, i) => {
                  const isHistorySummary =
                    m.role === 'assistant' &&
                    typeof m.content === 'string' &&
                    m.content.trim().startsWith('我们之前的对话内容如下')

                  return (
                  <div
                    key={i}
                    className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[85%] ${m.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col items-start'}`}>
                      <div
                        className={`rounded-lg px-4 py-2.5 text-sm whitespace-pre-wrap ${
                          m.role === 'user'
                            ? 'bg-accent/20 text-accent'
                            : isHistorySummary
                              ? 'bg-accent/5 text-fg border border-accent/40'
                              : 'bg-white/5 text-fg border border-border'
                        }`}
                      >
                        {m.content}
                      </div>
                      {m.role === 'user' && (
                        <div className="mt-1.5 flex items-center gap-2 flex-wrap justify-end">
                          <button
                            type="button"
                            onClick={() => handleAddToReference(m.content)}
                            className="px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
                          >
                            添加到参考信息
                          </button>
                        </div>
                      )}
                      {m.role === 'assistant' && (
                        <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                          {extractPatchBlock(m.content) && (
                            <button
                              type="button"
                              disabled={applyingPatch}
                              onClick={() => handleApplyPatch(extractPatchBlock(m.content))}
                              className="px-2.5 py-1 text-xs rounded border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10 disabled:opacity-50"
                            >
                              {applyingPatch ? '应用中…' : '应用此 patch'}
                            </button>
                            )}
                          <button
                            type="button"
                            onClick={() => handleWriteToPreview(m.content)}
                            className="px-2.5 py-1 text-xs rounded border border-border text-cyan-400 hover:bg-white/10"
                          >
                            接受修改
                          </button>
                          <button
                            type="button"
                            onClick={() => handleCopyContent(m.content)}
                            className="px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
                          >
                            复制
                          </button>
                          <button
                            type="button"
                            onClick={() => handleAddContentToInput(m.content)}
                            className="px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
                          >
                            加入输入框
                          </button>
                          <button
                            type="button"
                            onClick={() => handleAddToReference(m.content)}
                            className="px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
                          >
                            添加到参考信息
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  )
                })}
                {loading && (
                  <div className="flex justify-start items-center gap-3">
                    <div className="max-w-[85%] flex flex-col items-start">
                      <div
                        className={`rounded-lg px-4 py-2.5 text-sm whitespace-pre-wrap border border-border ${
                          streamingContent ? 'bg-white/5 text-fg' : 'text-muted bg-white/5'
                        }`}
                      >
                        {streamingContent || 'thinking…'}
                      </div>
                      <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                        <button
                          type="button"
                          onClick={handleStop}
                          className="px-3 py-1.5 text-sm rounded-lg border border-amber-500/50 text-amber-400 hover:bg-amber-500/10"
                        >
                          停止
                        </button>
                        {streamingContent && (
                          <button
                            type="button"
                            onClick={() => handleAddToReference(streamingContent)}
                            className="px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
                          >
                            添加到参考信息
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <div className="border-t border-border px-4 py-2">
                <button
                  type="button"
                  onClick={() => setReferencePanelOpen((v) => !v)}
                  className="text-xs text-muted hover:text-fg flex items-center gap-1"
                >
                  <span>{referencePanelOpen ? '收起参考信息' : '参考信息（可选）'}</span>
                  {referenceBlocks.filter((b) => (b.content || '').trim()).length > 0 && (
                    <span className="inline-flex items-center justify-center min-w-[1.25rem] px-1 rounded-full bg-white/10 text-[11px] text-muted">
                      {referenceBlocks.filter((b) => (b.content || '').trim()).length}
                    </span>
                  )}
                </button>
                {referencePanelOpen && (
                  <div className="mt-2 space-y-2">
                    {referenceBlocks.length === 0 && (
                      <p className="text-[11px] text-muted">
                        可以在这里粘贴多段资料作为上下文，助手回答时会一并参考，但不会单独显示为消息。
                      </p>
                    )}
                    {referenceBlocks.map((block, idx) => (
                      <div
                        key={block.id}
                        className="rounded-lg border border-border bg-white/5 px-3 py-2 space-y-2"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-muted shrink-0">
                            参考 {idx + 1}
                          </span>
                          <input
                            type="text"
                            value={block.title}
                            onChange={(e) =>
                              handleUpdateReferenceBlock(block.id, 'title', e.target.value)
                            }
                            placeholder="可选：给这段资料起个标题"
                            className="flex-1 min-w-0 px-2 py-1 rounded bg-transparent border border-border/60 text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-accent"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveReferenceBlock(block.id)}
                            className="px-2 py-1 text-[11px] rounded border border-border text-muted hover:text-red-400 hover:border-red-400/60"
                          >
                            删除
                          </button>
                        </div>
                        <textarea
                          rows={3}
                          value={block.content}
                          onChange={(e) =>
                            handleUpdateReferenceBlock(block.id, 'content', e.target.value)
                          }
                          placeholder="在这里粘贴这段参考资料文本（支持多段）。"
                          className="w-full px-2 py-1.5 rounded bg-black/20 border border-border text-xs text-white placeholder-[#64748b] resize-y focus:outline-none focus:border-accent"
                        />
                      </div>
                    ))}
                    <div className="flex items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={handleAddReferenceBlock}
                        className="px-2.5 py-1 text-xs rounded border border-border text-muted hover:text-fg hover:bg-white/5"
                      >
                        + 新增参考块
                      </button>
                      <p className="text-[11px] text-muted text-right">
                        参考信息会自动加入每次请求的隐藏上下文，无需在输入框里重复粘贴。
                      </p>
                    </div>
                  </div>
                )}
              </div>
              <ChatInput
                value={input}
                onChange={setInput}
                onSubmit={() => handleSubmit({ preventDefault: () => {} })}
                placeholder="输入消息，Enter 换行，Ctrl+Enter 发送"
                disabled={loading}
                submitLabel="发送"
              />
            </>
          )}
        </div>

        {/* 右侧：文章预览 */}
        <div className="w-[560px] shrink-0 flex flex-col min-h-0 bg-white/[0.02] overflow-hidden">
          <div className="shrink-0 px-4 py-3 border-b border-border flex items-center justify-between gap-2 flex-wrap">
            <h2 className="text-sm font-medium text-muted">文章预览</h2>
            <div className="flex items-center gap-2">
              {previewContent && !editMode && (
                <button
                  type="button"
                  onClick={enterEditMode}
                  className="text-xs px-2 py-1 rounded border border-border text-cyan-400 hover:bg-cyan-500/10"
                >
                  编辑
                </button>
              )}
              {editMode && (
                <>
                  <button
                    type="button"
                    onClick={saveEditAndExit}
                    className="text-xs px-2 py-1 rounded border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
                  >
                    保存
                  </button>
                  <button
                    type="button"
                    onClick={exitEditMode}
                    className="text-xs px-2 py-1 rounded border border-border text-muted hover:bg-white/10"
                  >
                    取消
                  </button>
                </>
              )}
              {selectedSessionId && article && (
                <button
                  type="button"
                  onClick={() => { setPatchAnchor(''); setPatchContent(''); setPatchDialogOpen(true) }}
                  className="text-xs px-2 py-1 rounded border border-border text-muted hover:bg-white/10"
                >
                  局部插入
                </button>
              )}
              {selectedSessionId && (
                <button
                  type="button"
                  onClick={() => setShowRevisions((s) => !s)}
                  className="text-xs text-muted hover:text-muted"
                >
                  {showRevisions ? '收起历史' : '历史版本'}
                </button>
              )}
            </div>
          </div>
          {showRevisions && selectedSessionId && (
            <div className="shrink-0 border-b border-border max-h-48 overflow-y-auto p-2 bg-black/20">
              {revisionsLoading ? (
                <p className="text-xs text-muted">加载中…</p>
              ) : revisions.length === 0 ? (
                <p className="text-xs text-muted">暂无版本记录</p>
              ) : (
                <ul className="space-y-1">
                  {revisions.map((rev) => (
                    <li
                      key={rev.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setPreviewRevisionId(rev.id)}
                      onKeyDown={(e) => e.key === 'Enter' && setPreviewRevisionId(rev.id)}
                      className={`flex items-center justify-between gap-2 text-xs rounded px-2 py-1.5 cursor-pointer ${
                        previewRevisionId === rev.id ? 'bg-cyan-500/20 border border-cyan-500/50' : 'hover:bg-white/10'
                      }`}
                    >
                      <span className="text-muted truncate flex-1 min-w-0">
                        {rev.created_at?.slice(0, 19).replace('T', ' ')} · {rev.source === 'agent' ? '助手' : '用户'}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleRestoreRevision(rev.id)
                          setPreviewRevisionId(null)
                        }}
                        className="shrink-0 px-2 py-0.5 rounded text-cyan-400 hover:bg-white/10"
                      >
                        恢复
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-2 bg-[#f6f8fa]">
            {previewRevisionId != null && (
              <div className="shrink-0 flex items-center justify-between gap-2 rounded-lg px-3 py-2 bg-cyan-500/10 border border-cyan-500/30 text-sm flex-wrap">
                <span className="text-cyan-300">
                  正在查看历史版本 · {revisions.find((r) => r.id === previewRevisionId)?.created_at?.slice(0, 19).replace('T', ' ') ?? ''}
                </span>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1.5 text-xs text-muted cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showDiffView}
                      onChange={(e) => setShowDiffView(e.target.checked)}
                      className="rounded border-border"
                    />
                    差异对比
                  </label>
                  <button
                    type="button"
                    onClick={() => { setPreviewRevisionId(null); setShowDiffView(false) }}
                    className="px-2 py-1 text-xs rounded border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/20"
                  >
                    返回当前
                  </button>
                </div>
              </div>
            )}
            {editMode ? (
                <div className="flex-1 min-h-0 flex flex-col gap-2">
                  <textarea
                    value={editDraft}
                    onChange={(e) => setEditDraft(e.target.value)}
                    placeholder="在此编辑文章内容（Markdown）…"
                    className="flex-1 min-h-[200px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-mono leading-relaxed"
                    spellCheck={false}
                  />
                </div>
              ) : showDiffView && previewRevisionId != null ? (
                <ArticleDiffView
                  oldText={article ?? ''}
                  newText={previewContent}
                  className="mt-2"
                />
              ) : previewContent ? (
                <MarkdownPreview
                  markdown={previewContent}
                  className="p-4 min-h-[200px] w-full"
                  theme="dark"
                />
              ) : (
                <p className="text-muted text-sm">
                  {selectedSessionId ? '点击对话中助手回复的「接受修改」可更新文章，并作为后续润色/续写的上下文。' : '选择会话后，此处显示该会话的文章草稿。'}
                </p>
              )}
          </div>
          {previewContent && (
            <div className="shrink-0 px-4 py-3 border-t border-border flex items-center justify-center gap-3 bg-black/20">
              <MarkdownActionButtons
                content={previewContent}
                onSendToArticle={handleAddContentToInput}
                sendToArticleLabel="加入输入框"
                onAddToReference={handleAddToReference}
                extra={
                  <button
                    type="button"
                    onClick={() => setOutputDialog('wechat')}
                    className="px-4 py-2 rounded-lg border border-border text-muted hover:bg-white/10 hover:text-fg text-sm"
                  >
                    同步到公众号草稿
                  </button>
                }
              />
            </div>
          )}
        </div>
      </div>

      {/* 编辑会话对话框：重命名 + 参考文章（MediaWiki） */}
      {editDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={closeEditDialog}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-center px-5 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-white">编辑会话</h3>
              <button
                type="button"
                onClick={closeEditDialog}
                className="text-muted hover:text-fg text-2xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
              <div>
                <label className="block text-sm text-muted mb-1">会话标题</label>
                <input
                  type="text"
                  value={editDialog.title}
                  onChange={(e) => setEditDialog((prev) => ({ ...prev, title: e.target.value }))}
                  className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                  placeholder="新会话"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-2">参考文章（MediaWiki）</label>
                <p className="text-xs text-muted mb-2">添加 MediaWiki 页面标题，生成文章时会读取这些页面内容作为参考。</p>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={editDialogMwInput}
                    onChange={(e) => setEditDialogMwInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addMwTitle(editDialogMwInput))}
                    className="flex-1 rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                    placeholder="输入页面标题后按回车或点击添加"
                  />
                  <button
                    type="button"
                    onClick={() => addMwTitle(editDialogMwInput)}
                    className="shrink-0 px-3 py-2 rounded-lg bg-white/10 text-[#e2e8f0] text-sm hover:bg-white/15"
                  >
                    添加
                  </button>
                </div>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={editDialogSearchQuery}
                    onChange={(e) => setEditDialogSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), searchMediaWiki())}
                    className="flex-1 rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent"
                    placeholder="搜索 MediaWiki 页面"
                  />
                  <button
                    type="button"
                    onClick={searchMediaWiki}
                    className="shrink-0 px-3 py-2 rounded-lg bg-white/10 text-[#e2e8f0] text-sm hover:bg-white/15"
                  >
                    搜索
                  </button>
                </div>
                {editDialogSearchResults.length > 0 && (
                  <div className="mb-2 p-2 rounded-lg bg-white/5 border border-border max-h-32 overflow-y-auto">
                    <p className="text-xs text-muted mb-1">点击添加：</p>
                    <ul className="space-y-1">
                      {editDialogSearchResults.map((tit) => (
                        <li key={tit}>
                          <button
                            type="button"
                            onClick={() => { addMwTitle(tit); setEditDialogSearchResults((prev) => prev.filter((t) => t !== tit)); }}
                            className="w-full text-left px-2 py-1.5 rounded text-sm text-[#e2e8f0] hover:bg-white/10"
                          >
                            {tit}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <ul className="space-y-1.5">
                  {(editDialog.mwTitles || []).map((tit, idx) => (
                    <li key={`${tit}-${idx}`} className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-sm text-[#e2e8f0]">
                      <span className="flex-1 min-w-0 truncate">{tit}</span>
                      <button
                        type="button"
                        onClick={() => removeMwTitle(idx)}
                        className="shrink-0 p-1 rounded text-muted hover:bg-white/10 hover:text-red-400"
                        title="移除"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </li>
                  ))}
                </ul>
                {(editDialog.mwTitles || []).length === 0 && (
                  <p className="text-xs text-muted">暂无参考页面，可输入标题添加或搜索后选择。</p>
                )}
              </div>
            </div>
            <div className="shrink-0 flex gap-3 px-5 py-4 border-t border-border bg-surface">
              <button
                type="button"
                onClick={closeEditDialog}
                className="flex-1 px-4 py-2 rounded-lg border border-border text-muted hover:text-fg"
              >
                取消
              </button>
              <button
                type="button"
                onClick={saveEditDialog}
                disabled={editDialogSaving}
                className="flex-1 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 disabled:opacity-50"
              >
                {editDialogSaving ? '保存中…' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 局部插入：在锚点后插入段落 */}
      {patchDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setPatchDialogOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-center px-5 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-white">局部插入</h3>
              <button
                type="button"
                onClick={() => setPatchDialogOpen(false)}
                className="text-muted hover:text-fg text-2xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
              <p className="text-xs text-muted">在文章中找到「锚点」首次出现的位置，在其后插入下面填写的内容，其余不变。</p>
              <div>
                <label className="block text-sm text-muted mb-1">锚点（文中唯一出现的文本，将在此之后插入）</label>
                {(article || '')
                  .split('\n')
                  .map((l) => l.trim())
                  .filter((l) => /^#{1,6}\s+.+/.test(l))
                  .length > 0 && (
                  <div className="mb-2">
                    <span className="text-xs text-muted mr-2">快捷选择：</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {(article || '')
                        .split('\n')
                        .map((l) => l.trim())
                        .filter((l) => /^#{1,6}\s+.+/.test(l))
                        .map((line, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => setPatchAnchor(line)}
                            className="text-xs px-2 py-1 rounded border border-border text-muted hover:bg-white/10 hover:border-cyan-500/50 max-w-full truncate"
                            title={line}
                          >
                            {line.length > 28 ? line.slice(0, 26) + '…' : line}
                          </button>
                        ))}
                    </div>
                  </div>
                )}
                <textarea
                  value={patchAnchor}
                  onChange={(e) => setPatchAnchor(e.target.value)}
                  placeholder="例如：**三个铁证表明AI已深度参战：** 或从上方选择小节标题"
                  rows={2}
                  className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">要插入的段落（支持 Markdown）</label>
                <textarea
                  value={patchContent}
                  onChange={(e) => setPatchContent(e.target.value)}
                  placeholder="输入要插入的段落…"
                  rows={6}
                  className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-accent resize-y"
                />
              </div>
            </div>
            <div className="shrink-0 flex gap-3 px-5 py-4 border-t border-border bg-surface">
              <button
                type="button"
                onClick={() => setPatchDialogOpen(false)}
                className="flex-1 px-4 py-2 rounded-lg border border-border text-muted hover:text-fg"
              >
                取消
              </button>
              <button
                type="button"
                onClick={handlePatchSubmit}
                disabled={patchSubmitting || !patchAnchor.trim()}
                className="flex-1 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 disabled:opacity-50"
              >
                {patchSubmitting ? '插入中…' : '插入'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 输出：同步到公众号草稿（复用 TaskParamsForm，与「编辑后重新执行」同一组件；正文为当前文章 Markdown，提交时转公众号 HTML） */}
      {outputDialog === 'wechat' && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setOutputDialog(null)}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full mx-4 max-w-5xl h-[95vh] max-h-[95vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-center px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-white">同步到公众号草稿</h3>
              <button type="button" onClick={() => setOutputDialog(null)} className="text-2xl text-muted hover:text-fg">&times;</button>
            </div>
            <form onSubmit={submitWechatOutputTask} className="flex flex-col flex-1 min-h-0 overflow-hidden">
              <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
                <p className="text-xs text-muted">将当前文章作为正文新建一篇公众号草稿（Markdown 提交时转为公众号 HTML）。创建任务后由任务队列执行，可在任务管理中审计。请填写标题与封面。</p>
                <TaskParamsForm
                  taskType="wechat_mp_draft"
                  schema={wechatOutputSchemaForForm}
                  metadata={wechatOutputMetadata}
                  setMetadata={setWechatOutputMetadata}
                  fieldIdPrefix="article-wechat-output"
                  onCoverUpload={(file) => WECHAT_MP_API.uploadCover(file)}
                />
              </div>
              <div className="shrink-0 flex gap-3 px-6 py-4 border-t border-border bg-surface">
                <button type="button" onClick={() => setOutputDialog(null)} className="flex-1 px-4 py-2 border border-border rounded-lg text-muted hover:text-fg">取消</button>
                <button
                  type="submit"
                  disabled={wechatOutputSubmitting || !(wechatOutputMetadata?.title || '').trim() || !(wechatOutputMetadata?.thumb_media_id || '').trim()}
                  className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50"
                >
                  {wechatOutputSubmitting ? '提交中…' : '创建任务'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
