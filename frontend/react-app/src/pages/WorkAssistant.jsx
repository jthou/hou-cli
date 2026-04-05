/**
 * 工作助手 - 通用对话入口，支持模型选择、会话持久化、参考块（与写作助手概念和操作一致）
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import ChatInput from '../components/ChatInput'
import MarkdownPreview from '../components/MarkdownPreview'
import StreamingReasoningPanel from '../components/StreamingReasoningPanel'
import { useToast } from '../components/ToastModal'
import { useSelectableModels } from '../hooks/useSelectableModels'
import ModelSelector from '../components/ModelSelector'
import { buildArticleWritingMessageForModel, extractUserQuestionForDisplay } from '../utils/referenceUtils'
import { shouldAppendStreamingPlainText } from '../utils/streamSseContent'
import { stripAgentStatusPrefix } from '../utils/streamUi'
import { useReferenceBlocks } from '../hooks/useReferenceBlocks'
import ReferenceBlocksPanel from '../components/ReferenceBlocksPanel'
import UserMessageActionButtons from '../components/UserMessageActionButtons'
import { useDeleteSessionMessage } from '../hooks/useDeleteSessionMessage'
import { useBatchDeleteSessions } from '../hooks/useBatchDeleteSessions'
import { useBatchDeleteMessages } from '../hooks/useBatchDeleteMessages'
import ContextSelectionPanel from '../components/ContextSelectionPanel'

const SESSION_TYPE = 'work_assistant'
const STORAGE_KEY = 'work_assistant_selected_session'

export default function WorkAssistant() {
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const { providers, models: selectableModels, defaultModel, loading: modelsLoading } = useSelectableModels()
  const [sessions, setSessions] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [selectedSessionId, setSelectedSessionId] = useState(() => {
    try {
      return sessionStorage.getItem(STORAGE_KEY) || null
    } catch {
      return null
    }
  })
  const [messages, setMessages] = useState([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingToolCalls, setStreamingToolCalls] = useState([])
  /** 时间：2026-04-04；理由：__REASONING__ 流式思考；方法：shouldAppendStreamingPlainText.onReasoningDelta */
  const [streamingReasoning, setStreamingReasoning] = useState('')
  const [contextSelectionMeta, setContextSelectionMeta] = useState(null)
  const [selectedModel, setSelectedModel] = useState('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [referencePanelOpen, setReferencePanelOpen] = useState(false)
  /** 2026-03-21：侧栏/对话区批量删除（设计见 docs/design/01-batch-delete-sessions-and-messages-design.md） */
  const [sessionBulkMode, setSessionBulkMode] = useState(false)
  const [bulkSessionIds, setBulkSessionIds] = useState([])
  const [messageBulkMode, setMessageBulkMode] = useState(false)
  const [bulkMessageIds, setBulkMessageIds] = useState([])
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)
  const streamingContentRef = useRef('')
  const {
    referenceBlocks,
    handleAddReferenceBlock,
    handleAddReferenceBlockWithContent,
    handleUpdateReferenceBlock,
    handleRemoveReferenceBlock,
    reloadBlocks,
  } = useReferenceBlocks(selectedSessionId, referencePanelOpen, SESSION_TYPE)

  const handleAddReferenceBlockAndOpen = () => {
    setReferencePanelOpen(true)
    handleAddReferenceBlock()
  }

  useEffect(() => {
    if (defaultModel && !selectedModel) setSelectedModel(defaultModel)
    else if (!selectedModel && selectableModels?.length) setSelectedModel(selectableModels[0]?.value || '')
  }, [defaultModel, selectedModel, selectableModels])

  const loadSessions = useCallback(() => {
    setSessionsLoading(true)
    fetch(`/api/sessions/list?type=${encodeURIComponent(SESSION_TYPE)}&limit=50`)
      .then((r) => r.json())
      .then((d) => {
        if (d.sessions) setSessions(d.sessions)
        if (d.error) toast?.error?.(`加载会话列表失败：${d.error}`)
      })
      .catch((e) => toast?.error?.(e?.message || '加载会话列表失败'))
      .finally(() => setSessionsLoading(false))
  }, [toast])

  const executeBatchDeleteSessions = useBatchDeleteSessions({
    sessionType: SESSION_TYPE,
    loadSessions,
    selectedSessionId,
    setSelectedSessionId,
    setMessages,
    storageKey: STORAGE_KEY,
    toast,
  })
  const executeBatchDeleteMessages = useBatchDeleteMessages({
    selectedSessionId,
    setMessages,
    toast,
  })

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    if (sessions.length === 0) {
      setSelectedSessionId(null)
      return
    }
    const ids = new Set(sessions.map((s) => s.session_id))
    if (!selectedSessionId || !ids.has(selectedSessionId)) {
      const first = sessions[0]?.session_id
      if (first) {
        setSelectedSessionId(first)
        try {
          sessionStorage.setItem(STORAGE_KEY, first)
        } catch (_) {}
      }
    }
  }, [sessions, selectedSessionId])

  useEffect(() => {
    try {
      if (selectedSessionId) {
        sessionStorage.setItem(STORAGE_KEY, selectedSessionId)
      } else {
        sessionStorage.removeItem(STORAGE_KEY)
      }
    } catch (_) {}
  }, [selectedSessionId])

  useEffect(() => {
    setBulkMessageIds([])
    setMessageBulkMode(false)
  }, [selectedSessionId])

  useEffect(() => {
    if (!selectedSessionId) {
      setMessages([])
      setDetailLoading(false)
      return
    }
    if (loading) return // 发送中不覆盖，避免新建会话时清空刚添加的用户消息
    setDetailLoading(true)
    setMessages([])
    fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.messages)) {
          setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id })))
        } else if (d.error) {
          toast?.error?.(`加载历史失败：${d.error}`)
        }
      })
      .catch((e) => toast?.error?.(e?.message || '加载历史失败'))
      .finally(() => setDetailLoading(false))
  }, [selectedSessionId, loading])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  /** 从 AddReference 页跳回时聚焦指定会话并重新加载参考块 */
  useEffect(() => {
    const focusId = location.state?.focusSessionId
    if (!focusId || typeof focusId !== 'string') return
    navigate(location.pathname + location.search, { replace: true, state: {} })
    setSelectedSessionId(focusId)
    try {
      sessionStorage.setItem(STORAGE_KEY, focusId)
    } catch (_) {}
    reloadBlocks(focusId)
  }, [location.state?.focusSessionId, location.pathname, location.search, navigate, reloadBlocks])

  const handleDeleteMessage = useDeleteSessionMessage({ selectedSessionId, setMessages, toast })

  const toggleBulkSession = (sid) => {
    setBulkSessionIds((prev) =>
      prev.includes(sid) ? prev.filter((x) => x !== sid) : [...prev, sid]
    )
  }

  const handleBulkDeleteSessions = async () => {
    if (bulkSessionIds.length === 0) return
    const ok = await toast.confirm(
      `确定删除选中的 ${bulkSessionIds.length} 个会话？删除后不可恢复。`
    )
    if (!ok) return
    await executeBatchDeleteSessions(bulkSessionIds)
    setBulkSessionIds([])
    setSessionBulkMode(false)
  }

  const toggleBulkMessage = (mid) => {
    if (!mid) return
    setBulkMessageIds((prev) =>
      prev.includes(mid) ? prev.filter((x) => x !== mid) : [...prev, mid]
    )
  }

  const handleBulkDeleteMessages = async () => {
    if (bulkMessageIds.length === 0) return
    const ok = await toast.confirm(
      `确定删除选中的 ${bulkMessageIds.length} 条消息？删除后不可恢复。`
    )
    if (!ok) return
    await executeBatchDeleteMessages(bulkMessageIds)
    setBulkMessageIds([])
    setMessageBulkMode(false)
  }

  const handleDeleteSession = async (sessionId, e) => {
    e?.stopPropagation?.()
    if (!sessionId) return
    const ok = await toast.confirm('确定删除该会话？删除后不可恢复，再次对话时不会带入该历史。')
    if (!ok) return
    try {
      const r = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
      const d = await r.json()
      if (d.success) {
        loadSessions()
        if (selectedSessionId === sessionId) {
          setSelectedSessionId(null)
          setMessages([])
          try {
            sessionStorage.removeItem(STORAGE_KEY)
          } catch (_) {}
        }
      } else {
        toast.error(d.error || '删除失败')
      }
    } catch (err) {
      toast.error(err?.message || '删除失败')
    }
  }

  const handleNewSession = () => {
    fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata: { type: SESSION_TYPE } }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.session_id) {
          loadSessions()
          setSelectedSessionId(d.session_id)
        }
      })
      .catch(() => {})
  }

  const handleStop = () => {
    abortControllerRef.current?.abort()
  }

  const handleRegenerate = async (messageId) => {
    if (!selectedSessionId || !messageId || loading) return
    const idx = messages.findIndex((m) => m.message_id === messageId)
    if (idx >= 0) {
      setMessages((prev) => prev.slice(0, idx + 1))
    }
    setLoading(true)
    setStreamingContent('')
    setStreamingReasoning('')
    setStreamingToolCalls([])
    // 时间：2026-03-13；理由：新一轮流式前清空上轮「选用上下文」；方法与 GeneralChat handleRegenerate 一致
    setContextSelectionMeta(null)
    const ac = new AbortController()
    abortControllerRef.current = ac
    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: '',
          session_id: selectedSessionId,
          context_type: SESSION_TYPE,
          regenerate_from_message_id: messageId,
          ...(selectedModel ? { model: selectedModel } : {}),
        }),
        signal: ac.signal,
      })
      if (!res.ok) {
        setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${res.statusText || res.status}` }])
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      // 时间：2026-03-13；理由：再生与首答共用编排帧，需解析 __TOOL__ / __CTX_META__ 且避免重复 done；方法：与 handleSubmit 对齐 streamTerminalHandled
      let streamTerminalHandled = false
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
                if (
                  shouldAppendStreamingPlainText(raw, {
                    onToolCall: (toolData) => {
                      if (toolData?.name) {
                        setStreamingToolCalls((prev) => [...prev, {
                          name: toolData.name,
                          args: toolData.args || {},
                          success: toolData.success,
                          result: toolData.result,
                          error: toolData.error,
                        }])
                      }
                    },
                    onContextMeta: (m) => setContextSelectionMeta(m),
                    onReasoningDelta: (d) => setStreamingReasoning((prev) => prev + d),
                  })
                ) {
                  fullContent += raw
                  streamingContentRef.current = fullContent
                  setStreamingContent(fullContent)
                }
              } else if (obj.status === 'done') {
                if (streamTerminalHandled) {
                  fullContent = ''
                  continue
                }
                streamTerminalHandled = true
                setContextSelectionMeta(null)
                fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`)
                  .then((r) => r.json())
                  .then((d) => {
                    if (d.success && Array.isArray(d.messages)) {
                      setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id })))
                    }
                  })
                  .catch(() => {})
                setStreamingContent('')
                setStreamingReasoning('')
                setStreamingToolCalls([])
                streamingContentRef.current = ''
                fullContent = ''
              } else if (obj.status === 'error') {
                setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
                setStreamingContent('')
                setStreamingReasoning('')
                setStreamingToolCalls([])
                setContextSelectionMeta(null)
                streamingContentRef.current = ''
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
              if (
                shouldAppendStreamingPlainText(raw, {
                  onToolCall: (toolData) => {
                    if (toolData?.name) {
                      setStreamingToolCalls((prev) => [...prev, {
                        name: toolData.name,
                        args: toolData.args || {},
                        success: toolData.success,
                        result: toolData.result,
                        error: toolData.error,
                      }])
                    }
                  },
                  onContextMeta: (m) => setContextSelectionMeta(m),
                  onReasoningDelta: (d) => setStreamingReasoning((prev) => prev + d),
                })
              ) {
                fullContent += raw
                streamingContentRef.current = fullContent
                setStreamingContent(fullContent)
              }
            } else if (obj.status === 'done') {
              if (streamTerminalHandled) {
                fullContent = ''
                continue
              }
              streamTerminalHandled = true
              setContextSelectionMeta(null)
              fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`)
                .then((r) => r.json())
                .then((d) => {
                  if (d.success && Array.isArray(d.messages)) {
                    setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id })))
                  }
                })
                .catch(() => {})
              setStreamingContent('')
              setStreamingReasoning('')
              setStreamingToolCalls([])
              streamingContentRef.current = ''
              fullContent = ''
            } else if (obj.status === 'error') {
              setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
              setStreamingContent('')
              setStreamingReasoning('')
              setStreamingToolCalls([])
              setContextSelectionMeta(null)
              streamingContentRef.current = ''
            }
          }
        } catch (_) {}
      }
    } catch (err) {
      if (err?.name === 'AbortError') return
      setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${err?.message || '请求失败'}` }])
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleSubmit = async (e) => {
    e?.preventDefault?.()
    const text = (input || '').trim()
    if (!text) return

    const messageForModel = buildArticleWritingMessageForModel(referenceBlocks, text)

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setStreamingContent('')
    setStreamingReasoning('')
    setStreamingToolCalls([])
    // 时间：2026-03-13；理由：新提问清空上轮上下文选用展示；方法：与 GeneralChat handleSubmit 一致
    setContextSelectionMeta(null)
    setLoading(true) // 先设 loading，再创建会话，避免 useEffect 覆盖消息

    let sessionId = selectedSessionId
    if (!sessionId) {
      const createRes = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metadata: { type: SESSION_TYPE } }),
      }).then((r) => r.json())
      if (!createRes.success || !createRes.session_id) {
        setLoading(false)
        return
      }
      sessionId = createRes.session_id
      setSelectedSessionId(sessionId)
      loadSessions()
    }
    const isFirstMessage = messages.length === 0
    const ac = new AbortController()
    abortControllerRef.current = ac

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageForModel,
          session_id: sessionId,
          context_type: SESSION_TYPE,
          ...(selectedModel ? { model: selectedModel } : {}),
        }),
        signal: ac.signal,
      })
      if (!res.ok) {
        setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${res.statusText || res.status}` }])
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      // 时间：2026-03-13；理由：与 GeneralChat 一致，避免多段 done 触发重复 fetch/乐观追加；方法：streamTerminalHandled
      let streamTerminalHandled = false
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
                if (
                  shouldAppendStreamingPlainText(raw, {
                    onToolCall: (toolData) => {
                      if (toolData?.name) {
                        setStreamingToolCalls((prev) => [...prev, {
                          name: toolData.name,
                          args: toolData.args || {},
                          success: toolData.success,
                          result: toolData.result,
                          error: toolData.error,
                        }])
                      }
                    },
                    onContextMeta: (m) => setContextSelectionMeta(m),
                    onReasoningDelta: (d) => setStreamingReasoning((prev) => prev + d),
                  })
                ) {
                  fullContent += raw
                  streamingContentRef.current = fullContent
                  setStreamingContent(fullContent)
                }
              } else if (obj.status === 'done') {
                if (streamTerminalHandled) {
                  fullContent = ''
                  continue
                }
                streamTerminalHandled = true
                const finalContent = fullContent.trim() || '（助手未返回内容）'
                setStreamingContent('')
                setStreamingReasoning('')
                setStreamingToolCalls([])
                setContextSelectionMeta(null)
                streamingContentRef.current = ''
                if (isFirstMessage && text) {
                  fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: text.slice(0, 30).trim() || text.slice(0, 30) }),
                  })
                    .then((r) => r.json())
                    .then((d) => { if (d.success) loadSessions() })
                    .catch(() => {})
                }
                fetch(`/api/sessions/${encodeURIComponent(sessionId)}`)
                  .then((r) => r.json())
                  .then((d) => {
                    if (d.success && Array.isArray(d.messages)) {
                      setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id })))
                    } else {
                      setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
                    }
                  })
                  .catch(() => setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }]))
                fullContent = ''
              } else if (obj.status === 'error') {
                setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
                setStreamingContent('')
                setStreamingReasoning('')
                setStreamingToolCalls([])
                setContextSelectionMeta(null)
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
              if (
                shouldAppendStreamingPlainText(raw, {
                  onToolCall: (toolData) => {
                    if (toolData?.name) {
                      setStreamingToolCalls((prev) => [...prev, {
                        name: toolData.name,
                        args: toolData.args || {},
                        success: toolData.success,
                        result: toolData.result,
                        error: toolData.error,
                      }])
                    }
                  },
                  onContextMeta: (m) => setContextSelectionMeta(m),
                  onReasoningDelta: (d) => setStreamingReasoning((prev) => prev + d),
                })
              ) {
                fullContent += raw
                streamingContentRef.current = fullContent
                setStreamingContent(fullContent)
              }
            } else if (obj.status === 'done') {
              if (streamTerminalHandled) {
                fullContent = ''
                continue
              }
              streamTerminalHandled = true
              const finalContent = fullContent.trim() || '（助手未返回内容）'
              setStreamingContent('')
              setStreamingReasoning('')
              streamingContentRef.current = ''
              if (isFirstMessage && text) {
                fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
                  method: 'PATCH',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ title: text.slice(0, 30).trim() || text.slice(0, 30) }),
                })
                  .then((r) => r.json())
                  .then((d) => { if (d.success) loadSessions() })
                  .catch(() => {})
              }
              setStreamingToolCalls([])
              setContextSelectionMeta(null)
              fetch(`/api/sessions/${encodeURIComponent(sessionId)}`)
                .then((r) => r.json())
                .then((d) => {
                  if (d.success && Array.isArray(d.messages)) {
                    setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id })))
                  } else {
                    setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
                  }
                })
                .catch(() => setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }]))
              fullContent = ''
            } else if (obj.status === 'error') {
              setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
              setStreamingContent('')
              setStreamingReasoning('')
              setStreamingToolCalls([])
              setContextSelectionMeta(null)
              streamingContentRef.current = ''
              fullContent = ''
            }
          }
          setStreamingContent('')
          setStreamingReasoning('')
          setContextSelectionMeta(null)
          streamingContentRef.current = ''
        } catch (_) {}
      }
    } catch (err) {
      if (err?.name === 'AbortError') return
      setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${err?.message || '请求失败'}` }])
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="工作助手"
        actions={
          <Link
            to="/settings/work-config"
            className="px-3 py-1.5 rounded border border-border text-sm text-muted hover:text-fg hover:bg-white/10"
          >
            工作配置
          </Link>
        }
      />
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* 左侧会话列表（可收缩） */}
        <div
          className={`shrink-0 flex flex-col border-r border-border bg-surface/30 transition-[width] ${
            sidebarCollapsed ? 'w-8' : 'w-72'
          }`}
        >
          {sidebarCollapsed ? (
            <div className="h-full flex flex-col items-center justify-start pt-3">
              <button
                type="button"
                onClick={() => setSidebarCollapsed(false)}
                className="px-1.5 py-1 rounded border border-border text-[11px] text-muted hover:text-fg hover:bg-white/5"
                title="展开会话列表"
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
                    title="收起会话列表"
                  >
                    收起
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setSessionBulkMode((v) => !v)
                    setBulkSessionIds([])
                  }}
                  className={`w-full py-1.5 text-xs rounded-lg border ${
                    sessionBulkMode
                      ? 'border-accent text-accent bg-accent/10'
                      : 'border-border text-muted hover:bg-white/5'
                  }`}
                >
                  {sessionBulkMode ? '退出多选会话' : '多选会话'}
                </button>
              </div>
              <div className="flex-1 overflow-y-auto">
            {sessionsLoading && (
              <div className="p-4 text-center text-muted text-sm">加载中…</div>
            )}
            {!sessionsLoading && sessions.length === 0 && (
              <div className="p-4 text-muted text-sm">暂无会话，点击上方新建</div>
            )}
            {!sessionsLoading &&
              sessions.length > 0 && (
              <ul className="p-2 space-y-1">
              {sessions.map((s) => (
                <li key={s.session_id} className="flex items-center gap-1 rounded-lg overflow-hidden">
                {sessionBulkMode && (
                  <input
                    type="checkbox"
                    className="shrink-0 ml-1 rounded border-border"
                    checked={bulkSessionIds.includes(s.session_id)}
                    onChange={() => toggleBulkSession(s.session_id)}
                    title="选中以批量删除"
                  />
                )}
                <div
                  className={`flex-1 flex items-center gap-1 min-w-0 px-3 py-2.5 text-sm rounded-lg ${
                    selectedSessionId === s.session_id
                      ? 'bg-accent/20 text-accent'
                      : 'text-muted hover:bg-white/5 hover:text-fg'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => {
                      if (!sessionBulkMode) setSelectedSessionId(s.session_id)
                    }}
                    className="flex-1 min-w-0 text-left truncate"
                    title={s.title || s.preview || s.session_id}
                  >
                    {s.title || s.preview || `会话 ${s.session_id?.slice(0, 8)}`}
                  </button>
                  {!sessionBulkMode && (
                  <button
                    type="button"
                    onClick={(e) => handleDeleteSession(s.session_id, e)}
                    className="p-1 rounded text-muted hover:bg-red-500/20 hover:text-red-400 shrink-0 opacity-60 hover:opacity-100"
                    title="删除会话（再次对话时不会带入该历史）"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                  )}
                </div>
              </li>
              ))}
              </ul>
            )}
              {sessionBulkMode && sessions.length > 0 && (
                <div className="shrink-0 border-t border-border p-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-muted">已选 {bulkSessionIds.length}</span>
                  <button
                    type="button"
                    onClick={() => setBulkSessionIds(sessions.map((x) => x.session_id))}
                    className="px-2 py-1 rounded border border-border text-muted hover:bg-white/5"
                  >
                    全选
                  </button>
                  <button
                    type="button"
                    onClick={() => setBulkSessionIds([])}
                    className="px-2 py-1 rounded border border-border text-muted hover:bg-white/5"
                  >
                    清空
                  </button>
                  <button
                    type="button"
                    disabled={bulkSessionIds.length === 0}
                    onClick={handleBulkDeleteSessions}
                    className="px-2 py-1 rounded border border-red-500/40 text-red-400 hover:bg-red-500/10 disabled:opacity-40"
                  >
                    批量删除
                  </button>
                </div>
              )}
              </div>
            </>
          )}
        </div>
        {/* 右侧对话区 */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {selectedSessionId && (
            <div className="shrink-0 px-4 py-2 border-b border-border flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setMessageBulkMode((v) => !v)
                  setBulkMessageIds([])
                }}
                className={`px-2.5 py-1 text-xs rounded border ${
                  messageBulkMode
                    ? 'border-accent text-accent bg-accent/10'
                    : 'border-border text-muted hover:bg-white/5'
                }`}
              >
                {messageBulkMode ? '取消选择消息' : '选择消息'}
              </button>
              {messageBulkMode && (
                <>
                  <span className="text-xs text-muted">已选 {bulkMessageIds.length}</span>
                  <button
                    type="button"
                    disabled={loading || bulkMessageIds.length === 0}
                    onClick={handleBulkDeleteMessages}
                    className="px-2.5 py-1 text-xs rounded border border-red-500/40 text-red-400 hover:bg-red-500/10 disabled:opacity-40"
                  >
                    删除选中消息
                  </button>
                </>
              )}
            </div>
          )}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {detailLoading && (
              <div className="text-center py-8 text-muted text-sm">加载会话…</div>
            )}
            {!detailLoading && messages.length === 0 && !streamingContent && (
              <div className="text-center py-12 text-muted text-sm">
                输入消息开始对话，可在下方选择模型。
              </div>
            )}
          {messages.map((msg, i) => {
            // 时间：2026-03-13；理由：与 GeneralChat / ArticleWriting 一致；方法：共用 stripAgentStatusPrefix
            const { status: agentStatus, content: assistantDisplay } =
              msg.role === 'assistant'
                ? stripAgentStatusPrefix(msg.content)
                : { status: null, content: msg.content }
            return (
            <div
              key={msg.message_id || i}
              className={`flex items-start gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {messageBulkMode && msg.message_id && (
                <input
                  type="checkbox"
                  className="mt-3 shrink-0 rounded border-border"
                  checked={bulkMessageIds.includes(msg.message_id)}
                  onChange={() => toggleBulkMessage(msg.message_id)}
                  title="选中以批量删除"
                />
              )}
              <div
                className={`max-w-[85%] rounded-lg px-4 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-accent/20 text-fg'
                    : 'bg-white/5 text-fg'
                }`}
              >
                {msg.role === 'user' ? (
                  <>
                    <p className="text-sm whitespace-pre-wrap">{extractUserQuestionForDisplay(msg.content)}</p>
                    <UserMessageActionButtons
                      content={msg.content}
                      messageId={msg.message_id}
                      onRegenerate={handleRegenerate}
                      onWriteToInput={setInput}
                      onDeleteMessage={handleDeleteMessage}
                      loading={loading}
                    />
                  </>
                ) : (
                  <>
                    {agentStatus && (
                      <p className="text-xs text-muted mb-1.5">{agentStatus}</p>
                    )}
                    <div className="prose prose-invert prose-sm max-w-none">
                      <MarkdownPreview markdown={assistantDisplay || ''} theme="dark" />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {i > 0 && messages[i - 1]?.role === 'user' && messages[i - 1]?.message_id && (
                        <button
                          type="button"
                          onClick={() => handleRegenerate(messages[i - 1].message_id)}
                          disabled={loading}
                          className="px-2 py-1 text-xs rounded border border-border text-muted hover:text-accent hover:bg-white/5 disabled:opacity-50"
                          title="要求 AI 重新回答此问题"
                        >
                          重新回答
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setInput(msg.content || '')}
                        className="px-2 py-1 text-xs rounded border border-border text-muted hover:text-accent hover:bg-white/5"
                        title="将回复内容写入输入框"
                      >
                        写回输入框
                      </button>
                      {msg.message_id && (
                        <button
                          type="button"
                          onClick={() => handleDeleteMessage(msg.message_id)}
                          className="px-2 py-1 text-xs rounded border border-border text-muted hover:text-accent hover:bg-white/5"
                          title="删除此消息"
                        >
                          删除
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
            )
          })}
          {streamingToolCalls.length > 0 && (
            <div className="flex justify-start w-full max-w-[85%]">
              <div className="space-y-1.5 w-full">
                {streamingToolCalls.map((tc, idx) => (
                  <div
                    key={idx}
                    className={`text-xs rounded-lg px-3 py-2 border ${
                      tc.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200' : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
                    }`}
                  >
                    <span className="font-medium">🔧 {tc.name}</span>
                    <span className="text-muted ml-1">{tc.success ? '→ 成功' : '→ 失败'}</span>
                    <div className="mt-1 text-muted truncate" title={
                      tc.success && tc.result != null
                        ? (typeof tc.result === 'string' ? tc.result : JSON.stringify(tc.result))
                        : tc.error || ''
                    }>
                      {tc.success && tc.result != null
                        ? (() => {
                            const r = typeof tc.result === 'string' ? tc.result : JSON.stringify(tc.result)
                            return r.length > 120 ? r.slice(0, 120) + '…' : r
                          })()
                        : tc.error || '（无结果）'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* 时间：2026-03-13；理由：与 GeneralChat 一致；方法：shouldAppendStreamingPlainText 解析 __CTX_META__ */}
          {contextSelectionMeta && (
            <div className="flex justify-start w-full">
              <ContextSelectionPanel meta={contextSelectionMeta} />
            </div>
          )}
          {streamingReasoning.trim() !== '' && (
            <div className="flex justify-start w-full">
              <div className="max-w-[85%] w-full">
                <StreamingReasoningPanel text={streamingReasoning} />
              </div>
            </div>
          )}
          {streamingContent && (() => {
            const { status: streamAgentStatus, content: streamMd } = stripAgentStatusPrefix(streamingContent)
            return (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-lg px-4 py-2.5 bg-white/5">
                  {streamAgentStatus && (
                    <p className="text-xs text-muted mb-1.5">{streamAgentStatus}</p>
                  )}
                  <div className="prose prose-invert prose-sm max-w-none">
                    <MarkdownPreview markdown={streamMd || ''} theme="dark" />
                  </div>
                </div>
              </div>
            )
          })()}
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
              <ReferenceBlocksPanel
                referenceBlocks={referenceBlocks}
                onAdd={handleAddReferenceBlockAndOpen}
                onUpdate={handleUpdateReferenceBlock}
                onRemove={handleRemoveReferenceBlock}
              />
            )}
          </div>
          <div className="shrink-0 flex items-center gap-2 px-4 py-2 border-t border-border bg-surface/50">
            <ModelSelector
              value={selectedModel}
              onChange={setSelectedModel}
              providers={providers}
              models={selectableModels}
              loading={modelsLoading}
            />
            {loading && (
              <button
                type="button"
                onClick={handleStop}
                className="text-xs px-2 py-1 rounded border border-red-500/50 text-red-400 hover:bg-red-500/10"
              >
                停止
              </button>
            )}
          </div>
          <ChatInput
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            placeholder="输入消息，Enter 换行，Ctrl+Enter 发送"
            disabled={loading || detailLoading}
            submitLabel="发送"
          />
        </div>
      </div>
    </div>
  )
}
