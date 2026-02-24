import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

const DARK_STORAGE_KEY = 'hou-cli-dark-mode'
const isDark = () => localStorage.getItem(DARK_STORAGE_KEY) !== '0'
if (isDark()) document.documentElement.classList.add('dark')
else document.documentElement.classList.remove('dark')

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
