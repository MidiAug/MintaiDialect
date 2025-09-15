import React from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { Layout } from 'antd'
import AppHeader from '@/components/Layout/AppHeader'
import JiagengHeader from '@/components/Layout/JiagengHeader'
import AppFooter from '@/components/Layout/AppFooter'
import ScrollToTop from '@/components/ScrollToTop'
import HomePage from '@/pages/HomePage'
import ASRTTSPage from '@/pages/ASRTTSPage'
import SpeechTranslationPage from '@/pages/SpeechTranslationPage'
import VoiceInteractionPage from '@/pages/VoiceInteractionPage'
import VoiceCloningPage from '@/pages/VoiceCloningPage'
import DigitalJiagengPage from '@/pages/DigitalJiagengPage'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import ProtectedRoute from '@/components/ProtectedRoute'
import AccountPage from '@/pages/AccountPage'

const { Content } = Layout

function App() {
  const location = useLocation()
  const isRoot = location.pathname === '/'
  return (
    <Layout className="app-layout">
      <ScrollToTop />
      {isRoot ? <JiagengHeader /> : <AppHeader />}
      <Content className="main-content">
        <div className="page-container">
          <Routes>
            <Route path="/" element={<ProtectedRoute><DigitalJiagengPage /></ProtectedRoute>} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/account" element={<ProtectedRoute><AccountPage /></ProtectedRoute>} />
            <Route path="/asr-tts" element={<ProtectedRoute><ASRTTSPage /></ProtectedRoute>} />
            <Route path="/speech-translation" element={<ProtectedRoute><SpeechTranslationPage /></ProtectedRoute>} />
            <Route path="/voice-interaction" element={<ProtectedRoute><VoiceInteractionPage /></ProtectedRoute>} />
            <Route path="/voice-cloning" element={<ProtectedRoute><VoiceCloningPage /></ProtectedRoute>} />
            <Route path="/digital-jiageng" element={<ProtectedRoute><DigitalJiagengPage /></ProtectedRoute>} />
          </Routes>
        </div>
      </Content>
      {!isRoot && <AppFooter />}
    </Layout>
  )
}

export default App 