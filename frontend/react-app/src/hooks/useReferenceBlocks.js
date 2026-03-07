/**
 * 参考块状态与持久化 hook，供 ArticleWriting、WorkAssistant 复用
 * 按会话加载/保存参考块到 IndexedDB
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { saveReferenceBlocks, loadReferenceBlocks } from '../utils/articleWritingIndexedDB'
import { generateReferenceBlockId } from '../utils/referenceUtils'
import { runWhenIdle } from '../utils/runWhenIdle'

export function useReferenceBlocks(selectedSessionId, referencePanelOpen) {
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
        runWhenIdle(() => saveReferenceBlocks(selectedSessionId, next).catch(() => {}))
      }
      return next
    })
  }, [selectedSessionId])

  const handleUpdateReferenceBlock = useCallback((id, field, value) => {
    setReferenceBlocks((prev) =>
      prev.map((b) => (b.id === id ? { ...b, [field]: value } : b))
    )
  }, [])

  const handleRemoveReferenceBlock = useCallback((id) => {
    setReferenceBlocks((prev) => {
      const next = prev.filter((b) => b.id !== id)
      if (selectedSessionId) {
        runWhenIdle(() => saveReferenceBlocks(selectedSessionId, next).catch(() => {}))
      }
      return next
    })
  }, [selectedSessionId])

  const reloadBlocks = useCallback((sessionIdOverride) => {
    const sid = sessionIdOverride ?? selectedSessionId
    if (!sid) return
    loadReferenceBlocks(sid).then((blocks) => {
      setReferenceBlocks(blocks)
      referenceBlocksLoadedRef.current = true
    })
  }, [selectedSessionId])

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
      runWhenIdle(() => saveReferenceBlocks(prevSessionId, referenceBlocksRef.current).catch(() => {}))
    }

    loadReferenceBlocks(selectedSessionId).then((blocks) => {
      if (cancelled) return
      setReferenceBlocks(blocks)
      referenceBlocksLoadedRef.current = true
    })
    return () => { cancelled = true }
  }, [selectedSessionId])

  /** 参考块持久化：面板关闭时写入 */
  useEffect(() => {
    if (!referenceBlocksLoadedRef.current || !selectedSessionId) return
    if (prevReferencePanelOpenRef.current && !referencePanelOpen) {
      runWhenIdle(() => saveReferenceBlocks(selectedSessionId, referenceBlocks).catch(() => {}))
    }
    prevReferencePanelOpenRef.current = referencePanelOpen
  }, [referencePanelOpen, referenceBlocks, selectedSessionId])

  /** 内容变更时防抖写入 */
  useEffect(() => {
    if (!referenceBlocksLoadedRef.current || !selectedSessionId) return
    const id = setTimeout(() => {
      saveReferenceBlocks(selectedSessionId, referenceBlocks).catch(() => {})
    }, 800)
    return () => clearTimeout(id)
  }, [referenceBlocks, selectedSessionId])

  /** 组件卸载时保存当前会话参考块 */
  useEffect(() => {
    return () => {
      const blocks = referenceBlocksRef.current
      if (referenceBlocksLoadedRef.current && selectedSessionId && blocks?.length > 0) {
        runWhenIdle(() => saveReferenceBlocks(selectedSessionId, blocks).catch(() => {}), { timeout: 0 })
      }
    }
  }, [selectedSessionId])

  return {
    referenceBlocks,
    handleAddReferenceBlock,
    handleUpdateReferenceBlock,
    handleRemoveReferenceBlock,
    reloadBlocks,
  }
}
