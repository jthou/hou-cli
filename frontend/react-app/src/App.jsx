import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ToastProvider } from './components/ToastModal'
import Sidebar from './components/Sidebar'
import TaskManagement from './pages/TaskManagement'
import PipelineOrchestration from './pages/PipelineOrchestration'
import VideoDownload from './pages/VideoDownload'
import VideoExtractAudio from './pages/VideoExtractAudio'
import SpeechToText from './pages/SpeechToText'
import WeatherQuery from './pages/WeatherQuery'
import WebSearch from './pages/WebSearch'
import ArticleWriting from './pages/ArticleWriting'
import SettingsGeneral from './pages/SettingsGeneral'
import SettingsStorage from './pages/SettingsStorage'
import SettingsTests from './pages/SettingsTests'
import SettingsBackend from './pages/SettingsBackend'
import SettingsLlmAudit from './pages/SettingsLlmAudit'
import SettingsSystemPromptAudit from './pages/SettingsSystemPromptAudit'
import About from './pages/About'
import WechatDraftPage from './pages/WechatDraftPage'
import UrlToWiki from './pages/UrlToWiki'
import PdfToWiki from './pages/PdfToWiki'
import WikiDirectory from './pages/WikiDirectory'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <ToastProvider>
      <BrowserRouter>
        <div className="flex h-screen w-full">
          <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
          <main className="flex-1 flex flex-col min-w-0 min-h-0 bg-surface overflow-hidden">
            <Routes>
              <Route path="/" element={<TaskManagement />} />
              <Route path="/pipeline" element={<PipelineOrchestration />} />
              <Route path="/video-download" element={<VideoDownload />} />
              <Route path="/video-extract-audio" element={<VideoExtractAudio />} />
              <Route path="/speech-to-text" element={<SpeechToText />} />
              <Route path="/weather-query" element={<WeatherQuery />} />
              <Route path="/web-search" element={<WebSearch />} />
              <Route path="/article-writing" element={<ArticleWriting />} />
              <Route path="/wechat-drafts" element={<WechatDraftPage />} />
              <Route path="/url-to-wiki" element={<UrlToWiki />} />
              <Route path="/pdf-to-wiki" element={<PdfToWiki />} />
              <Route path="/wiki-directory" element={<WikiDirectory />} />
              <Route path="/settings/general" element={<SettingsGeneral />} />
              <Route path="/settings/storage" element={<SettingsStorage />} />
              <Route path="/settings/llm-audit" element={<SettingsLlmAudit />} />
              <Route path="/settings/system-prompt-audit" element={<SettingsSystemPromptAudit />} />
              <Route path="/settings/tests" element={<SettingsTests />} />
              <Route path="/settings/backend" element={<SettingsBackend />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </ToastProvider>
  )
}
