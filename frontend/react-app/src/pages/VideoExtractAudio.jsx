import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function VideoExtractAudio() {
  const [inputFile, setInputFile] = useState('')
  const [outputFile, setOutputFile] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [audioFormat, setAudioFormat] = useState('mp3')
  const [audioQuality, setAudioQuality] = useState('192k')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!inputFile.trim()) {
      alert('请输入视频文件路径')
      return
    }
    setSubmitting(true)
    setResult(null)
    const metadata = {
      input_file: inputFile.trim(),
      audio_format: audioFormat,
      audio_quality: audioQuality,
    }
    if (outputFile.trim()) metadata.output_file = outputFile.trim()
    if (outputDir.trim()) metadata.output_dir = outputDir.trim()
    try {
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: 'video_extract_audio',
          metadata,
        }),
      })
      const data = await res.json()
      if (data.success) {
        setResult({ taskId: data.task_id, success: true })
        setInputFile('')
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

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">视频提取音频</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        <p className="text-[#94a3b8] mb-6">
          从本地视频文件中提取音频轨并保存为音频文件。提交后任务将加入队列，可在
          <Link to="/" className="text-accent hover:underline ml-1">任务管理</Link>
          中查看进度。
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelCls}>视频文件路径 <span className="text-red-400">*</span></label>
            <input
              type="text"
              value={inputFile}
              onChange={e => setInputFile(e.target.value)}
              placeholder="如：/Users/xx/video.mp4（须在用户主目录下）"
              className={inputCls}
              required
            />
          </div>

          <div>
            <label className={labelCls}>输出文件路径（可选）</label>
            <input
              type="text"
              value={outputFile}
              onChange={e => setOutputFile(e.target.value)}
              placeholder="不填则自动生成到 ~/hou-cli/outputs"
              className={inputCls}
            />
          </div>

          <div>
            <label className={labelCls}>输出目录（可选，未指定输出文件时生效）</label>
            <input
              type="text"
              value={outputDir}
              onChange={e => setOutputDir(e.target.value)}
              placeholder="留空使用 ~/hou-cli/outputs"
              className={inputCls}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>音频格式</label>
              <select value={audioFormat} onChange={e => setAudioFormat(e.target.value)} className={inputCls}>
                <option value="mp3">MP3</option>
                <option value="wav">WAV</option>
                <option value="aac">AAC</option>
                <option value="flac">FLAC</option>
                <option value="ogg">OGG</option>
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

          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 transition-colors"
          >
            {submitting ? '提交中...' : '提交任务'}
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
