import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ToastProvider } from './components/ToastModal'
import Sidebar from './components/Sidebar'
import Home from './pages/Home'
import WorkAssistant from './pages/WorkAssistant'
import GeneralChat from './pages/GeneralChat'
import CodeAssistant from './pages/CodeAssistant'
import TaskManagement from './pages/TaskManagement'
import PipelineOrchestration from './pages/PipelineOrchestration'
import VideoDownload from './pages/VideoDownload'
import ImageGeneration from './pages/ImageGeneration'
import VideoExtractAudio from './pages/VideoExtractAudio'
import SpeechToText from './pages/SpeechToText'
import WeatherQuery from './pages/WeatherQuery'
import DiskScan from './pages/DiskScan'
import WebSearch from './pages/WebSearch'
import AiHotNews from './pages/AiHotNews'
import ArticleWriting from './pages/ArticleWriting'
import PptAssistant from './pages/PptAssistant'
import SettingsGeneral from './pages/SettingsGeneral'
import SettingsWritingProfile from './pages/SettingsWritingProfile'
import SettingsWorkConfig from './pages/SettingsWorkConfig'
import SettingsStorage from './pages/SettingsStorage'
import SettingsTests from './pages/SettingsTests'
import SettingsBackend from './pages/SettingsBackend'
import SettingsLlmAudit from './pages/SettingsLlmAudit'
import SettingsNetworkAudit from './pages/SettingsNetworkAudit'
import SettingsSystemPromptAudit from './pages/SettingsSystemPromptAudit'
import SettingsModelConfigAudit from './pages/SettingsModelConfigAudit'
import SettingsKanban from './pages/SettingsKanban'
import SettingsDevAudit from './pages/SettingsDevAudit'
import About from './pages/About'
import WechatDraftPage from './pages/WechatDraftPage'
import UrlToWiki from './pages/UrlToWiki'
import PdfToWiki from './pages/PdfToWiki'
import PdfReader from './pages/PdfReader'
import WikiDirectory from './pages/WikiDirectory'
import MediaWikiReader from './pages/MediaWikiReader'
import WikipediaReader from './pages/WikipediaReader'
import WebReader from './pages/WebReader'
import WereadReader from './pages/WereadReader'
import AddReference from './pages/AddReference'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <ToastProvider>
      <BrowserRouter>
        <div className="flex h-screen w-full">
          <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
          <main className="flex-1 flex flex-col min-w-0 min-h-0 bg-surface overflow-hidden">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/home" element={<Home />} />
              <Route path="/work-assistant" element={<WorkAssistant />} />
              <Route path="/general-chat" element={<GeneralChat />} />
              <Route path="/code-assistant" element={<CodeAssistant />} />
              <Route path="/tasks" element={<TaskManagement />} />
              <Route path="/pipeline" element={<PipelineOrchestration />} />
              <Route path="/video-download" element={<VideoDownload />} />
              <Route path="/image-generation" element={<ImageGeneration />} />
              <Route path="/video-extract-audio" element={<VideoExtractAudio />} />
              <Route path="/speech-to-text" element={<SpeechToText />} />
              <Route path="/weather-query" element={<WeatherQuery />} />
              <Route path="/disk-scan" element={<DiskScan />} />
              <Route path="/web-search" element={<WebSearch />} />
              <Route path="/ai-hot-news" element={<AiHotNews />} />
              <Route path="/article-writing" element={<ArticleWriting />} />
              <Route path="/ppt-assistant" element={<PptAssistant />} />
              <Route path="/add-reference" element={<AddReference />} />
              <Route path="/wechat-drafts" element={<WechatDraftPage />} />
              <Route path="/url-to-wiki" element={<UrlToWiki />} />
              <Route path="/pdf-to-wiki" element={<PdfToWiki />} />
              <Route path="/pdf-reader" element={<PdfReader />} />
              <Route path="/mediawiki-reader" element={<MediaWikiReader />} />
              <Route path="/wikipedia-reader" element={<WikipediaReader />} />
              <Route path="/web-reader" element={<WebReader />} />
              <Route path="/weread-reader" element={<WereadReader />} />
              <Route path="/wiki-directory" element={<WikiDirectory />} />
              <Route path="/settings/general" element={<SettingsGeneral />} />
              <Route path="/settings/writing-profile" element={<SettingsWritingProfile />} />
              <Route path="/settings/work-config" element={<SettingsWorkConfig />} />
              <Route path="/settings/storage" element={<SettingsStorage />} />
              <Route path="/settings/llm-audit" element={<SettingsLlmAudit />} />
              <Route path="/settings/network-audit" element={<SettingsNetworkAudit />} />
              <Route path="/settings/system-prompt-audit" element={<SettingsSystemPromptAudit />} />
              <Route path="/settings/model-config-audit" element={<SettingsModelConfigAudit />} />
              <Route
                path="/settings/model-availability-audit"
                element={<Navigate to="/settings/model-config-audit" replace />}
              />
              <Route path="/settings/kanban" element={<SettingsKanban />} />
              <Route path="/settings/tests" element={<SettingsTests />} />
              <Route path="/settings/dev-audit" element={<SettingsDevAudit />} />
              <Route path="/settings/backend" element={<SettingsBackend />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </ToastProvider>
  )
}
