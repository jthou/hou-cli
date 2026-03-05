/**
 * IndexedDB 持久化写文章参考块
 * 参考块可含大量正文，用 IndexedDB 避免 5MB 限制，并支持跨会话保留
 */

const DB_NAME = 'hou-cli-article-writing'
const DB_VERSION = 1
const STORE_NAME = 'reference_blocks'
const KEY_REFERENCE_BLOCKS = 'reference_blocks'

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
 * 保存参考块到 IndexedDB
 * @param {Array<{id: string, title: string, content: string}>} blocks
 */
export async function saveReferenceBlocks(blocks) {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.put({
        key: KEY_REFERENCE_BLOCKS,
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
 * 从 IndexedDB 读取参考块
 * @returns {Promise<Array<{id: string, title: string, content: string}>>}
 */
export async function loadReferenceBlocks() {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.get(KEY_REFERENCE_BLOCKS)
      req.onsuccess = () => {
        const record = req.result
        const blocks = record?.blocks
        resolve(Array.isArray(blocks) ? blocks : [])
      }
      req.onerror = () => reject(req.error)
    })
  } catch (e) {
    console.warn('[ArticleWriting] IndexedDB load failed:', e)
    return []
  }
}
