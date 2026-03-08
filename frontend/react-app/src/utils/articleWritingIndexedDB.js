/**
 * IndexedDB 持久化参考块（按会话、按类型存储）
 * 参考块可含大量正文，用 IndexedDB 避免 5MB 限制
 * 写作助手与工作助手的参考块按 contextType 隔离：article_writing_${sessionId} / work_assistant_${sessionId}
 */

const DB_NAME = 'hou-cli-article-writing'
const DB_VERSION = 2
const STORE_NAME = 'reference_blocks'
const KEY_REFERENCE_BLOCKS_LEGACY = 'reference_blocks'

/** 旧版 key（无类型前缀），用于迁移 */
function legacyKeyForSession(sessionId) {
  return sessionId ? `reference_blocks_${sessionId}` : null
}

/** 新版 key（含 contextType 前缀） */
function keyForSession(sessionId, contextType = 'article_writing') {
  if (!sessionId) return null
  return `${contextType}_${sessionId}`
}

let dbPromise = null

function openDB() {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onerror = () => reject(req.error)
    req.onsuccess = () => resolve(req.result)
    req.onupgradeneeded = (e) => {
      const db = e.target.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'key' })
      }
    }
  })
  return dbPromise
}

/**
 * 保存参考块到 IndexedDB（按会话、按类型）
 * @param {string} sessionId - 会话 ID
 * @param {Array<{id: string, title: string, content: string}>} blocks
 * @param {string} [contextType='article_writing'] - 上下文类型：article_writing | work_assistant
 */
export async function saveReferenceBlocks(sessionId, blocks, contextType = 'article_writing') {
  const key = keyForSession(sessionId, contextType)
  if (!key) return
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.put({
        key,
        blocks: Array.isArray(blocks) ? blocks : [],
        updatedAt: Date.now(),
      })
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (e) {
    console.warn('[ArticleWriting] IndexedDB save failed:', e)
  }
}

/**
 * 从 IndexedDB 读取参考块（按会话、按类型）
 * @param {string} sessionId - 会话 ID
 * @param {string} [contextType='article_writing'] - 上下文类型：article_writing | work_assistant
 * @returns {Promise<Array<{id: string, title: string, content: string}>>}
 */
export async function loadReferenceBlocks(sessionId, contextType = 'article_writing') {
  const key = keyForSession(sessionId, contextType)
  if (!key) return []
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.get(key)
      req.onsuccess = async () => {
        const record = req.result
        let blocks = record?.blocks
        if (Array.isArray(blocks) && blocks.length > 0) {
          resolve(blocks)
          return
        }
        // 迁移：尝试旧版 key（reference_blocks_${sessionId}），若有则迁移到新版
        const legacyKey = legacyKeyForSession(sessionId)
        if (legacyKey) {
          const legacyReq = store.get(legacyKey)
          legacyReq.onsuccess = async () => {
            const legacyRecord = legacyReq.result
            const legacyBlocks = legacyRecord?.blocks
            if (Array.isArray(legacyBlocks) && legacyBlocks.length > 0) {
              await saveReferenceBlocks(sessionId, legacyBlocks, contextType)
              await deleteKey(legacyKey)
              resolve(legacyBlocks)
              return
            }
            // 再尝试全局旧 key 与 sessionStorage（仅 article_writing）
            if (contextType === 'article_writing') {
              let legacy = await loadLegacyReferenceBlocks()
              if (legacy.length === 0) {
                try {
                  const raw = typeof sessionStorage !== 'undefined' && sessionStorage.getItem('article_writing_reference_blocks')
                  const parsed = raw ? JSON.parse(raw) : []
                  legacy = Array.isArray(parsed) ? parsed : []
                  if (legacy.length > 0) {
                    sessionStorage.removeItem('article_writing_reference_blocks')
                  }
                } catch (_) {}
              }
              if (legacy.length > 0) {
                await saveReferenceBlocks(sessionId, legacy, contextType)
                await deleteLegacyReferenceBlocks()
              }
              resolve(legacy.length > 0 ? legacy : [])
            } else {
              resolve([])
            }
          }
          legacyReq.onerror = () => resolve([])
          return
        }
        resolve([])
      }
      req.onerror = () => reject(req.error)
    })
  } catch (e) {
    console.warn('[ArticleWriting] IndexedDB load failed:', e)
    return []
  }
}

/** 读取旧版全局参考块（迁移用） */
async function loadLegacyReferenceBlocks() {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.get(KEY_REFERENCE_BLOCKS_LEGACY)
      req.onsuccess = () => {
        const record = req.result
        const blocks = record?.blocks
        resolve(Array.isArray(blocks) ? blocks : [])
      }
      req.onerror = () => reject(req.error)
    })
  } catch {
    return []
  }
}

/** 删除指定 key 的记录（迁移后清理旧版按会话 key） */
async function deleteKey(key) {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.delete(key)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (_) {}
}

/** 删除旧版全局参考块（迁移后清理） */
async function deleteLegacyReferenceBlocks() {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.delete(KEY_REFERENCE_BLOCKS_LEGACY)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (_) {}
}
