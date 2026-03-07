/**
 * IndexedDB 持久化写文章参考块（按会话存储）
 * 参考块可含大量正文，用 IndexedDB 避免 5MB 限制
 * 每个会话有独立的参考块
 */

const DB_NAME = 'hou-cli-article-writing'
const DB_VERSION = 2
const STORE_NAME = 'reference_blocks'
const KEY_REFERENCE_BLOCKS_LEGACY = 'reference_blocks'

function keyForSession(sessionId) {
  return sessionId ? `reference_blocks_${sessionId}` : null
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
 * 保存参考块到 IndexedDB（按会话）
 * @param {string} sessionId - 会话 ID
 * @param {Array<{id: string, title: string, content: string}>} blocks
 */
export async function saveReferenceBlocks(sessionId, blocks) {
  const key = keyForSession(sessionId)
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
 * 从 IndexedDB 读取参考块（按会话）
 * @param {string} sessionId - 会话 ID
 * @returns {Promise<Array<{id: string, title: string, content: string}>>}
 */
export async function loadReferenceBlocks(sessionId) {
  const key = keyForSession(sessionId)
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
        // 尝试迁移：先 IndexedDB 旧 key，再 sessionStorage
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
          await saveReferenceBlocks(sessionId, legacy)
          await deleteLegacyReferenceBlocks()
        }
        resolve(legacy.length > 0 ? legacy : [])
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
