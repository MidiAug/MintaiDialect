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
import { Layout } from 'antd'
import AppHeader from './components/Layout/AppHeader'
import { useEffect, useState } from 'react'

// 数字嘉庚自动重定向组件
function DigitalJiagengRedirect() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  
  useEffect(() => {
    // 生成新的UUID格式会话ID
    const newSessionId = crypto.randomUUID()
    setSessionId(newSessionId)
  }, [])
  
  if (sessionId) {
    return <Navigate to={`/digital-jiageng/sessions/${sessionId}`} replace />
  }
  
  return <div>正在创建新会话...</div>
}

function App() {
  const location = useLocation()
  const isDemo = location.pathname === '/demo'
  
  if (isDemo) {
    return <DemoPage />
  }
  
  return (
    <Layout>
      <AppHeader />
      <div className="main-container">
        <div className="page-container">
            <Routes>
              <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/account" element={<ProtectedRoute><AccountPage /></ProtectedRoute>} />
              <Route path="/asr-tts" element={<ProtectedRoute><ASRTTSPage /></ProtectedRoute>} />
              <Route path="/speech-translation" element={<ProtectedRoute><SpeechTranslationPage /></ProtectedRoute>} />
              <Route path="/voice-interaction" element={<ProtectedRoute><VoiceInteractionPage /></ProtectedRoute>} />
              <Route path="/voice-cloning" element={<ProtectedRoute><VoiceCloningPage /></ProtectedRoute>} />
              <Route path="/digital-jiageng" element={<ProtectedRoute><DigitalJiagengRedirect /></ProtectedRoute>} />
              <Route path="/digital-jiageng/sessions/:sessionId" element={<ProtectedRoute><DigitalJiagengPage /></ProtectedRoute>} />
            </Routes>
          </div>
      </div>
    </Layout>
  )
}

export default App 