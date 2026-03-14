/**
 * 参考块状态与持久化 hook，供 ArticleWriting、WorkAssistant 复用
 * 按会话加载/保存参考块到 IndexedDB
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { saveReferenceBlocks, loadReferenceBlocks } from '../utils/articleWritingIndexedDB'
import { generateReferenceBlockId } from '../utils/referenceUtils'
import { runWhenIdle } from '../utils/runWhenIdle'

export function useReferenceBlocks(selectedSessionId, referencePanelOpen, contextType = 'article_writing') {
  const [referenceBlocks, setReferenceBlocks] = useState([])
  const referenceBlocksRef = useRef(referenceBlocks)
  referenceBlocksRef.current = referenceBlocks
  const referenceBlocksLoadedRef = useRef(false)
  const prevSelectedSessionIdRef = useRef(null)
  const prevReferencePanelOpenRef = useRef(referencePanelOpen)

  const handleAddReferenceBlock = useCallback(() => {
    setReferenceBlocks((prev) => {
      const next = [...prev, { id: generateReferenceBlockId(), title: '', content: '' }]
      if (selectedSessionId) {
        runWhenIdle(() => saveReferenceBlocks(selectedSessionId, next, contextType).catch(() => {}))
      }
      return next
    })
  }, [selectedSessionId, contextType])

  const handleAddReferenceBlockWithContent = useCallback((content) => {
    const text = (content || '').trim()
    if (!text) return
    setReferenceBlocks((prev) => {
      const next = [...prev, { id: generateReferenceBlockId(), title: '', content: text }]
      if (selectedSessionId) {
        runWhenIdle(() => saveReferenceBlocks(selectedSessionId, next, contextType).catch(() => {}))
      }
      return next
    })
  }, [selectedSessionId, contextType])

  const handleUpdateReferenceBlock = useCallback((id, field, value) => {
    setReferenceBlocks((prev) =>
      prev.map((b) => (b.id === id ? { ...b, [field]: value } : b))
    )
  }, [])

  const handleRemoveReferenceBlock = useCallback((id) => {
    setReferenceBlocks((prev) => {
      const next = prev.filter((b) => b.id !== id)
      if (selectedSessionId) {
        runWhenIdle(() => saveReferenceBlocks(selectedSessionId, next, contextType).catch(() => {}))
      }
      return next
    })
  }, [selectedSessionId, contextType])

  const reloadBlocks = useCallback((sessionIdOverride) => {
    const sid = sessionIdOverride ?? selectedSessionId
    if (!sid) return
    loadReferenceBlocks(sid, contextType).then((blocks) => {
      setReferenceBlocks(blocks)
      referenceBlocksLoadedRef.current = true
    })
  }, [selectedSessionId, contextType])

  /** 参考块按会话：切换会话时保存旧会话、加载新会话 */
  useEffect(() => {
    if (!selectedSessionId) {
      setReferenceBlocks([])
      referenceBlocksLoadedRef.current = true
      prevSelectedSessionIdRef.current = null
      return
    }
    let cancelled = false
    const prevSessionId = prevSelectedSessionIdRef.current
    prevSelectedSessionIdRef.current = selectedSessionId

    if (prevSessionId && prevSessionId !== selectedSessionId && referenceBlocksRef.current.length > 0) {
      runWhenIdle(() => saveReferenceBlocks(prevSessionId, referenceBlocksRef.current, contextType).catch(() => {}))
    }

    loadReferenceBlocks(selectedSessionId, contextType).then((blocks) => {
      if (cancelled) return
      setReferenceBlocks(blocks)
      referenceBlocksLoadedRef.current = true
    })
    return () => { cancelled = true }
  }, [selectedSessionId, contextType])

  /** 参考块持久化：面板关闭时写入 */
  useEffect(() => {
    if (!referenceBlocksLoadedRef.current || !selectedSessionId) return
    if (prevReferencePanelOpenRef.current && !referencePanelOpen) {
      runWhenIdle(() => saveReferenceBlocks(selectedSessionId, referenceBlocks, contextType).catch(() => {}))
    }
    prevReferencePanelOpenRef.current = referencePanelOpen
  }, [referencePanelOpen, referenceBlocks, selectedSessionId, contextType])

  /** 内容变更时防抖写入 */
  useEffect(() => {
    if (!referenceBlocksLoadedRef.current || !selectedSessionId) return
    const id = setTimeout(() => {
      saveReferenceBlocks(selectedSessionId, referenceBlocks, contextType).catch(() => {})
    }, 800)
    return () => clearTimeout(id)
  }, [referenceBlocks, selectedSessionId, contextType])

  /** 组件卸载时保存当前会话参考块 */
  useEffect(() => {
    return () => {
      const blocks = referenceBlocksRef.current
      if (referenceBlocksLoadedRef.current && selectedSessionId && blocks?.length > 0) {
        runWhenIdle(() => saveReferenceBlocks(selectedSessionId, blocks, contextType).catch(() => {}), { timeout: 0 })
      }
    }
  }, [selectedSessionId, contextType])

  return {
    referenceBlocks,
    handleAddReferenceBlock,
    handleAddReferenceBlockWithContent,
    handleUpdateReferenceBlock,
    handleRemoveReferenceBlock,
    reloadBlocks,
  }
}
