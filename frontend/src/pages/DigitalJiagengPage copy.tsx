import React, { useState, useRef, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Button, 
  Select, 
  message, 
  Space, 
  Row,
  Col,
  Switch,
  Avatar,
  Tag,
  Divider
} from 'antd'
import { 
  AudioOutlined, 
  UserOutlined,
  HeartOutlined,
  BookOutlined,
  GlobalOutlined
} from '@ant-design/icons'
import { digitalJiagengAPI, LanguageType } from '@/services/api'
import jiagengImg from '@/assets/jiageng.png'
import { useParams } from 'react-router-dom'

const { Title, Paragraph, Text } = Typography

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
}

const DigitalJiagengPage: React.FC = () => {
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null)
  const [currentSubtitleText, setCurrentSubtitleText] = useState<string>('')
  const [recordingTime, setRecordingTime] = useState(0)
  const [sessionId, setSessionId] = useState<string | null>(urlSessionId || null)
  
  // 设置状态
  const [settings, setSettings] = useState<JiagengSettings>({
    enableRolePlay: true,
    inputLanguage: LanguageType.MINNAN,
    outputLanguage: LanguageType.MINNAN,
    voiceGender: 'male',
    speakingSpeed: 1.0,
    showSubtitles: false
  })

  // 录音相关
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recordingChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const recordingTimerRef = useRef<number | null>(null)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const lastSubtitleRef = useRef<string>('')
  // 字幕调试开关与节流
  const DEBUG_SUBS = true
  const lastLogTimeRef = useRef<number>(0)


  // 语言选项（仅展示当前支持项）
  const inputLanguageOptions = [
    { label: '闽南语/普通话', value: LanguageType.MINNAN },
  ]
  const outputLanguageOptions = [
    { label: '闽南语', value: LanguageType.MINNAN },
  ]

  // 生成会话ID
  const generateSessionId = () => {
    return crypto.randomUUID()
  }

  // 初始化会话ID
  useEffect(() => {
    if (urlSessionId) {
      setSessionId(urlSessionId)
      console.log('[DJ-UI] 使用URL中的会话ID:', urlSessionId)
    } else {
      // 如果没有URL参数，生成新的会话ID并重定向
      const newSessionId = generateSessionId()
      setSessionId(newSessionId)
      console.log('[DJ-UI] 生成新会话ID:', newSessionId)
      // 重定向到带会话ID的URL
      window.history.replaceState(null, '', `/digital-jiageng/sessions/${newSessionId}`)
    }
  }, [urlSessionId])

  // 加载会话历史消息
  useEffect(() => {
    const loadHistory = async () => {
      if (!sessionId) return
      
      try {
        const response = await digitalJiagengAPI.getConversationHistory(sessionId)
        if (response.success && response.data?.history) {
          // 转换历史记录为消息格式
          const historyMessages: ChatMessage[] = response.data.history.map((item: any, index: number) => {
            const isUser = item.role === 'user'
            return {
              id: `${sessionId}_${index}_${item.role}`,
              type: isUser ? 'user' : 'jiageng',
              content: item.content || '',
              timestamp: item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
              // 历史消息可能没有音频URL，保留为空
              audioUrl: undefined,
              subtitles: []
            }
          })
          
          setMessages(historyMessages)
          console.log('[DJ-UI] 已加载历史消息:', historyMessages.length)
        }
      } catch (error) {
        console.error('[DJ-UI] 加载历史消息失败:', error)
        // 静默失败，不影响新会话的使用
      }
    }
    
    loadHistory()
  }, [sessionId])

  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      // 清理录音计时器
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
      }
      // 无需清理动画帧与音频上下文
      // 清理音频播放
      if (currentAudioRef.current) {
        currentAudioRef.current.pause()
        currentAudioRef.current = null
      }
    }
  }, [])



  // 初始化录音权限
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

  // 将任意音频 Blob 在浏览器端转换为 16kHz 单声道 WAV，避免后端依赖系统 ffmpeg
  const convertToWav = async (blob: Blob): Promise<Blob> => {
    const arrayBuffer = await blob.arrayBuffer()
    const AudioCtx = (window as any).AudioContext || (window as any).webkitAudioContext
    const audioCtx = new AudioCtx()
    const decoded: AudioBuffer = await new Promise((resolve, reject) => {
      // 复制一份 ArrayBuffer 给 decodeAudioData，避免部分浏览器视为已消耗
      const copy = arrayBuffer.slice(0)
      audioCtx.decodeAudioData(copy, resolve, reject)
    })
    // 释放解码用的 AudioContext，避免资源泄露
    if ((audioCtx as any).close) {
      try { await (audioCtx as any).close() } catch {}
    }
    const targetSampleRate = 16000
    const duration = decoded.duration
    const OfflineCtx = (window as any).OfflineAudioContext || (window as any).webkitOfflineAudioContext
    const offline: OfflineAudioContext = new OfflineCtx(1, Math.ceil(targetSampleRate * duration), targetSampleRate)
    const src = offline.createBufferSource()
    // 合成为单声道
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
    // 写 WAV 头 + PCM16LE 数据
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

  // 基于标点/空格逐句切分字幕：按音频总时长等分
  const generateSubtitles = (rawText: string, durationSec: number) => {
    const text = (rawText || '').trim()
    if (!text) return [] as Array<{ text: string; start_time: number; end_time: number }>

    // 1) 优先：若原句使用空格分隔语块，则直接按空格切分
    const spaceParts = text.split(/\s+/).filter(Boolean)
    let segs: string[] = []
    if (spaceParts.length >= 3) {
      segs = spaceParts
    } else {
      // 2) 其次：按标点切句
      const punctSet = new Set(['，', ',', '。', '.', '！', '!', '？', '?'])
      const sentences: string[] = []
      let buf = ''
      for (const ch of text) {
        buf += ch
        if (punctSet.has(ch)) {
          const seg = buf.trim()
          if (seg) sentences.push(seg)
          buf = ''
        }
      }
      if (buf.trim()) sentences.push(buf.trim())
      segs = sentences.filter(s => s && s.trim())
      // 3) 再次：若仍只有一句，按空格切词（即使只有少量空格也分段）
      if (segs.length <= 1 && spaceParts.length > 1) {
        segs = spaceParts
      }
      // 4) 最后：若仍只有一句，按固定字数切块
      if (segs.length <= 1) {
        const noPunct = stripPunctForDisplay(text)
        const MAX_CHARS = 12
        const tmp: string[] = []
        for (let i = 0; i < noPunct.length; i += MAX_CHARS) {
          tmp.push(noPunct.slice(i, i + MAX_CHARS))
        }
        segs = tmp
      }
    }

    // 显示时去标点
    const displaySegs = segs.map(s => stripPunctForDisplay(s))
    const n = Math.max(1, displaySegs.length)
    const total = (isFinite(durationSec) && durationSec > 0) ? durationSec : n
    const slot = total / n

    const out: Array<{ text: string; start_time: number; end_time: number }> = []
    for (let i = 0; i < n; i++) {
      const start = i * slot
      const end = (i === n - 1) ? total : (i + 1) * slot
      out.push({ text: displaySegs[i] || '', start_time: start, end_time: end })
    }
    if (DEBUG_SUBS) console.debug('[SUB] simple subtitles', out.map(r => ({ t: r.text, s: r.start_time.toFixed(2), e: r.end_time.toFixed(2) })))
    return out
  }

  // 显示用：去除标点符号
  const stripPunctForDisplay = (s: string) =>
    (s || '')
      // 去掉潜在的标签与转义
      .replace(/^\s*(zh|tlp)\s*[:：\\/\-]*\s*/i, '')
      .replace(/\\/g, '')
      .replace(/[，,。\.！!？?、；;：:（）()【】\[\]“”‘’'"…—\-]/g, '')
      .trim()

  // 清洗混合文本：保留中文及常用标点；去除 tlp 行、移除 zh 标签、去掉反斜杠/拉丁字母
  const normalizeZhSource = (raw: string) => {
    let s = (raw || '').replace(/```[\s\S]*?```/g, '')
    // 改写带标签的行：保留 zh 行内容，移除行首 zh: 前缀；删除 tlp 行
    s = s.replace(/(^|\n)\s*zh\s*[:：\\/\-]*\s*/gi, '$1')
    s = s.replace(/(^|\n)\s*tlp\s*[:：\\/\-]*.*(?=\n|$)/gi, '$1')
    // 去掉 JSON 键名
    s = s.replace(/"?(zh|tlp)"?\s*:\s*/gi, '')
    // 去掉反斜杠与拉丁字符（避免把台罗带进来）
    s = s.replace(/\\/g, '')
    s = s.replace(/[A-Za-z0-9\u00C0-\u02AF\u1E00-\u1EFF]/g, '')
    // 仅保留中文与常用标点和空白
    s = s.replace(/[^\u4e00-\u9fff，,。\.！!？?、；;：:\s]/g, '')
    return s.replace(/\s+/g, ' ').trim()
  }

  // 解码音频并计算静音边界（简单能量法）
  const analyzeAudioSilences = async (audioUrl: string) => {
    try {
      const res = await fetch(audioUrl)
      const arr = await res.arrayBuffer()
      const AudioCtx = (window as any).AudioContext || (window as any).webkitAudioContext
      const ctx = new AudioCtx()
      const buf: AudioBuffer = await new Promise((resolve, reject) => {
        ctx.decodeAudioData(arr.slice(0), resolve, reject)
      })
      const channel = buf.getChannelData(0)
      const sampleRate = buf.sampleRate
      const frameMs = 20
      const hopMs = 10
      const frameSize = Math.max(1, Math.floor(sampleRate * (frameMs / 1000)))
      const hopSize = Math.max(1, Math.floor(sampleRate * (hopMs / 1000)))
      const rms: number[] = []
      for (let i = 0; i + frameSize <= channel.length; i += hopSize) {
        let sum = 0
        for (let j = 0; j < frameSize; j++) {
          const s = channel[i + j]
          sum += s * s
        }
        rms.push(Math.sqrt(sum / frameSize))
      }
      // 动态阈值：取35分位作为静音阈值上限（更容易识别静音）
      const sorted = [...rms].sort((a, b) => a - b)
      const q = sorted[Math.floor(sorted.length * 0.35)] || 0.01
      const threshold = Math.max(0.005, Math.min(0.03, q))
      // 语音起点估计：高于阈值一段时间即视为起声
      const minVoiceMs = 120
      const minVoiceFrames = Math.max(1, Math.floor(minVoiceMs / hopMs))
      let voiceRun = 0
      let onsetTime = 0
      let onsetFound = false
      const minSilenceMs = 180
      const minSilenceFrames = Math.max(1, Math.floor(minSilenceMs / hopMs))
      const boundaryTimes: number[] = []
      let run = 0
      for (let idx = 0; idx < rms.length; idx++) {
        // 静音累计
        if (rms[idx] < threshold) run++; else run = 0
        // 起声累计（使用稍高阈值）
        if (!onsetFound) {
          if (rms[idx] >= Math.min(0.08, threshold * 1.6)) {
            voiceRun++
            if (voiceRun >= minVoiceFrames) {
              onsetFound = true
              onsetTime = Math.max(0, ((idx - minVoiceFrames) * hopMs) / 1000)
            }
          } else {
            voiceRun = 0
          }
        }
        if (run === minSilenceFrames) {
          const time = ((idx - Math.floor(minSilenceFrames / 2)) * hopMs) / 1000
          if (time > 0) boundaryTimes.push(time)
        }
      }
      if (DEBUG_SUBS) {
        console.debug('[SUB] analyze', {
          sampleRate,
          frames: rms.length,
          q25: q.toFixed(5),
          threshold: threshold.toFixed(5),
          boundaryTimes: boundaryTimes.map(t => t.toFixed(2)),
          duration: buf.duration.toFixed(2),
          onset: onsetFound ? onsetTime.toFixed(2) : 'n/a'
        })
      }
      // 关闭上下文
      if ((ctx as any).close) {
        try { await (ctx as any).close() } catch {}
      }
      return { boundaryTimes, duration: buf.duration, onsetTime: onsetFound ? onsetTime : 0 }
    } catch (e) {
      if (DEBUG_SUBS) console.debug('[SUB] analyze failed', e)
      return { boundaryTimes: [] as number[], duration: 0, onsetTime: 0 }
    }
  }

  // 根据静音边界拟合句子区间
  const refineSubtitlesWithAudio = async (
    audioUrl: string,
    rawText: string,
    fallback: Array<{ text: string; start_time: number; end_time: number }>
  ) => {
    const { boundaryTimes, duration, onsetTime } = await analyzeAudioSilences(audioUrl)
    // 使用 fallback 的分段数量作为目标，避免因文本异常导致重分段数量偏差
    const n = Math.max(1, fallback.length)
    if (n === 0) return fallback

    // 需要 boundaryTimes 数量=句子数-1 才可直接拟合
    const eps = 0.15
    const bt = boundaryTimes.filter(t => t > eps && t < (duration - eps)).sort((a, b) => a - b)
    const shift = Math.min(Math.max(0, onsetTime), 0.15) // 更保守的全局提前校准
    const qualityOk = duration > 0 && bt.length >= n - 1 && n >= 2
    if (qualityOk) {
      // 取前 N-1 个边界
      const cut = bt.slice(0, n - 1)
      const results: Array<{ text: string; start_time: number; end_time: number }> = []
      let start = 0
      for (let i = 0; i < n; i++) {
        const end = i === n - 1 ? duration : cut[i]
        const adjStart = Math.max(0, start - shift)
        const adjEnd = Math.max(adjStart + 0.2, end - shift)
        results.push({ text: fallback[i]?.text || '', start_time: adjStart, end_time: adjEnd })
        start = end
      }
      // 健壮性检查：时间单调递增、相邻不重叠、最小时长
      const MIN_DUR = 0.25
      let monotonic = true
      for (let i = 0; i < results.length; i++) {
        const seg = results[i]
        if (!(seg.end_time - seg.start_time >= MIN_DUR)) { monotonic = false; break }
        if (i > 0 && !(seg.start_time >= results[i-1].end_time - 1e-3)) { monotonic = false; break }
      }
      if (!monotonic) {
        if (DEBUG_SUBS) console.debug('[SUB] refine rejected by sanity check; fallback used')
        return fallback
      }
      if (DEBUG_SUBS) console.debug('[SUB] refined by audio', results.map(r => ({ t: r.text, s: r.start_time.toFixed(2), e: r.end_time.toFixed(2) })))
      return results
    }
    // 否则回退到原有按字符权重的分配
    if (DEBUG_SUBS) console.debug('[SUB] refine fallback, bt=', bt.length, 'segments=', n)
    if (shift > 0 && n >= 2) {
      const shifted = fallback.map(seg => {
        const ns = Math.max(0, seg.start_time - shift)
        const ne = Math.max(ns + 0.2, seg.end_time - shift)
        return { ...seg, start_time: ns, end_time: ne }
      })
      return shifted
    }
    return fallback
  }

  // 开始录音
  const startRecording = async () => {
    if (isRecording) return // 防止重复开始录音
    
    try {
      const stream = await initAudioContext()
      if (!stream) return

      recordingChunksRef.current = []
      // 选择浏览器支持的音频编码格式（多数浏览器为 webm/opus 或 ogg/opus）
      let preferredMimeType = ''
      if ((window as any).MediaRecorder && (MediaRecorder as any).isTypeSupported) {
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          preferredMimeType = 'audio/webm;codecs=opus'
        } else if (MediaRecorder.isTypeSupported('audio/webm')) {
          preferredMimeType = 'audio/webm'
        } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
          preferredMimeType = 'audio/ogg;codecs=opus'
        }
      }

      mediaRecorderRef.current = new MediaRecorder(
        streamRef.current as MediaStream,
        preferredMimeType ? { mimeType: preferredMimeType } : undefined
      )
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordingChunksRef.current.push(event.data)
        }
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
      setRecordingTime(0)
      
      // 清理可能存在的旧计时器
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
      }
      
      // 录音计时
      recordingTimerRef.current = window.setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

    } catch (error) {
      console.error('录音启动失败:', error)
      message.error('录音启动失败，请重试')
    }
  }

  // 停止录音
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
      }
      
      mediaRecorderRef.current.onstop = async () => {
        try {
          const rawType = mediaRecorderRef.current?.mimeType || 'audio/webm'
          const rawBlob = new Blob(recordingChunksRef.current, { type: rawType })
          const wavBlob = await convertToWav(rawBlob)
          const wavFile = new File([wavBlob], 'recording.wav', { type: 'audio/wav' })
          handleAudioMessage(wavFile)
        } catch (err) {
          console.error('录音转WAV失败，回退原始格式:', err)
          const fallbackBlob = new Blob(recordingChunksRef.current, { type: 'audio/webm' })
          const fallbackFile = new File([fallbackBlob], 'recording.webm', { type: 'audio/webm' })
          handleAudioMessage(fallbackFile)
        }
      }

      // 停止所有音频轨道
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }
    }
  }

  // 处理音频消息（统一使用 File 类型，便于后端读取文件信息）
  const handleAudioMessage = async (audioFile: File) => {
    if (recordingTime < 1) {
      message.warning('录音时间太短，请重新录制')
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
    console.debug('[DJ-UI] start handleAudioMessage, settings.showSubtitles=', settings.showSubtitles)

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
        // 更新会话ID（如果后端返回了新的会话ID）
        if (response.data.session_id && response.data.session_id !== sessionId) {
          setSessionId(response.data.session_id)
          console.log('[DJ-UI] 更新会话ID:', response.data.session_id)
        }

        const jiagengMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'jiageng',
          // 内容不再用于字幕生成，保留为空
          content: '',
          audioUrl: response.data.response_audio_url,
          timestamp: new Date().toLocaleTimeString(),
          // 使用后端返回的字幕
          subtitles: (response.data as any)?.subtitles || []
        }

        setMessages(prev => [...prev, jiagengMessage])
        
        // 自动播放嘉庚的回复
        if (response.data.response_audio_url) {
          const subs = (response.data as any)?.subtitles || []
          console.debug('[DJ-UI] play reply audio, subsLen=', subs.length, subs.slice(0, 2))
          // 无论 settings.showSubtitles 是否为 true，仍然驱动播放与内部 ontime 字幕逻辑
          playAudio(jiagengMessage.id, response.data.response_audio_url, undefined, subs)
        } else {
          // 后端未返回音频：保持文字展示，做温和提示即可，避免被误判为失败
          message.info('本次未生成音频，已显示文字')
        }
      } else {
        message.error(response.message || '对话处理失败')
      }
    } catch (error) {
      console.error('Digital Jiageng Error:', error)
      message.error('对话服务异常，请稍后重试')
    } finally {
      setIsProcessing(false)
    }
  }

  // 播放音频
  const playAudio = (messageId: string, audioUrl: string, contentText?: string, initialSubtitles?: Array<{ text: string; start_time: number; end_time: number }>) => {
    if (currentlyPlaying === messageId) {
      // 停止播放
      if (currentAudioRef.current) {
        currentAudioRef.current.pause()
        currentAudioRef.current = null
      }
      setCurrentlyPlaying(null)
      setCurrentSubtitleText('')
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, isPlaying: false } : msg
      ))
    } else {
      // 开始播放
      setCurrentlyPlaying(messageId)
      setCurrentSubtitleText('')
      lastSubtitleRef.current = ''
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, isPlaying: true } : { ...msg, isPlaying: false }
      ))

      const audio = new Audio(audioUrl)
      currentAudioRef.current = audio

      // 获取消息的字幕数据（优先使用调用方传入，避免 state 竞态）
      const message = messages.find(msg => msg.id === messageId)
      let subtitles = (initialSubtitles && initialSubtitles.length > 0) ? initialSubtitles : (message?.subtitles || [])

      audio.onloadedmetadata = () => {
        console.debug('[DJ-UI] audio metadata loaded, duration=', audio.duration, 'existingSubtitles=', subtitles?.length || 0)
      }
      // 前端不再兜底生成字幕

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
          const now = performance.now()
          if (DEBUG_SUBS && (now - lastLogTimeRef.current) > 200) {
            lastLogTimeRef.current = now
            const idx = subtitles.findIndex(s => s === seg)
            console.debug('[SUB] ontime', {
              t: currentTime.toFixed(2),
              idx,
              seg: seg ? { s: seg.start_time.toFixed(2), e: seg.end_time.toFixed(2), raw, show } : null
            })
          }
        }
      }

      audio.onended = () => {
        setCurrentlyPlaying(null)
        setCurrentSubtitleText('')
        currentAudioRef.current = null
        setMessages(prev => prev.map(msg => 
          msg.id === messageId ? { ...msg, isPlaying: false } : msg
        ))
        console.debug('[DJ-UI] audio ended')
      }

      // 若已有音频在播，先停止
      if (currentAudioRef.current && currentAudioRef.current !== audio) {
        try { currentAudioRef.current.pause() } catch {}
      }
      audio.play()
      console.debug('[DJ-UI] audio.play invoked')
    }
  }





  return (
    <>
      {/* CSS 动画定义 */}
      <style>{`
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.05); }
          100% { transform: scale(1); }
        }
        
        @keyframes waveform {
          0%, 100% { transform: scaleY(1); }
          50% { transform: scaleY(1.5); }
        }
        
        @keyframes thinking {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }

        @keyframes ripple {
          0% { transform: scale(1); opacity: 0.6; }
          70% { transform: scale(1.6); opacity: 0.2; }
          100% { transform: scale(2.2); opacity: 0; }
        }

        @keyframes micGlow {
          0%   { box-shadow: 0 8px 24px rgba(255,77,79,0.15), 0 0 0 0 rgba(255,77,79,0.0); }
          50%  { box-shadow: 0 8px 24px rgba(255,77,79,0.28), 0 0 0 6px rgba(255,77,79,0.18); }
          100% { box-shadow: 0 8px 24px rgba(255,77,79,0.15), 0 0 0 0 rgba(255,77,79,0.0); }
        }
      `}</style>
      
      
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div className="text-center mb-24">
        {/* <Title level={2}>🎭 数字嘉庚</Title> */}
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          与AI嘉庚进行自然对话，体验跨越时空的智慧交流
        </Paragraph>
      </div>

      <Row gutter={[24, 24]}>
        {/* 左侧：设置面板 */}
        <Col xs={24} lg={6}>
          <Card title="对话设置" size="small" className="mb-16">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* 角色扮演开关 */}
              {/* <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text strong>嘉庚扮演</Text>
                  <Switch
                    checked={settings.enableRolePlay}
                    onChange={(checked) => setSettings(prev => ({ 
                      ...prev, 
                      enableRolePlay: checked,
                      // 开启嘉庚扮演模式时自动设置为男声
                      voiceGender: checked ? 'male' : prev.voiceGender
                    }))}
                    checkedChildren="开"
                    unCheckedChildren="关"
                  />
                </div>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {settings.enableRolePlay ? '以陈嘉庚身份对话' : '普通AI助手模式'}
                </Text>
              </div>

              <Divider /> */}

              {/* 语言设置 */}
              <div>
                <Text strong>输入语言</Text>
                <Select
                  value={settings.inputLanguage}
                  onChange={(value) => setSettings(prev => ({ ...prev, inputLanguage: value }))}
                  options={inputLanguageOptions}
                  style={{ width: '100%', marginTop: 4 }}
                  open={false}
                  onClick={() => message.info('暂不支持其他语言')}
                />
              </div>

              <div>
                <Text strong>输出语言</Text>
                <Select
                  value={settings.outputLanguage}
                  onChange={(value) => setSettings(prev => ({ ...prev, outputLanguage: value }))}
                  options={outputLanguageOptions}
                  style={{ width: '100%', marginTop: 4 }}
                  open={false}
                  onClick={() => message.info('暂不支持其他语言')}
                />
              </div>

              <Divider />

              {/* 语音设置 */}
              {!settings.enableRolePlay && (
                <div>
                  <Text strong>语音性别</Text>
                  <Select
                    value={settings.voiceGender}
                    onChange={(value) => setSettings(prev => ({ ...prev, voiceGender: value }))}
                    style={{ width: '100%', marginTop: 4 }}
                    options={[
                      { label: '男声', value: 'male' },
                      { label: '女声', value: 'female' }
                    ]}
                  />
                </div>
              )}

              <div>
                <Text strong>语速: {settings.speakingSpeed}x</Text>
                <div style={{ marginTop: 8 }}>
                  <Button.Group>
                    <Button size="small" onClick={() => setSettings(prev => ({ ...prev, speakingSpeed: 0.5 }))}>0.5x</Button>
                    <Button size="small" onClick={() => setSettings(prev => ({ ...prev, speakingSpeed: 1.0 }))}>1.0x</Button>
                    <Button size="small" onClick={() => setSettings(prev => ({ ...prev, speakingSpeed: 1.5 }))}>1.5x</Button>
                    <Button size="small" onClick={() => setSettings(prev => ({ ...prev, speakingSpeed: 2.0 }))}>2.0x</Button>
                  </Button.Group>
                </div>
              </div>

            </Space>
          </Card>


        </Col>

        {/* 中间：实时对话区域 */}
        <Col xs={24} lg={12}>
          <Card title="语音通话" className="mb-16">
            {/* 通话界面 */}
              <div 
                style={{ 
                height: 520, 
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'flex-start',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: '12px',
                position: 'relative',
                padding: '40px 20px'
              }}
            >
              {/* 顶部：头像固定区（固定高度，避免位移） */}
              <div style={{ height: 260, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                <div style={{ position: 'relative', display: 'inline-block', transform: 'translateZ(0)' }}>
                  <Avatar 
                    size={120} 
                    icon={<UserOutlined />} 
                    style={{ 
                      backgroundColor: '#ffffff',
                      color: '#1890ff',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.2)'
                    }} 
                  />
                </div>
                <div style={{ marginTop: '16px' }}>
                  <Text style={{ color: '#ffffff', fontSize: '18px', fontWeight: 'bold' }}>
                    {settings.enableRolePlay ? '陈嘉庚先生' : 'AI助手'}
                  </Text>
                </div>
              </div>

              {/* 下部：状态/操作区（固定高度，避免位移） */}
              <div style={{ height: 180, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                {/* 思考 */}
                {isProcessing && (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ 
                      display: 'flex', justifyContent: 'center', alignItems: 'center',
                      height: '60px', gap: '8px', marginBottom: '12px'
                    }}>
                      {[...Array(3)].map((_, i) => (
                        <div key={i} style={{ width: '12px', height: '12px', backgroundColor: '#ffffff', borderRadius: '50%', animation: 'thinking 1.4s ease-in-out infinite both', animationDelay: `${i * 0.16}s` }} />
                      ))}
                    </div>

                  </div>
                )}

                {/* 录音状态不在此处显示可视化 */}

                {/* 播放动效 */}
                {currentlyPlaying && !isRecording && (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-end', height: '60px', gap: '4px', marginBottom: '12px' }}>
                      {[...Array(10)].map((_, i) => (
                        <div key={i} style={{ width: '6px', height: `${12 + (i % 3) * 8}px`, backgroundColor: '#ffffff', borderRadius: '3px', animation: 'waveform 1s ease-in-out infinite', animationDelay: `${i * 0.08}s`, opacity: 0.85 }} />
                      ))}
                    </div>
                  </div>
                )}

                {/* 操作按钮：仅空闲或录音时显示 */}
                {!currentlyPlaying && !isProcessing && (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Button
                        type="primary" size="large" shape="circle" icon={<AudioOutlined />}
                        onMouseDown={startRecording} onMouseUp={stopRecording}
                        onTouchStart={startRecording} onTouchEnd={stopRecording}
                        disabled={isProcessing}
                        style={{
                          width: '100px', height: '100px', fontSize: '32px',
                          backgroundColor: '#ffffff',
                          borderColor: isRecording ? '#ff4d4f' : '#ffffff',
                          color: isRecording ? '#ff4d4f' : '#667eea',
                          transition: 'all 0.2s ease',
                          boxShadow: '0 8px 24px rgba(0,0,0,0.15)'
                        }}
                      />
                    </div>
                    <div style={{ marginTop: 12 }}>
                      <Text style={{ color: '#ffffff', fontSize: 14, opacity: 0.9 }}>
                        {isRecording ? `录音中 ${recordingTime}s` : '按住说话'}
                      </Text>
                    </div>
                  </>
                )}
              </div>

              {/* 字幕浮层（播放时显示） */}
              {(() => {
                if (settings.showSubtitles && currentlyPlaying && currentSubtitleText) {
                  console.debug('[DJ-UI] render subtitle overlay:', currentSubtitleText)
                  return (
                    <div
                      style={{
                        position: 'absolute',
                        bottom: 18,
                        left: '50%',
                        transform: 'translateX(-50%)',
                        background: 'rgba(0,0,0,0.45)',
                        padding: '10px 16px',
                        borderRadius: 18,
                        border: '1px solid rgba(255,255,255,0.12)',
                        maxWidth: '88%',
                        zIndex: 5,
                        pointerEvents: 'none'
                      }}
                    >
                      <Text style={{ color: '#fff', fontSize: 14, lineHeight: 1.4 }}>{currentSubtitleText}</Text>
                    </div>
                  )
                }
                // 无字幕时不再显示占位，避免“过早结束”的视觉误判
                return null
              })()}

              {/* 字幕开关 */}
              <div 
                style={{ 
                  position: 'absolute', 
                  top: '16px', 
                  right: '16px',
                  background: 'rgba(255,255,255,0.2)',
                  borderRadius: '20px',
                  padding: '8px 12px'
                }}
              >
                <Space>
                  <Text style={{ color: '#ffffff', fontSize: '12px' }}>字幕</Text>
                  <Switch
                    size="small"
                    checked={settings.showSubtitles}
                    onChange={(checked) => setSettings(prev => ({ ...prev, showSubtitles: checked }))}
                  />
                </Space>
              </div>
            </div>

            {/* 移除页面下方字幕组件，仅保留浮层 */}
          </Card>
        </Col>

        {/* 右侧：状态信息 */}
        <Col xs={24} lg={6}>
          {/* 嘉庚介绍 */}
          {settings.enableRolePlay && (
            <Card title="陈嘉庚先生" size="small" className="mb-16">
              <div className="text-center mb-12">
                <Avatar size={80} src={jiagengImg} />
              </div>
              <Paragraph style={{ fontSize: '12px', textAlign: 'center' }}>
                <Text strong>陈嘉庚 (1874-1961)</Text><br />
                著名华侨领袖、企业家、教育家。倾资兴学，创办厦门大学和集美学校，被誉为"华侨旗帜、民族光辉"。
              </Paragraph>
              <div className="text-center">
                <Tag icon={<BookOutlined />} color="blue">教育家</Tag>
                <Tag icon={<GlobalOutlined />} color="green">华侨领袖</Tag>
                <Tag icon={<HeartOutlined />} color="red">爱国者</Tag>
              </div>
            </Card>
          )}

          <Card title="对话统计" size="small" className="mb-16">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>对话轮次:</Text>
                <Text strong>{messages.filter(m => m.type === 'user').length}</Text>
              </div>
            </Space>
          </Card>

          <Card title="使用提示" size="small">
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8', fontSize: '12px' }}>
              <li>按住录音按钮开始说话</li>
              <li>松开按钮结束录音并发送</li>
              <li>录音时长建议1-30秒</li>
              <li>嘉庚会自动播放语音回复</li>
              <li>可在设置中调整语言和语音</li>
              <li>开启扮演模式体验历史对话</li>
            </ul>
          </Card>
        </Col>
      </Row>

      {/* 功能说明
      <Card title="数字嘉庚功能介绍" className="mt-24">
        <Row gutter={[24, 24]}>
          <Col xs={24} md={8}>
            <Title level={4}>🎭 角色扮演</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>AI扮演陈嘉庚先生身份</li>
              <li>还原历史人物的思想理念</li>
              <li>体验跨越时空的对话</li>
              <li>学习教育家的智慧思想</li>
            </ul>
          </Col>
          <Col xs={24} md={8}>
            <Title level={4}>🎤 语音交互</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>按住录音，自然语音输入</li>
              <li>支持多种方言语音识别</li>
              <li>智能语音合成回复</li>
              <li>实时字幕同步显示</li>
            </ul>
          </Col>
          <Col xs={24} md={8}>
            <Title level={4}>⚙️ 智能设置</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>自由切换普通AI模式</li>
              <li>多语言输入输出设置</li>
              <li>语速调节和语音设置</li>
              <li>对话历史管理功能</li>
            </ul>
          </Col>
        </Row>
      </Card> */}
    </div>
    </>
  )
}

export default DigitalJiagengPage 