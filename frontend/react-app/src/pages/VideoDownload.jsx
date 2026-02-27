import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useToast } from '../components/ToastModal'

export default function VideoDownload() {
  const toast = useToast()
  const [url, setUrl] = useState('')
  const [quality, setQuality] = useState('best')
  const [outputDir, setOutputDir] = useState('')
  const [downloadSubtitle, setDownloadSubtitle] = useState(false)
  const [subtitleLanguages, setSubtitleLanguages] = useState('')
  const [downloadSubtitleOnly, setDownloadSubtitleOnly] = useState(false)
  const [extractAudioOnly, setExtractAudioOnly] = useState(false)
  const [audioFormat, setAudioFormat] = useState('mp3')
  const [audioQuality, setAudioQuality] = useState('192k')
  const [downloadThumbnail, setDownloadThumbnail] = useState(false)
  const [downloadDanmaku, setDownloadDanmaku] = useState(false)
  const [preferredTool, setPreferredTool] = useState('auto')
  const [cookiesFile, setCookiesFile] = useState('')
  const [cookiesFromBrowser, setCookiesFromBrowser] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) {
      toast.warning('请输入视频链接')
      return
    }
    setSubmitting(true)
    setResult(null)
    const metadata = {
      url: url.trim(),
      quality,
      download_subtitle: downloadSubtitle,
      extract_audio_only: extractAudioOnly,
      download_thumbnail: downloadThumbnail,
      download_danmaku: downloadDanmaku,
      download_subtitle_only: downloadSubtitleOnly,
      preferred_tool: preferredTool === 'auto' ? undefined : preferredTool,
    }
    if (outputDir.trim()) metadata.output_dir = outputDir.trim()
    if (subtitleLanguages.trim()) metadata.subtitle_languages = subtitleLanguages.trim()
    if (extractAudioOnly) {
      metadata.audio_format = audioFormat
      metadata.audio_quality = audioQuality
    }
    if (cookiesFile.trim()) metadata.cookies_file = cookiesFile.trim()
    if (cookiesFromBrowser) metadata.cookies_from_browser = cookiesFromBrowser
    try {
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'video_download',
          metadata,
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

  const inputCls = 'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none'
  const labelCls = 'block text-sm font-medium text-[#94a3b8] mb-1'
  const checkboxCls = 'flex items-center gap-3 text-[#94a3b8] cursor-pointer'

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
            <label className={labelCls}>视频链接 <span className="text-red-400">*</span></label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://www.bilibili.com/video/BVxxx 或 b23.tv/xxx"
              className={inputCls}
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>视频质量</label>
              <select value={quality} onChange={e => setQuality(e.target.value)} className={inputCls}>
                <option value="best">最佳</option>
                <option value="1080p">1080p</option>
                <option value="720p">720p</option>
                <option value="480p">480p</option>
                <option value="360p">360p</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>优先工具</label>
              <select value={preferredTool} onChange={e => setPreferredTool(e.target.value)} className={inputCls}>
                <option value="auto">自动</option>
                <option value="yt-dlp">yt-dlp</option>
                <option value="you-get">you-get</option>
              </select>
            </div>
          </div>

          <div>
            <label className={labelCls}>保存目录（可选，须在用户主目录下）</label>
            <input
              type="text"
              value={outputDir}
              onChange={e => setOutputDir(e.target.value)}
              placeholder="留空使用默认下载目录"
              className={inputCls}
            />
          </div>

          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <label className={checkboxCls}>
              <input type="checkbox" checked={downloadSubtitle} onChange={e => setDownloadSubtitle(e.target.checked)} className="rounded" />
              下载字幕
            </label>
            <label className={checkboxCls}>
              <input type="checkbox" checked={downloadSubtitleOnly} onChange={e => setDownloadSubtitleOnly(e.target.checked)} className="rounded" />
              仅下载字幕
            </label>
            <label className={checkboxCls}>
              <input type="checkbox" checked={extractAudioOnly} onChange={e => setExtractAudioOnly(e.target.checked)} className="rounded" />
              仅提取音频
            </label>
            <label className={checkboxCls}>
              <input type="checkbox" checked={downloadThumbnail} onChange={e => setDownloadThumbnail(e.target.checked)} className="rounded" />
              下载封面
            </label>
            <label className={checkboxCls}>
              <input type="checkbox" checked={downloadDanmaku} onChange={e => setDownloadDanmaku(e.target.checked)} className="rounded" />
              B 站弹幕
            </label>
          </div>

          {extractAudioOnly && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>音频格式</label>
                <select value={audioFormat} onChange={e => setAudioFormat(e.target.value)} className={inputCls}>
                  <option value="mp3">MP3</option>
                  <option value="m4a">M4A</option>
                  <option value="opus">Opus</option>
                  <option value="wav">WAV</option>
                  <option value="aac">AAC</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>音频码率</label>
                <select value={audioQuality} onChange={e => setAudioQuality(e.target.value)} className={inputCls}>
                  <option value="128k">128k</option>
                  <option value="192k">192k</option>
                  <option value="256k">256k</option>
                  <option value="320k">320k</option>
                </select>
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-[#94a3b8] hover:text-accent"
          >
            {showAdvanced ? '收起' : '更多选项'} ▼
          </button>

          {showAdvanced && (
            <div className="space-y-4 border-l-2 border-border pl-4">
              <div>
                <label className={labelCls}>字幕语言（逗号分隔）</label>
                <input
                  type="text"
                  value={subtitleLanguages}
                  onChange={e => setSubtitleLanguages(e.target.value)}
                  placeholder="如：zh,en"
                  className={inputCls}
                />
              </div>
              <div>
                <label className={labelCls}>Cookies 文件路径</label>
                <input
                  type="text"
                  value={cookiesFile}
                  onChange={e => setCookiesFile(e.target.value)}
                  placeholder="Netscape 或 JSON 格式，用于需登录的视频"
                  className={inputCls}
                />
              </div>
              <div>
                <label className={labelCls}>从浏览器提取 Cookies</label>
                <select value={cookiesFromBrowser} onChange={e => setCookiesFromBrowser(e.target.value)} className={inputCls}>
                  <option value="">不使用</option>
                  <option value="chrome">Chrome</option>
                  <option value="firefox">Firefox</option>
                  <option value="safari">Safari</option>
                  <option value="edge">Edge</option>
                </select>
              </div>
            </div>
          )}

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
