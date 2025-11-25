import React, { useState, useRef, useEffect } from 'react'
import { 
  Typography, 
  Button, 
  Select, 
  message, 
  Space, 
  Switch,
  Avatar,
  Drawer,
  Modal,
  ConfigProvider,
  theme
} from 'antd'
import { 
  AudioOutlined, 
  SettingOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  HomeOutlined
} from '@ant-design/icons'
import { digitalJiagengAPI, LanguageType } from '@/services/api'
import jiagengImg from '@/assets/jiageng.png' // 确保你的路径正确
import { useParams, useNavigate } from 'react-router-dom'

const { Text, Title, Paragraph } = Typography

// --- 类型定义 ---
interface ChatMessage {
  id: string
  type: 'user' | 'jiageng'
  content: string
  audioUrl?: string
  timestamp: string
  audioBlob?: Blob
  isPlaying?: boolean
  subtitles?: Array<{
    text: string
    start_time: number
    end_time: number
  }>
}

interface JiagengSettings {
  enableRolePlay: boolean
  inputLanguage: LanguageType
  outputLanguage: LanguageType
  voiceGender: 'male' | 'female'
  speakingSpeed: number
  showSubtitles: boolean
  enableStream: boolean  // 流式开关
}

const DigitalJiagengPage: React.FC = () => {
  // --- 状态管理 ---
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null)
  const [currentSubtitleText, setCurrentSubtitleText] = useState<string>('')
  const [recordingTime, setRecordingTime] = useState(0)
  const [sessionId, setSessionId] = useState<string | null>(urlSessionId || null)
  
  // UI 状态
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [introOpen, setIntroOpen] = useState(false)

  // 设置
  const [settings, setSettings] = useState<JiagengSettings>({
    enableRolePlay: true,
    inputLanguage: LanguageType.MINNAN,
    outputLanguage: LanguageType.MINNAN,
    voiceGender: 'male',
    speakingSpeed: 1.0,
    showSubtitles: true,
    enableStream: false  // 流式开关默认关闭
  })

  // --- Refs ---
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recordingChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const recordingTimerRef = useRef<number | null>(null)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const lastSubtitleRef = useRef<string>('')
  const lastLogTimeRef = useRef<number>(0)
  const DEBUG_SUBS = true
  
  // 流式播放队列管理
  const audioQueueRef = useRef<Array<{
    segmentIndex: number
    audioUrl: string
    text: string
    subtitles: Array<{ text: string; start_time: number; end_time: number }>
    duration: number
  }>>([])
  const isPlayingQueueRef = useRef<boolean>(false)
  const currentQueueIndexRef = useRef<number>(0)
  const accumulatedTextRef = useRef<string>('')

  // --- 辅助逻辑 ---

  // 1. 初始化 Session
  useEffect(() => {
    if (urlSessionId) {
      setSessionId(urlSessionId)
    } else {
      const newSessionId = crypto.randomUUID()
      setSessionId(newSessionId)
      window.history.replaceState(null, '', `/digital-jiageng/sessions/${newSessionId}`)
    }
  }, [urlSessionId])

  // 2. 权限初始化
  const initAudioContext = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      return stream
    } catch (error) {
      console.error('音频权限获取失败:', error)
      message.error('无法获取麦克风权限，请检查浏览器设置')
      return null
    }
  }

  // 3. Audio Blob 转 WAV
  const convertToWav = async (blob: Blob): Promise<Blob> => {
    const arrayBuffer = await blob.arrayBuffer()
    const AudioCtx = (window as any).AudioContext || (window as any).webkitAudioContext
    const audioCtx = new AudioCtx()
    const decoded: AudioBuffer = await new Promise((resolve, reject) => {
      const copy = arrayBuffer.slice(0)
      audioCtx.decodeAudioData(copy, resolve, reject)
    })
    if ((audioCtx as any).close) { try { await (audioCtx as any).close() } catch {} }
    
    const targetSampleRate = 16000
    const duration = decoded.duration
    const OfflineCtx = (window as any).OfflineAudioContext || (window as any).webkitOfflineAudioContext
    const offline: OfflineAudioContext = new OfflineCtx(1, Math.ceil(targetSampleRate * duration), targetSampleRate)
    const src = offline.createBufferSource()
    const monoBuffer = offline.createBuffer(1, decoded.length, decoded.sampleRate)
    const ch0 = new Float32Array(decoded.length)
    decoded.copyFromChannel(ch0, 0)
    if (decoded.numberOfChannels > 1) {
      const ch1 = new Float32Array(decoded.length)
      decoded.copyFromChannel(ch1, 1)
      for (let i = 0; i < ch0.length; i++) ch0[i] = (ch0[i] + ch1[i]) / 2
    }
    monoBuffer.copyToChannel(ch0, 0)
    src.buffer = monoBuffer
    src.connect(offline.destination)
    src.start()
    const rendered = await offline.startRendering()
    const pcm = rendered.getChannelData(0)
    
    const wavBuffer = new ArrayBuffer(44 + pcm.length * 2)
    const view = new DataView(wavBuffer)
    const writeString = (offset: number, s: string) => { for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i)) }
    
    writeString(0, 'RIFF')
    view.setUint32(4, 36 + pcm.length * 2, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true)
    view.setUint16(22, 1, true)
    view.setUint32(24, targetSampleRate, true)
    view.setUint32(28, targetSampleRate * 2, true)
    view.setUint16(32, 2, true)
    view.setUint16(34, 16, true)
    writeString(36, 'data')
    view.setUint32(40, pcm.length * 2, true)
    
    let offset = 44
    for (let i = 0; i < pcm.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, pcm[i]))
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
    }
    return new Blob([view], { type: 'audio/wav' })
  }

  // 4. 字幕清洗
  const stripPunctForDisplay = (s: string) =>
    (s || '')
      .replace(/^\s*(zh|tlp)\s*[:：\\/\-]*\s*/i, '')
      .replace(/\\/g, '')
      .replace(/[，,。\.！!？?、；;：:（）()【】\[\]“”‘’'"…—\-]/g, '')
      .trim()

  // 5. 开始录音
  const startRecording = async () => {
    if (isRecording) return
    
    const stream = await initAudioContext()
    if (!stream) return

    recordingChunksRef.current = []
    let preferredMimeType = ''
    if ((window as any).MediaRecorder) {
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) preferredMimeType = 'audio/webm;codecs=opus'
        else if (MediaRecorder.isTypeSupported('audio/webm')) preferredMimeType = 'audio/webm'
    }

    mediaRecorderRef.current = new MediaRecorder(stream, preferredMimeType ? { mimeType: preferredMimeType } : undefined)
    
    mediaRecorderRef.current.ondataavailable = (event) => {
      if (event.data.size > 0) recordingChunksRef.current.push(event.data)
    }

    mediaRecorderRef.current.start()
    setIsRecording(true)
    setRecordingTime(0)
    
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current)
    recordingTimerRef.current = window.setInterval(() => {
      setRecordingTime(prev => prev + 1)
    }, 1000)
  }

  // 6. 停止录音
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current)
      
      mediaRecorderRef.current.onstop = async () => {
        try {
          const rawType = mediaRecorderRef.current?.mimeType || 'audio/webm'
          const rawBlob = new Blob(recordingChunksRef.current, { type: rawType })
          const wavBlob = await convertToWav(rawBlob)
          const wavFile = new File([wavBlob], 'recording.wav', { type: 'audio/wav' })
          // 根据流式开关决定使用流式还是非流式版本
          if (settings.enableStream) {
            handleAudioMessageStream(wavFile)
          } else {
          handleAudioMessage(wavFile)
          }
        } catch (err) {
          console.error('WAV转换失败:', err)
          const fallbackBlob = new Blob(recordingChunksRef.current, { type: 'audio/webm' })
          const fallbackFile = new File([fallbackBlob], 'recording.webm', { type: 'audio/webm' })
          // 根据流式开关决定使用流式还是非流式版本
          if (settings.enableStream) {
            handleAudioMessageStream(fallbackFile)
          } else {
          handleAudioMessage(fallbackFile)
          }
        }
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }
    }
  }

  // 6.5. 播放队列中的下一个片段
  const playNextSegment = () => {
    if (isPlayingQueueRef.current) return
    
    const queue = audioQueueRef.current
    if (currentQueueIndexRef.current >= queue.length) {
      // 队列播放完成
      isPlayingQueueRef.current = false
      currentQueueIndexRef.current = 0
      audioQueueRef.current = []
      setCurrentSubtitleText('')
      return
    }
    
    const segment = queue[currentQueueIndexRef.current]
    if (!segment) {
      playNextSegment() // 跳过无效片段
      return
    }
    
    isPlayingQueueRef.current = true
    
    const audio = new Audio(segment.audioUrl)
    currentAudioRef.current = audio
    
    // 设置字幕同步
    audio.ontimeupdate = () => {
      const currentTime = audio.currentTime
      const epsilon = 0.05
      const seg = segment.subtitles.find(
        s => currentTime >= Math.max(0, s.start_time - epsilon) && currentTime <= s.end_time + epsilon
      )
      const raw = seg?.text || ''
      const show = stripPunctForDisplay(raw)
      if (show !== lastSubtitleRef.current) {
        lastSubtitleRef.current = show
        setCurrentSubtitleText(show)
      }
    }
    
    audio.onended = () => {
      currentQueueIndexRef.current++
      isPlayingQueueRef.current = false
      playNextSegment() // 自动播放下一个片段
    }
    
    audio.onerror = () => {
      console.error(`[Stream] 片段 ${segment.segmentIndex} 播放失败`)
      currentQueueIndexRef.current++
      isPlayingQueueRef.current = false
      playNextSegment() // 即使失败也继续下一个
    }
    
    audio.play().catch(err => {
      console.error(`[Stream] 片段 ${segment.segmentIndex} 播放错误:`, err)
      currentQueueIndexRef.current++
      isPlayingQueueRef.current = false
      playNextSegment()
    })
  }

  // 6.6. 处理流式音频消息
  const handleAudioMessageStream = async (audioFile: File) => {
    if (recordingTime < 1) {
      message.warning('说话时间太短了')
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: '[语音消息]',
      audioUrl: URL.createObjectURL(audioFile),
      audioBlob: audioFile,
      timestamp: new Date().toLocaleTimeString()
    }

    setMessages(prev => [...prev, userMessage])
    setIsProcessing(true)

    // 创建嘉庚消息（初始为空，流式更新）
    const jiagengMessageId = (Date.now() + 1).toString()
    const jiagengMessage: ChatMessage = {
      id: jiagengMessageId,
      type: 'jiageng',
      content: '',
      timestamp: new Date().toLocaleTimeString(),
      subtitles: [],
    }
    setMessages(prev => [...prev, jiagengMessage])

    // 重置队列状态
    audioQueueRef.current = []
    currentQueueIndexRef.current = 0
    isPlayingQueueRef.current = false
    accumulatedTextRef.current = ''

    try {
      await digitalJiagengAPI.chatWithJiagengStream(
        {
          audio_file: audioFile,
          session_id: sessionId || undefined,
          settings: ({
            enable_role_play: settings.enableRolePlay,
            input_language: settings.inputLanguage,
            output_language: settings.outputLanguage,
            voice_gender: settings.voiceGender,
            speaking_speed: settings.speakingSpeed,
            show_subtitles: settings.showSubtitles
          } as any)
        },
        (chunk) => {
          console.log('[Stream] 收到 chunk:', chunk.type, chunk)
          
          if (chunk.type === 'segment') {
            // 收到片段，添加到队列
            if (chunk.audio_url && chunk.text) {
              const segmentData = {
                segmentIndex: chunk.segment_index || 0,
                audioUrl: chunk.audio_url,
                text: chunk.text,
                subtitles: chunk.subtitles || [],
                duration: chunk.audio_duration || 0,
              }
              
              // 按 segment_index 排序插入队列
              audioQueueRef.current.push(segmentData)
              audioQueueRef.current.sort((a, b) => a.segmentIndex - b.segmentIndex)
              
              // 更新消息内容
              accumulatedTextRef.current += chunk.text
              setMessages(prev => prev.map(msg => 
                msg.id === jiagengMessageId 
                  ? { ...msg, content: accumulatedTextRef.current }
                  : msg
              ))
              
              // 如果是第一个片段，立即开始播放
              if (audioQueueRef.current.length === 1 && !isPlayingQueueRef.current) {
                playNextSegment()
              }
            }
          } else if (chunk.type === 'complete') {
            // 流式完成
            console.log('[Stream] 收到完成消息，更新状态')
            setMessages(prev => prev.map(msg => 
              msg.id === jiagengMessageId 
                ? { 
                    ...msg, 
                    content: chunk.text || accumulatedTextRef.current,
                    subtitles: chunk.all_segments?.flatMap((seg: any) => seg.subtitles || []) || []
                  }
                : msg
            ))
            
            setIsProcessing(false)
            console.log('[Stream] isProcessing 已设置为 false')
          } else if (chunk.type === 'error') {
            // 错误处理
            console.error('[Stream] 收到错误消息:', chunk.error)
            message.error(chunk.error || '嘉庚先生好像没听清，请重试')
            setIsProcessing(false)
          } else {
            // 未知类型，也设置为完成（防止卡住）
            console.warn('[Stream] 收到未知类型消息:', chunk)
            setIsProcessing(false)
          }
        }
      )
    } catch (error) {
      console.error('[Stream] 流式请求异常:', error)
      message.error('网络连接异常')
      setIsProcessing(false)
    }
  }

  // 7. 处理音频发送（非流式版本，保留兼容性）
  const handleAudioMessage = async (audioFile: File) => {
    if (recordingTime < 1) {
      message.warning('说话时间太短了')
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: '[语音消息]',
      audioUrl: URL.createObjectURL(audioFile),
      audioBlob: audioFile,
      timestamp: new Date().toLocaleTimeString()
    }

    setMessages(prev => [...prev, userMessage])
    setIsProcessing(true)

    try {
      const response = await digitalJiagengAPI.chatWithJiageng({
        audio_file: audioFile,
        session_id: sessionId || undefined,
        settings: ({
          enable_role_play: settings.enableRolePlay,
          input_language: settings.inputLanguage,
          output_language: settings.outputLanguage,
          voice_gender: settings.voiceGender,
          speaking_speed: settings.speakingSpeed,
          show_subtitles: settings.showSubtitles
        } as any)
      })

      if (response.success) {
        if (response.data.session_id && response.data.session_id !== sessionId) {
          setSessionId(response.data.session_id)
        }

        const jiagengMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'jiageng',
          content: '',
          audioUrl: response.data.response_audio_url,
          timestamp: new Date().toLocaleTimeString(),
          subtitles: (response.data as any)?.subtitles || []
        }

        setMessages(prev => [...prev, jiagengMessage])
        
        if (response.data.response_audio_url) {
          playAudio(jiagengMessage.id, response.data.response_audio_url, undefined, jiagengMessage.subtitles)
        }
      } else {
        message.error('嘉庚先生好像没听清，请重试')
      }
    } catch (error) {
      console.error(error)
      message.error('网络连接异常')
    } finally {
      setIsProcessing(false)
    }
  }

  // 8. 播放音频与字幕同步
  const playAudio = (messageId: string, audioUrl: string, contentText?: string, initialSubtitles?: Array<{ text: string; start_time: number; end_time: number }>) => {
    if (currentlyPlaying === messageId) {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause()
        currentAudioRef.current = null
      }
      setCurrentlyPlaying(null)
      setCurrentSubtitleText('')
      setMessages(prev => prev.map(msg => msg.id === messageId ? { ...msg, isPlaying: false } : msg))
    } else {
      setCurrentlyPlaying(messageId)
      setCurrentSubtitleText('')
      lastSubtitleRef.current = ''
      setMessages(prev => prev.map(msg => msg.id === messageId ? { ...msg, isPlaying: true } : { ...msg, isPlaying: false }))

      const audio = new Audio(audioUrl)
      currentAudioRef.current = audio

      const message = messages.find(msg => msg.id === messageId)
      let subtitles = (initialSubtitles && initialSubtitles.length > 0) ? initialSubtitles : (message?.subtitles || [])

      audio.ontimeupdate = () => {
        const currentTime = audio.currentTime
        const epsilon = 0.05
        const seg = subtitles.find(
          s => currentTime >= Math.max(0, s.start_time - epsilon) && currentTime <= s.end_time + epsilon
        )
        const raw = seg?.text || ''
        const show = stripPunctForDisplay(raw)
        if (show !== lastSubtitleRef.current) {
          lastSubtitleRef.current = show
          setCurrentSubtitleText(show)
        }
      }

      audio.onended = () => {
        setCurrentlyPlaying(null)
        setCurrentSubtitleText('')
        currentAudioRef.current = null
        setMessages(prev => prev.map(msg => msg.id === messageId ? { ...msg, isPlaying: false } : msg))
      }

      if (currentAudioRef.current && currentAudioRef.current !== audio) {
        try { currentAudioRef.current.pause() } catch {}
      }
      audio.play()
    }
  }


  // ==========================================
  // 视觉与渲染 (UI Refactor)
  // ==========================================

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          fontFamily: "'Noto Serif SC', 'Songti SC', serif",
          colorPrimary: '#d4af37',
        }
      }}
    >
      <div className="immersive-container">
        {/* CSS-in-JS 样式定义 */}
        <style>{`
            @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap');

            .immersive-container {
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: radial-gradient(circle at 50% 30%, #2b3a42 0%, #0f1014 100%);
                font-family: 'Noto Serif SC', serif;
                color: #e0e0e0;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .top-bar {
                padding: 20px 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 10;
            }
            .nav-btn {
                background: rgba(255,255,255,0.08) !important;
                border: none !important;
                color: rgba(255,255,255,0.7) !important;
            }
            .nav-btn:hover {
                background: rgba(255,255,255,0.15) !important;
                color: #fff !important;
            }

            .main-stage {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                position: relative;
                width: 100%;
            }

            .avatar-wrapper {
                position: relative;
                transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
            }
            .avatar-image {
                width: 200px; height: 200px;
                border-radius: 50%;
                object-fit: cover;
                border: 4px solid rgba(212, 175, 55, 0.3);
                box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                transition: transform 0.5s ease, box-shadow 0.5s ease;
            }

            .processing .avatar-image {
                animation: breathe 2s infinite ease-in-out;
                filter: brightness(1.1);
            }
            .speaking .avatar-image {
                transform: scale(1.08);
                border-color: rgba(212, 175, 55, 0.8);
                box-shadow: 0 0 50px rgba(212, 175, 55, 0.4);
            }

            .subtitle-overlay {
                margin-top: 40px;
                min-height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0 20px;
                text-align: center;
                width: 100%;
                max-width: 800px;
            }
            .subtitle-text {
                font-size: 24px;
                font-weight: 500;
                color: rgba(255,255,255,0.95);
                text-shadow: 0 2px 8px rgba(0,0,0,0.8);
                letter-spacing: 1px;
                background: linear-gradient(to right, transparent, rgba(0,0,0,0.5), transparent);
                padding: 10px 40px;
                border-radius: 4px;
                animation: fadeIn 0.3s ease;
            }

            .bottom-controls {
                height: 220px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding-bottom: 40px;
            }

            /* --- 修复的核心部分 --- */
            .mic-container {
                position: relative;
                width: 90px; height: 90px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                user-select: none;
                -webkit-tap-highlight-color: transparent;
            }
            
            .mic-inner {
                width: 72px; height: 72px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(8px);
                /* 关键修复：确保 transform 是唯一的动画属性，移除 width/height 的动画影响 */
                transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), background-color 0.3s;
                z-index: 2;
                box-shadow: 0 8px 30px rgba(0,0,0,0.3);
                transform-origin: center center; /* 确保缩放中心点 */
            }
            
            /* 状态：按下 (Pressing) - 缩小 */
            .mic-container:active .mic-inner { 
                transform: scale(0.9) !important;
            }

            /* 状态：录音中 (Recording) - 放大并变红 */
            /* 关键修复：不要改变 width/height，而是使用 scale 放大 */
            .mic-container.active .mic-inner {
                background: #c0392b; 
                border-color: #e74c3c;
                /* 72px * 1.18 ≈ 85px，用 scale 代替 width 变化 */
                transform: scale(1.18); 
            }

            /* 状态：录音中且按下 (Recording + Pressing) - 稍微缩小以反馈点击 */
            .mic-container.active:active .mic-inner {
                transform: scale(1.1) !important;
            }
            /* --- 修复结束 --- */

            .ripple {
                position: absolute;
                top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                width: 100%; height: 100%;
                border-radius: 50%;
                background: rgba(192, 57, 43, 0.4);
                opacity: 0;
                z-index: 1;
            }
            .mic-container.active .ripple { animation: ripple 1.5s infinite; }
            .mic-container.active .ripple:nth-child(2) { animation-delay: 0.4s; }

            .hint-text {
                margin-top: 24px;
                font-size: 14px;
                color: rgba(255,255,255,0.4);
                letter-spacing: 1.5px;
                font-family: sans-serif;
            }

            @keyframes breathe {
                0%, 100% { transform: scale(1); opacity: 0.85; }
                50% { transform: scale(1.03); opacity: 1; }
            }
            @keyframes ripple {
                0% { width: 100%; height: 100%; opacity: 0.6; }
                100% { width: 280%; height: 280%; opacity: 0; }
            }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            @keyframes soundWave {
                0%, 100% { height: 4px; }
                50% { height: 16px; }
            }
        `}</style>

        {/* 1. 顶部导航 */}
        <div className="top-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
             <Button 
               shape="circle" 
               icon={<HomeOutlined />} 
               className="nav-btn" 
               onClick={() => navigate('/')} 
               style={{ marginRight: 8 }}
             />
             <Text strong style={{ fontSize: 18, color: '#d4af37', letterSpacing: 2 }}>数字嘉庚</Text>
          </div>
          <Space>
            <Button shape="circle" icon={<InfoCircleOutlined />} className="nav-btn" onClick={() => setIntroOpen(true)} />
            <Button shape="circle" icon={<SettingOutlined />} className="nav-btn" onClick={() => setSettingsOpen(true)} />
          </Space>
        </div>

        {/* 2. 核心舞台 */}
        <div className={`main-stage ${isProcessing ? 'processing' : ''} ${currentlyPlaying ? 'speaking' : ''}`}>
           <div className="avatar-wrapper">
               <img src={jiagengImg} alt="Chen Jiageng" className="avatar-image" />
           </div>

           <div className="subtitle-overlay">
               {currentSubtitleText ? (
                   <div className="subtitle-text">{currentSubtitleText}</div>
               ) : (
                   isProcessing && (
                       <Space>
                           <LoadingOutlined style={{ fontSize: 20, color: '#d4af37' }} />
                           <Text style={{ color: 'rgba(255,255,255,0.6)', fontStyle: 'italic' }}>思考中...</Text>
                       </Space>
                   )
               )}
           </div>
        </div>

        {/* 3. 底部控制 */}
        <div className="bottom-controls">
            <div 
                className={`mic-container ${isRecording ? 'active' : ''}`}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onTouchStart={startRecording}
                onTouchEnd={stopRecording}
                style={{ 
                    pointerEvents: (isProcessing || currentlyPlaying) ? 'none' : 'auto',
                    opacity: (isProcessing) ? 0.5 : 1 
                }}
            >
                <div className="ripple"></div>
                <div className="ripple"></div>
                <div className="mic-inner">
                    {currentlyPlaying ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 3, height: 24 }}>
                            {[1,2,3,4,3,2,1].map((n, i) => (
                                <div key={i} style={{
                                    width: 3,
                                    background: '#fff',
                                    animation: `soundWave 0.6s infinite ease-in-out ${i * 0.1}s`
                                }} />
                            ))}
                        </div>
                    ) : (
                        <AudioOutlined style={{ fontSize: 28, color: '#fff' }} />
                    )}
                </div>
            </div>

            <div className="hint-text">
                {isRecording 
                    ? `正在聆听... ${recordingTime}s` 
                    : (currentlyPlaying ? '嘉庚先生正在回答' : '长按提问')
                }
            </div>
        </div>

        {/* 4. 侧边栏 */}
        <Drawer
          title="设置"
          placement="right"
          onClose={() => setSettingsOpen(false)}
          open={settingsOpen}
          width={320}
          bodyStyle={{ background: '#141414' }}
          headerStyle={{ background: '#141414', borderBottom: '1px solid #333' }}
        >
           <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                  <Text type="secondary">流式响应</Text>
                  <div style={{ marginTop: 8 }}>
                      <Switch 
                        checked={settings.enableStream} 
                        onChange={v => setSettings(s => ({...s, enableStream: v}))} 
                        checkedChildren="开" unCheckedChildren="关"
                      />
                      <div style={{ marginTop: 4, fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                        开启后，响应会分段实时播放，降低首字延迟
                      </div>
                  </div>
              </div>
              <div>
                  <Text type="secondary">字幕显示</Text>
                  <div style={{ marginTop: 8 }}>
                      <Switch 
                        checked={settings.showSubtitles} 
                        onChange={v => setSettings(s => ({...s, showSubtitles: v}))} 
                        checkedChildren="开" unCheckedChildren="关"
                      />
                  </div>
              </div>
              <div>
                  <Text type="secondary">语速调节</Text>
                  <div style={{ marginTop: 8 }}>
                    <Select
                        value={settings.speakingSpeed}
                        onChange={v => setSettings(s => ({...s, speakingSpeed: v}))}
                        style={{ width: '100%' }}
                        options={[
                            { label: '0.8x (舒缓)', value: 0.8 },
                            { label: '1.0x (原速)', value: 1.0 },
                            { label: '1.2x (稍快)', value: 1.2 },
                        ]}
                    />
                  </div>
              </div>
           </Space>
        </Drawer>

        {/* 5. 介绍弹窗 */}
        <Modal
            open={introOpen}
            footer={null}
            onCancel={() => setIntroOpen(false)}
            centered
            bodyStyle={{ textAlign: 'center', padding: 40 }}
        >
            <Avatar size={80} src={jiagengImg} style={{ marginBottom: 16, border: '2px solid #d4af37' }} />
            <Title level={3} style={{ fontFamily: 'Noto Serif SC', marginBottom: 8 }}>陈嘉庚</Title>
            <Paragraph type="secondary">
                (1874-1961) <br/> 著名爱国华侨领袖、教育家
            </Paragraph>
            <Paragraph>
                您可以尝试用<b>闽南语</b>或<b>普通话</b>与先生对话，询问关于办学理念、抗战历史或人生智慧。
            </Paragraph>
            <Button type="primary" block size="large" onClick={() => setIntroOpen(false)}>开始对话</Button>
        </Modal>

      </div>
    </ConfigProvider>
  )
}

export default DigitalJiagengPage