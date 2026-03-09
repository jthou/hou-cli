/**
 * 工作助手 - 通用对话入口，支持模型选择、会话持久化、参考块（与写作助手概念和操作一致）
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
  const [selectedModel, setSelectedModel] = useState('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [referencePanelOpen, setReferencePanelOpen] = useState(false)
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)
  const streamingContentRef = useRef('')
  const {
    referenceBlocks,
    handleAddReferenceBlock,
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
  }, [])

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

    const referenceContext = formatReferenceContext(referenceBlocks)
    const messageForModel = referenceContext ? `${referenceContext}【用户本次提问】\n${text}` : text

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setStreamingContent('')
    setStreamingToolCalls([])
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
      setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${err?.message || '请求失败'}` }])
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="工作助手" subtitle="通用对话入口，可指定具体模型" />
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
                <div
                  className={`flex-1 flex items-center gap-1 min-w-0 px-3 py-2.5 text-sm rounded-lg ${
                    selectedSessionId === s.session_id
                      ? 'bg-accent/20 text-accent'
                      : 'text-muted hover:bg-white/5 hover:text-fg'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedSessionId(s.session_id)}
                    className="flex-1 min-w-0 text-left truncate"
                    title={s.title || s.preview || s.session_id}
                  >
                    {s.title || s.preview || `会话 ${s.session_id?.slice(0, 8)}`}
                  </button>
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
                </div>
              </li>
              ))}
              </ul>
            )}
              </div>
            </>
          )}
        </div>
        {/* 右侧对话区 */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {detailLoading && (
              <div className="text-center py-8 text-muted text-sm">加载会话…</div>
            )}
            {!detailLoading && messages.length === 0 && !streamingContent && (
              <div className="text-center py-12 text-muted text-sm">
                输入消息开始对话，可在下方选择模型。
              </div>
            )}
          {messages.map((msg, i) => (
            <div
              key={msg.message_id || i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-4 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-accent/20 text-fg'
                    : 'bg-white/5 text-fg'
                }`}
              >
                {msg.role === 'user' ? (
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm whitespace-pre-wrap flex-1 min-w-0">{extractUserQuestionForDisplay(msg.content)}</p>
                    {msg.message_id && (
                      <button
                        type="button"
                        onClick={() => handleRegenerate(msg.message_id)}
                        disabled={loading}
                        className="shrink-0 px-2 py-1 text-xs rounded border border-border text-muted hover:text-accent hover:bg-white/5 disabled:opacity-50"
                        title="要求 AI 重新回答此问题"
                      >
                        重新回答
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <MarkdownPreview markdown={msg.content} theme="dark" />
                  </div>
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
