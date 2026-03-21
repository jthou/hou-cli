/**
 * 通用对话 - 可调用全部工具，支持会话持久化、参考块（与工作助手、写作助手设计一致）
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import ChatInput from '../components/ChatInput'
import MarkdownPreview from '../components/MarkdownPreview'
import { useToast } from '../components/ToastModal'
import { useSelectableModels } from '../hooks/useSelectableModels'
import ModelSelector from '../components/ModelSelector'
import { formatReferenceContext, extractUserQuestionForDisplay } from '../utils/referenceUtils'
import { useReferenceBlocks } from '../hooks/useReferenceBlocks'
import ReferenceBlocksPanel from '../components/ReferenceBlocksPanel'
import UserMessageActionButtons from '../components/UserMessageActionButtons'
import { useDeleteSessionMessage } from '../hooks/useDeleteSessionMessage'
import { useBatchDeleteSessions } from '../hooks/useBatchDeleteSessions'
import { useBatchDeleteMessages } from '../hooks/useBatchDeleteMessages'

const DEFAULT_SESSION_TYPE = 'general_chat'
const DEFAULT_STORAGE_KEY = 'general_chat_selected_session'

export default function GeneralChat({
  title = '通用对话',
  subtitle = '可调用全部工具（搜索、浏览器、下载等），支持会话与参考信息',
  sessionType = DEFAULT_SESSION_TYPE,
  storageKey = DEFAULT_STORAGE_KEY,
  defaultPersona = '',
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const { providers, models: selectableModels, defaultModel, loading: modelsLoading } = useSelectableModels()
  const [sessions, setSessions] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [selectedSessionId, setSelectedSessionId] = useState(() => {
    try {
      return sessionStorage.getItem(storageKey) || null
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
  const [selectedModel, setSelectedModel] = useState('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [referencePanelOpen, setReferencePanelOpen] = useState(false)
  const [settingsPanelOpen, setSettingsPanelOpen] = useState(false)
  const [sessionPersona, setSessionPersona] = useState('')
  const [sessionEnabledTools, setSessionEnabledTools] = useState([])
  const [availableTools, setAvailableTools] = useState([])
  const [settingsSaving, setSettingsSaving] = useState(false)
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
    handleUpdateReferenceBlock,
    handleRemoveReferenceBlock,
    reloadBlocks,
  } = useReferenceBlocks(selectedSessionId, referencePanelOpen, sessionType)

  const handleAddReferenceBlockAndOpen = () => {
    setReferencePanelOpen(true)
    handleAddReferenceBlock()
  }

  const handleSaveSettings = async () => {
    if (!selectedSessionId || settingsSaving) return
    setSettingsSaving(true)
    try {
      const meta = {
        persona: (sessionPersona || '').trim(),
        enabled_tools: sessionEnabledTools,
      }
      const r = await fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metadata: meta }),
      })
      const d = await r.json()
      if (d.success) {
        toast.success('设置已保存')
      } else {
        toast.error(d.error || '保存失败')
      }
    } catch (err) {
      toast.error(err?.message || '保存失败')
    } finally {
      setSettingsSaving(false)
    }
  }

  const toggleTool = (name) => {
    if (availableTools.length === 0) return
    setSessionEnabledTools((prev) => {
      const allNames = availableTools.map((t) => t.name)
      if (prev.length === 0) {
        // 当前为「全部」：取消勾选 = 排除该项
        return allNames.filter((n) => n !== name)
      }
      const has = prev.includes(name)
      if (has) {
        const next = prev.filter((n) => n !== name)
        return next.length === 0 ? [] : next
      }
      const next = [...prev, name]
      return next.length === allNames.length ? [] : next
    })
  }

  const selectAllTools = () => setSessionEnabledTools(availableTools.map((t) => t.name))
  const clearTools = () => setSessionEnabledTools([])

  useEffect(() => {
    if (defaultModel && !selectedModel) setSelectedModel(defaultModel)
    else if (!selectedModel && selectableModels?.length) setSelectedModel(selectableModels[0]?.value || '')
  }, [defaultModel, selectedModel, selectableModels])

  const loadSessions = useCallback(() => {
    setSessionsLoading(true)
        fetch(`/api/sessions/list?type=${encodeURIComponent(sessionType)}&limit=50`)
      .then((r) => r.json())
      .then((d) => {
        if (d.sessions) setSessions(d.sessions)
        if (d.error) toast?.error?.(`加载会话列表失败：${d.error}`)
      })
      .catch((e) => toast?.error?.(e?.message || '加载会话列表失败'))
      .finally(() => setSessionsLoading(false))
  }, [sessionType, toast])

  const executeBatchDeleteSessions = useBatchDeleteSessions({
    sessionType,
    loadSessions,
    selectedSessionId,
    setSelectedSessionId,
    setMessages,
    storageKey,
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
          sessionStorage.setItem(storageKey, first)
        } catch (_) {}
      }
    }
  }, [sessions, selectedSessionId, storageKey])

  useEffect(() => {
    try {
      if (selectedSessionId) {
        sessionStorage.setItem(storageKey, selectedSessionId)
      } else {
        sessionStorage.removeItem(storageKey)
      }
    } catch (_) {}
  }, [selectedSessionId, storageKey])

  useEffect(() => {
    if (!selectedSessionId) {
      setMessages([])
      setDetailLoading(false)
      setSessionPersona('')
      setSessionEnabledTools([])
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
        if (d.success && d.session?.metadata) {
          const meta = d.session.metadata
          setSessionPersona(meta.persona || '')
          setSessionEnabledTools(Array.isArray(meta.enabled_tools) ? meta.enabled_tools : [])
        } else {
          setSessionPersona('')
          setSessionEnabledTools([])
        }
      })
      .catch((e) => toast?.error?.(e?.message || '加载历史失败'))
      .finally(() => setDetailLoading(false))
  }, [selectedSessionId])

  useEffect(() => {
    setBulkMessageIds([])
    setMessageBulkMode(false)
  }, [selectedSessionId])

  useEffect(() => {
    if (settingsPanelOpen && availableTools.length === 0) {
      fetch('/api/tools/list?agent=general_chat')
        .then((r) => r.json())
        .then((d) => {
          if (d.success && Array.isArray(d.tools)) setAvailableTools(d.tools)
        })
        .catch(() => {})
    }
  }, [settingsPanelOpen, availableTools.length])

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
      sessionStorage.setItem(storageKey, focusId)
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
            sessionStorage.removeItem(storageKey)
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
    const meta = { type: sessionType }
    if (defaultPersona) meta.persona = defaultPersona
    fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata: meta }),
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
    setStreamingToolCalls([])
    const ac = new AbortController()
    abortControllerRef.current = ac
    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: '',
          session_id: selectedSessionId,
          context_type: 'general_chat',
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
                if (!raw.startsWith('__DEBUG__:') && !raw.startsWith('__STATUS__:') && !raw.startsWith('__TOOL__:')) {
                  fullContent += raw
                  streamingContentRef.current = fullContent
                  setStreamingContent(fullContent)
                }
              } else if (obj.status === 'done') {
                fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`)
                  .then((r) => r.json())
                  .then((d) => {
                    if (d.success && Array.isArray(d.messages)) {
                      setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id })))
                    }
                  })
                  .catch(() => {})
                setStreamingContent('')
                streamingContentRef.current = ''
              } else if (obj.status === 'error') {
                setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
                setStreamingContent('')
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
            if (obj.status === 'done') {
              fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`)
                .then((r) => r.json())
                .then((d) => {
                  if (d.success && Array.isArray(d.messages)) {
                    setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id })))
                  }
                })
                .catch(() => {})
            }
          }
        } catch (_) {}
      }
    } catch (err) {
      if (err?.name === 'AbortError') return
      const isNetworkError = err?.message === 'Failed to fetch' || err?.name === 'TypeError'
      const msg = isNetworkError ? '无法连接后端。请确认后端已启动（默认端口 8081）。' : (err?.message || '请求失败')
      setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${msg}` }])
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleSubmit = async (e) => {
    e?.preventDefault?.()
    const text = (input || '').trim()
    if (!text) return

    const referenceContext = formatReferenceContext(referenceBlocks)
    const messageForModel = referenceContext ? `${referenceContext}【用户本次提问】\n${text}` : text

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setStreamingContent('')
    setStreamingToolCalls([])
    setLoading(true) // 先设 loading，再创建会话，避免 useEffect 覆盖消息

    let sessionId = selectedSessionId
    if (!sessionId) {
      const meta = { type: sessionType }
      if (defaultPersona) meta.persona = defaultPersona
      const createRes = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metadata: meta }),
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
          context_type: 'general_chat',
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
                if (raw.startsWith('__DEBUG__:') || raw.startsWith('__STATUS__:')) {
                  // 忽略
                } else if (raw.startsWith('__TOOL__:')) {
                  try {
                    const toolData = JSON.parse(raw.slice(9).trim())
                    if (toolData?.name) {
                      setStreamingToolCalls((prev) => [...prev, {
                        name: toolData.name,
                        args: toolData.args || {},
                        success: toolData.success,
                        result: toolData.result,
                        error: toolData.error,
                      }])
                    }
                  } catch (_) {}
                } else {
                  fullContent += raw
                  streamingContentRef.current = fullContent
                  setStreamingContent(fullContent)
                }
              } else if (obj.status === 'done') {
                const finalContent = fullContent.trim() || '（助手未返回内容）'
                setStreamingContent('')
                setStreamingToolCalls([])
                streamingContentRef.current = ''
                // 实验：先乐观追加助手回复，避免 fetch 返回时后端尚未持久化导致内容被覆盖而一闪而逝
                setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
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
                // 2025-03-20：后端可能尚未持久化，若 API 返回条数少于当前则延迟重试一次，确保拿到带 message_id 的完整列表（否则最新消息无法删除）
                const doFetch = (isRetry = false) => {
                  fetch(`/api/sessions/${encodeURIComponent(sessionId)}`)
                    .then((r) => r.json())
                    .then((d) => {
                      if (!d.success || !Array.isArray(d.messages)) return
                      const mapped = d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id }))
                      setMessages((prev) => {
                        if (mapped.length >= prev.length || isRetry) return mapped
                        if (!isRetry) setTimeout(() => doFetch(true), 400)
                        return prev
                      })
                    })
                    .catch(() => {})
                }
                doFetch()
                fullContent = ''
              } else if (obj.status === 'error') {
                setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
                setStreamingContent('')
                setStreamingToolCalls([])
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
              if (raw.startsWith('__TOOL__:')) {
                try {
                  const toolData = JSON.parse(raw.slice(9).trim())
                  if (toolData?.name) {
                    setStreamingToolCalls((prev) => [...prev, {
                      name: toolData.name,
                      args: toolData.args || {},
                      success: toolData.success,
                      result: toolData.result,
                      error: toolData.error,
                    }])
                  }
                } catch (_) {}
              } else if (!raw.startsWith('__DEBUG__:') && !raw.startsWith('__STATUS__:')) {
                fullContent += raw
                streamingContentRef.current = fullContent
                setStreamingContent(fullContent)
              }
            } else if (obj.status === 'done') {
              const finalContent = fullContent.trim() || '（助手未返回内容）'
              setStreamingToolCalls([])
              setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
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
                    setMessages((prev) => {
                      const apiCount = d.messages.length
                      if (apiCount >= prev.length) return d.messages.map((m) => ({ role: m.role, content: m.content, message_id: m.message_id }))
                      return prev
                    })
                  }
                })
                .catch(() => {})
              fullContent = ''
            } else if (obj.status === 'error') {
              setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
              setStreamingToolCalls([])
              fullContent = ''
            }
          }
          setStreamingContent('')
          streamingContentRef.current = ''
        } catch (_) {}
      }
    } catch (err) {
      if (err?.name === 'AbortError') return
      const isNetworkError = err?.message === 'Failed to fetch' || err?.name === 'TypeError'
      const msg = isNetworkError ? '无法连接后端。请确认后端已启动（默认端口 8081）。' : (err?.message || '请求失败')
      setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${msg}` }])
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader title={title} subtitle={subtitle} />
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
                输入消息开始对话，可调用搜索、浏览器、下载等工具。可在下方选择模型。
              </div>
            )}
          {messages.map((msg, i) => (
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
                      onWriteToInput={setInput}
                      onDeleteMessage={handleDeleteMessage}
                    />
                  </>
                ) : (
                  <>
                    <div className="prose prose-invert prose-sm max-w-none">
                      <MarkdownPreview markdown={msg.content} theme="dark" />
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
          ))}
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
          {streamingContent && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-lg px-4 py-2.5 bg-white/5">
                <div className="prose prose-invert prose-sm max-w-none">
                  <MarkdownPreview markdown={streamingContent} theme="dark" />
                </div>
              </div>
            </div>
          )}
            <div ref={messagesEndRef} />
          </div>
          <div className="border-t border-border px-4 py-2">
            <div className="flex items-center gap-4">
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
              {selectedSessionId && (
                <button
                  type="button"
                  onClick={() => setSettingsPanelOpen((v) => !v)}
                  className="text-xs text-muted hover:text-fg flex items-center gap-1"
                >
                  <span>{settingsPanelOpen ? '收起会话设置' : '会话设置'}</span>
                  {(sessionPersona || sessionEnabledTools.length > 0) && (
                    <span className="inline-flex items-center justify-center min-w-[1.25rem] px-1 rounded-full bg-white/10 text-[11px] text-muted">
                      {(sessionPersona ? 1 : 0) + (sessionEnabledTools.length > 0 ? 1 : 0)}
                    </span>
                  )}
                </button>
              )}
            </div>
            {referencePanelOpen && (
              <ReferenceBlocksPanel
                referenceBlocks={referenceBlocks}
                onAdd={handleAddReferenceBlockAndOpen}
                onUpdate={handleUpdateReferenceBlock}
                onRemove={handleRemoveReferenceBlock}
              />
            )}
            {settingsPanelOpen && selectedSessionId && (
              <div className="mt-3 p-3 rounded-lg border border-border bg-surface/50 space-y-3">
                <div>
                  <label className="block text-xs text-muted mb-1">限定身份（可选）</label>
                  <textarea
                    value={sessionPersona}
                    onChange={(e) => setSessionPersona(e.target.value)}
                    placeholder="例如：你是一位资深 Python 工程师，擅长代码审查与重构。"
                    className="w-full px-3 py-2 text-sm rounded border border-border bg-bg text-fg placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                    rows={2}
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs text-muted">工具选择（空=全部）</label>
                    <div className="flex gap-1">
                      <button type="button" onClick={selectAllTools} className="text-[11px] text-muted hover:text-fg">全选</button>
                      <span className="text-muted">|</span>
                      <button type="button" onClick={clearTools} className="text-[11px] text-muted hover:text-fg">清空</button>
                    </div>
                  </div>
                  <div className="max-h-32 overflow-y-auto flex flex-wrap gap-2 p-2 rounded border border-border bg-bg">
                    {availableTools.length === 0 && <span className="text-xs text-muted">加载中…</span>}
                    {availableTools.map((t) => (
                      <label key={t.name} className="flex items-center gap-1.5 text-xs cursor-pointer">
                        <input
                          type="checkbox"
                          checked={sessionEnabledTools.length === 0 || sessionEnabledTools.includes(t.name)}
                          onChange={() => toggleTool(t.name)}
                        />
                        <span title={t.description}>{t.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleSaveSettings}
                  disabled={settingsSaving}
                  className="px-3 py-1.5 text-xs rounded bg-accent hover:opacity-90 text-white disabled:opacity-50"
                >
                  {settingsSaving ? '保存中…' : '保存设置'}
                </button>
              </div>
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
