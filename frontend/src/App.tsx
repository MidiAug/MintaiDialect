import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import AppHeader from '@/components/Layout/AppHeader'
import AppFooter from '@/components/Layout/AppFooter'
import ScrollToTop from '@/components/ScrollToTop'
import HomePage from '@/pages/HomePage'
import ASRTTSPage from '@/pages/ASRTTSPage'
import SpeechTranslationPage from '@/pages/SpeechTranslationPage'
import VoiceInteractionPage from '@/pages/VoiceInteractionPage'
import VoiceCloningPage from '@/pages/VoiceCloningPage'
import DigitalJiagengPage from '@/pages/DigitalJiagengPage'

const { Content } = Layout

function App() {
  return (
    <Layout className="app-layout">
      <ScrollToTop />
      <AppHeader />
      <Content className="main-content">
        <div className="page-container">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/asr-tts" element={<ASRTTSPage />} />
            <Route path="/speech-translation" element={<SpeechTranslationPage />} />
            <Route path="/voice-interaction" element={<VoiceInteractionPage />} />
            <Route path="/voice-cloning" element={<VoiceCloningPage />} />
            <Route path="/digital-jiageng" element={<DigitalJiagengPage />} />
          </Routes>
        </div>
      </Content>
      <AppFooter />
    </Layout>
  )
}

export default App 