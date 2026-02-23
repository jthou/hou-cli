import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function VideoDownload() {
  const [url, setUrl] = useState('')
  const [quality, setQuality] = useState('best')
  const [downloadSubtitle, setDownloadSubtitle] = useState(false)
  const [extractAudioOnly, setExtractAudioOnly] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) {
      alert('请输入视频链接')
      return
    }
    setSubmitting(true)
    setResult(null)
    try {
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'video_download',
          metadata: {
            url: url.trim(),
            quality,
            download_subtitle: downloadSubtitle,
            extract_audio_only: extractAudioOnly,
          },
        }),
      })
      const data = await res.json()
      if (data.success) {
        setResult({ taskId: data.task_id, success: true })
        setUrl('')
      } else {
        throw new Error(data.detail || data.message || '创建任务失败')
      }
    } catch (err) {
      setResult({ error: err.message, success: false })
    }
    setSubmitting(false)
  }

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">视频下载</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        <p className="text-[#94a3b8] mb-6">
          支持 Bilibili、YouTube 等平台。输入视频链接后提交，下载任务将加入队列，可在
          <Link to="/" className="text-accent hover:underline ml-1">任务管理</Link>
          中查看进度。
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#94a3b8] mb-1">
              视频链接 <span className="text-red-400">*</span>
            </label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://www.bilibili.com/video/BVxxx 或 b23.tv/xxx"
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#94a3b8] mb-1">视频质量</label>
            <select
              value={quality}
              onChange={e => setQuality(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none"
            >
              <option value="best">最佳</option>
              <option value="1080p">1080p</option>
              <option value="720p">720p</option>
              <option value="480p">480p</option>
              <option value="360p">360p</option>
            </select>
          </div>

          <div className="flex flex-col gap-3">
            <label className="flex items-center gap-3 text-[#94a3b8] cursor-pointer">
              <input
                type="checkbox"
                checked={downloadSubtitle}
                onChange={e => setDownloadSubtitle(e.target.checked)}
                className="rounded"
              />
              下载字幕
            </label>
            <label className="flex items-center gap-3 text-[#94a3b8] cursor-pointer">
              <input
                type="checkbox"
                checked={extractAudioOnly}
                onChange={e => setExtractAudioOnly(e.target.checked)}
                className="rounded"
              />
              仅提取音频（MP3）
            </label>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 transition-colors"
          >
            {submitting ? '提交中...' : '提交下载任务'}
          </button>
        </form>

        {result && (
          <div className={`mt-6 p-4 rounded-lg ${result.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {result.success ? (
              <p>
                任务已创建：<Link to="/" className="underline">{result.taskId}</Link>
                ，请在任务管理中查看进度。
              </p>
            ) : (
              <p>失败：{result.error}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
