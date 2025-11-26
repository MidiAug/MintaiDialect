import DemoPage from '@/pages/DemoPage'
import { Routes, Route, useLocation, Navigate } from 'react-router-dom'
import ProtectedRoute from '@/components/ProtectedRoute'
import DigitalJiagengPage from '@/pages/DigitalJiagengPage'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import AccountPage from '@/pages/AccountPage'
import ASRTTSPage from '@/pages/ASRTTSPage'
import SpeechTranslationPage from '@/pages/SpeechTranslationPage'
import VoiceInteractionPage from '@/pages/VoiceInteractionPage'
import VoiceCloningPage from '@/pages/VoiceCloningPage'
import AdminUsersPage from '@/pages/AdminUsersPage'
import { Layout } from 'antd'
import AppHeader from './components/Layout/AppHeader'
import { useEffect, useState } from 'react'
import { generateUUID } from '@/utils/uuid'

// 数字嘉庚自动重定向组件
function DigitalJiagengRedirect() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  
  useEffect(() => {
    // 生成新的UUID格式会话ID（兼容不支持 crypto.randomUUID 的浏览器）
    const newSessionId = generateUUID()
    setSessionId(newSessionId)
  }, [])
  
  if (sessionId) {
    return <Navigate to={`/digital-jiageng/sessions/${sessionId}`} replace />
  }
  
  return <div>正在创建新会话...</div>
}

function App() {
  const location = useLocation()
  
  // 1. 判断是否为沉浸式页面 (包含 /digital-jiageng)
  const isImmersivePage = location.pathname.startsWith('/digital-jiageng') || location.pathname === '/demo'
  
  if (location.pathname === '/demo') {
    return <DemoPage />
  }
  
  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 2. 如果不是沉浸式页面，才显示 Header */}
      {!isImmersivePage && <AppHeader />}
      
      {/* 3. 动态调整容器样式 */}
      {/* 如果是沉浸式页面，我们需要移除默认的 padding/margin，让组件全屏覆盖 */}
      <div 
        className={isImmersivePage ? "" : "main-container"} 
        style={isImmersivePage ? { width: '100%', height: '100vh', overflow: 'hidden' } : {}}
      >
        <div className={isImmersivePage ? "" : "page-container"}>
            <Routes>
              <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/account" element={<ProtectedRoute><AccountPage /></ProtectedRoute>} />
              <Route path="/asr-tts" element={<ProtectedRoute><ASRTTSPage /></ProtectedRoute>} />
              <Route path="/speech-translation" element={<ProtectedRoute><SpeechTranslationPage /></ProtectedRoute>} />
              <Route path="/voice-interaction" element={<ProtectedRoute><VoiceInteractionPage /></ProtectedRoute>} />
              <Route path="/voice-cloning" element={<ProtectedRoute><VoiceCloningPage /></ProtectedRoute>} />
              <Route path="/admin/users" element={<ProtectedRoute requireAdmin><AdminUsersPage /></ProtectedRoute>} />
              
              {/* 嘉庚路由 */}
              <Route path="/digital-jiageng" element={<ProtectedRoute><DigitalJiagengRedirect /></ProtectedRoute>} />
              <Route path="/digital-jiageng/sessions/:sessionId" element={<ProtectedRoute><DigitalJiagengPage /></ProtectedRoute>} />
            </Routes>
          </div>
      </div>
    </Layout>
  )
}

export default App