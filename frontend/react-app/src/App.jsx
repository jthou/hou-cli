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
import SettingsGeneral from './pages/SettingsGeneral'
import SettingsStorage from './pages/SettingsStorage'
import SettingsTests from './pages/SettingsTests'
import SettingsBackend from './pages/SettingsBackend'
import About from './pages/About'
import WechatDraftPage from './pages/WechatDraftPage'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <ToastProvider>
      <BrowserRouter>
        <div className="flex h-screen w-full">
          <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
          <main className="flex-1 flex flex-col min-w-0 bg-surface overflow-hidden">
            <Routes>
              <Route path="/" element={<TaskManagement />} />
              <Route path="/pipeline" element={<PipelineOrchestration />} />
              <Route path="/video-download" element={<VideoDownload />} />
              <Route path="/video-extract-audio" element={<VideoExtractAudio />} />
              <Route path="/speech-to-text" element={<SpeechToText />} />
              <Route path="/weather-query" element={<WeatherQuery />} />
              <Route path="/wechat-drafts" element={<WechatDraftPage />} />
              <Route path="/settings/general" element={<SettingsGeneral />} />
              <Route path="/settings/storage" element={<SettingsStorage />} />
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
