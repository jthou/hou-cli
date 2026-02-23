import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TaskManagement from './pages/TaskManagement'
import VideoDownload from './pages/VideoDownload'
import SettingsGeneral from './pages/SettingsGeneral'
import SettingsStorage from './pages/SettingsStorage'
import SettingsTests from './pages/SettingsTests'
import SettingsBackend from './pages/SettingsBackend'
import About from './pages/About'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <BrowserRouter>
      <div className="flex h-screen w-full">
        <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className="flex-1 flex flex-col min-w-0 bg-surface overflow-hidden">
          <Routes>
            <Route path="/" element={<TaskManagement />} />
            <Route path="/video-download" element={<VideoDownload />} />
            <Route path="/settings/general" element={<SettingsGeneral />} />
            <Route path="/settings/storage" element={<SettingsStorage />} />
            <Route path="/settings/tests" element={<SettingsTests />} />
            <Route path="/settings/backend" element={<SettingsBackend />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
