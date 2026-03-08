/**
 * IndexedDB 持久化网页阅读截图
 * 截图 base64 体积大，不适合 localStorage，使用 IndexedDB 存储
 */

const DB_NAME = 'hou-cli-web-reader'
const DB_VERSION = 1
const STORE_NAME = 'screenshots'
const KEY_LAST = 'last'
const KEY_LAST_READ = 'last_read'
const KEY_LAST_READ_WEB = 'last_read_web'
const KEY_LAST_READ_WEREAD = 'last_read_weread'

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
 * 保存截图到 IndexedDB（仅保留最近一次）
 * @param {string} url - 页面 URL，用于恢复时校验
 * @param {string[]} screenshots - base64 图片数组
 */
export async function saveScreenshots(url, screenshots) {
  if (!screenshots?.length) return
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.put({ key: KEY_LAST, url: url || '', screenshots, updatedAt: Date.now() })
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (e) {
    console.warn('[WebReader] IndexedDB save failed:', e)
  }
}

/**
 * 清除截图（当本次阅读无截图时调用，避免恢复错误会话）
 */
export async function clearScreenshots() {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.delete(KEY_LAST)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (e) {
    console.warn('[WebReader] IndexedDB clear failed:', e)
  }
}

/**
 * 从 IndexedDB 读取上次保存的截图
 * @param {string} [expectedUrl] - 期望的 URL，若提供则校验匹配
 * @returns {Promise<string[]|null>}
 */
export async function loadScreenshots(expectedUrl) {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.get(KEY_LAST)
      req.onsuccess = () => {
        const record = req.result
        if (!record?.screenshots?.length) {
          resolve(null)
          return
        }
        if (expectedUrl && record.url !== expectedUrl) {
          resolve(null)
          return
        }
        resolve(record.screenshots)
      }
      req.onerror = () => reject(req.error)
    })
  } catch (e) {
    console.warn('[WebReader] IndexedDB load failed:', e)
    return null
  }
}

/**
 * 异步保存上次阅读内容（文本、URL 等），避免 localStorage 同步阻塞主线程
 * @param {{ url?: string, urlInput?: string, title?: string, markdown?: string, content?: string, html?: string, viewMode?: string }} state
 */
export async function saveLastRead(state) {
  if (!state?.markdown && !state?.content) return
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.put({ key: KEY_LAST_READ, ...state, updatedAt: Date.now() })
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (e) {
    console.warn('[WebReader] IndexedDB saveLastRead failed:', e)
  }
}

/**
 * 异步读取上次阅读内容
 * @returns {Promise<{ url?: string, urlInput?: string, title?: string, markdown?: string, content?: string, html?: string, viewMode?: string } | null>}
 */
export async function loadLastRead() {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.get(KEY_LAST_READ)
      req.onsuccess = () => {
        const record = req.result
        if (!record?.markdown && !record?.content) {
          resolve(null)
          return
        }
        const { key, updatedAt, ...rest } = record || {}
        resolve(rest)
      }
      req.onerror = () => reject(req.error)
    })
  } catch (e) {
    console.warn('[WebReader] IndexedDB loadLastRead failed:', e)
    return null
  }
}

/**
 * 按上下文保存/读取上次阅读（web 与 weread 分离）
 * weread 支持仅保存 url+title+urlInput（有截图但未识别时），便于恢复
 * @param {'web'|'weread'} context
 */
export async function saveLastReadForContext(context, state) {
  const hasContent = state?.markdown || state?.content
  const hasWereadScreenshots = context === 'weread' && state?.url
  if (!hasContent && !hasWereadScreenshots) return
  const key = context === 'weread' ? KEY_LAST_READ_WEREAD : KEY_LAST_READ_WEB
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.put({ key, ...state, updatedAt: Date.now() })
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (e) {
    console.warn('[WebReader] IndexedDB saveLastReadForContext failed:', e)
  }
}

export async function loadLastReadForContext(context) {
  const key = context === 'weread' ? KEY_LAST_READ_WEREAD : KEY_LAST_READ_WEB
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const req = store.get(key)
      req.onsuccess = () => {
        const record = req.result
        const hasContent = record?.markdown || record?.content
        const hasWereadUrl = context === 'weread' && record?.url
        if (!hasContent && !hasWereadUrl) {
          resolve(null)
          return
        }
        const { key: _k, updatedAt, ...rest } = record || {}
        resolve(rest)
      }
      req.onerror = () => reject(req.error)
    })
  } catch (e) {
    console.warn('[WebReader] IndexedDB loadLastReadForContext failed:', e)
    return null
  }
}
