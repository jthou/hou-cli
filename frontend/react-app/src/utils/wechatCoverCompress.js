/**
 * 公众号封面上传前客户端预压缩（微信永久素材 ≤2MB，官方上限不变）。
 *
 * 时间：2026-03-13；理由：减少大原图上传失败与等待；方法与后端 cover_image_fit 双保险：Canvas JPEG 迭代 quality/长边。
 */

const TARGET_BYTES = Math.floor(1.9 * 1024 * 1024)

/**
 * @param {File|Blob} file
 * @returns {Promise<File|Blob>}
 */
export async function prepareWechatCoverFile(file) {
  if (!file || !(file instanceof Blob)) return file
  if (file.size <= TARGET_BYTES) return file
  if (typeof document === 'undefined' || typeof Image === 'undefined') return file

  const img = await loadImageFromFile(file)
  const w = img.naturalWidth || img.width
  const h = img.naturalHeight || img.height
  if (!w || !h) return file

  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) return file

  const maxDim = Math.max(w, h)
  const sideCaps = [2048, 1600, 1280, 1024, 900, 800, 640]
  const qualities = [0.88, 0.82, 0.76, 0.72, 0.68, 0.64, 0.6, 0.56, 0.52]

  for (const sideCap of sideCaps) {
    const scale = Math.min(1, sideCap / maxDim)
    const cw = Math.max(1, Math.round(w * scale))
    const ch = Math.max(1, Math.round(h * scale))
    for (const q of qualities) {
      canvas.width = cw
      canvas.height = ch
      ctx.drawImage(img, 0, 0, cw, ch)
      const blob = await canvasToJpegBlob(canvas, q)
      if (blob && blob.size > 0 && blob.size <= TARGET_BYTES) {
        const base = typeof file.name === 'string' ? file.name.replace(/\.[^.]+$/, '') : 'cover'
        return new File([blob], `${base || 'cover'}.jpg`, {
          type: 'image/jpeg',
          lastModified: Date.now(),
        })
      }
    }
  }

  return file
}

/**
 * @param {File|Blob} file
 * @returns {Promise<HTMLImageElement>}
 */
function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片加载失败'))
    }
    img.src = url
  })
}

/**
 * @param {HTMLCanvasElement} canvas
 * @param {number} quality 0..1
 * @returns {Promise<Blob|null>}
 */
function canvasToJpegBlob(canvas, quality) {
  return new Promise((resolve) => {
    canvas.toBlob((b) => resolve(b), 'image/jpeg', quality)
  })
}
