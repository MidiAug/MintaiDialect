import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 语言类型枚举
export enum LanguageType {
  MANDARIN = 'mandarin',
  MINNAN = 'minnan',
  HAKKA = 'hakka',
  TAIWANESE = 'taiwanese',
}

// 音频格式枚举
export enum AudioFormat {
  WAV = 'wav',
  MP3 = 'mp3',
  FLAC = 'flac',
  M4A = 'm4a',
  OGG = 'ogg',
}

// API响应格式
export interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
  timestamp?: string
}

// Mock API调用函数（用于开发和测试）
const mockApiCall = <T>(data: T, delay: number = 1000): Promise<ApiResponse<T>> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        success: true,
        message: '操作成功',
        data,
        timestamp: new Date().toISOString()
      })
    }, delay)
  })
}

// ============ ASR/TTS API ============

export interface ASRRequest {
  audio_file: File
  source_language?: LanguageType
  enable_timestamps?: boolean
  enable_word_level?: boolean
}

export interface TTSRequest {
  text: string
  target_language?: LanguageType
  voice_style?: string
  speed?: number
  pitch?: number
  audio_format?: AudioFormat
}

export const asrTtsAPI = {
  // 语音识别
  speechToText: (data: ASRRequest) => {
    const formData = new FormData()
    formData.append('audio_file', data.audio_file)
    formData.append('source_language', data.source_language || LanguageType.MINNAN)
    formData.append('enable_timestamps', String(data.enable_timestamps || false))
    formData.append('enable_word_level', String(data.enable_word_level || false))
    
    return api.post('/asr-tts/asr', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 文本转语音
  textToSpeech: (data: TTSRequest) => {
    return api.post('/asr-tts/tts', data)
  },

  // 批量语音识别
  batchSpeechToText: (files: File[], sourceLanguage?: LanguageType) => {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('audio_files', file)
    })
    formData.append('source_language', sourceLanguage || LanguageType.MINNAN)
    
    return api.post('/asr-tts/batch-asr', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 音频质量检测
  checkAudioQuality: (file: File) => {
    const formData = new FormData()
    formData.append('audio_file', file)
    
    return api.post('/asr-tts/audio-quality', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ============ 语音翻译 API ============

export interface SpeechTranslationRequest {
  audio_file: File
  source_language: LanguageType
  target_language: LanguageType
  return_audio?: boolean
  return_text?: boolean
}

export const speechTranslationAPI = {
  // 语音翻译
  translateSpeech: (data: SpeechTranslationRequest) => {
    const formData = new FormData()
    formData.append('audio_file', data.audio_file)
    formData.append('source_language', data.source_language)
    formData.append('target_language', data.target_language)
    formData.append('return_audio', String(data.return_audio !== false))
    formData.append('return_text', String(data.return_text !== false))
    
    return api.post('/speech-translation/translate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 语言检测
  detectLanguage: (file: File) => {
    const formData = new FormData()
    formData.append('audio_file', file)
    
    return api.post('/speech-translation/detect-language', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 获取支持的语言对
  getSupportedPairs: () => {
    return api.get('/speech-translation/supported-pairs')
  },
}

// ============ 语音交互 API ============

export interface VoiceInteractionRequest {
  audio_file?: File
  text_input?: string
  conversation_id?: string
  user_language?: LanguageType
  response_language?: LanguageType
  response_mode?: 'text' | 'audio' | 'both'
}

export const voiceInteractionAPI = {
  // 语音对话
  voiceChat: (data: VoiceInteractionRequest) => {
    const formData = new FormData()
    
    if (data.audio_file) {
      formData.append('audio_file', data.audio_file)
    }
    if (data.text_input) {
      formData.append('text_input', data.text_input)
    }
    if (data.conversation_id) {
      formData.append('conversation_id', data.conversation_id)
    }
    
    formData.append('user_language', data.user_language || LanguageType.MINNAN)
    formData.append('response_language', data.response_language || LanguageType.MINNAN)
    formData.append('response_mode', data.response_mode || 'both')
    
    return api.post('/voice-interaction/chat', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 方言问答
  dialectQA: (question: string, questionLanguage?: LanguageType, answerLanguage?: LanguageType, returnAudio?: boolean) => {
    const formData = new FormData()
    formData.append('question', question)
    formData.append('question_language', questionLanguage || LanguageType.MINNAN)
    formData.append('answer_language', answerLanguage || LanguageType.MINNAN)
    formData.append('return_audio', String(returnAudio || false))
    
    return api.post('/voice-interaction/qa', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 获取对话历史
  getConversationHistory: (conversationId: string) => {
    return api.get(`/voice-interaction/conversations/${conversationId}`)
  },

  // 删除对话历史
  deleteConversation: (conversationId: string) => {
    return api.delete(`/voice-interaction/conversations/${conversationId}`)
  },

  // 语音情感分析
  analyzeEmotion: (file: File, language?: LanguageType) => {
    const formData = new FormData()
    formData.append('audio_file', file)
    formData.append('language', language || LanguageType.MINNAN)
    
    return api.post('/voice-interaction/emotion-analysis', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ============ 音色克隆 API ============

export interface VoiceCloningRequest {
  reference_audio: File
  target_text?: string
  target_audio?: File
  language?: LanguageType
  quality?: 'low' | 'medium' | 'high'
  preserve_emotion?: boolean
  voice_speed?: number
  voice_pitch?: number
}

export const voiceCloningAPI = {
  // 文本驱动音色克隆
  textDrivenCloning: (data: VoiceCloningRequest) => {
    const formData = new FormData()
    formData.append('reference_audio', data.reference_audio)
    
    if (data.target_text) {
      formData.append('target_text', data.target_text)
    }
    
    formData.append('language', data.language || LanguageType.MINNAN)
    formData.append('quality', data.quality || 'high')
    formData.append('preserve_emotion', String(data.preserve_emotion !== false))
    formData.append('voice_speed', String(data.voice_speed || 1.0))
    formData.append('voice_pitch', String(data.voice_pitch || 1.0))
    
    return api.post('/voice-cloning/text-driven', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 音频驱动音色克隆
  audioDrivenCloning: (referenceAudio: File, targetAudio: File, options?: {
    quality?: 'low' | 'medium' | 'high'
    preserveContent?: boolean
    preserveEmotion?: boolean
    blendRatio?: number
  }) => {
    const formData = new FormData()
    formData.append('reference_audio', referenceAudio)
    formData.append('target_audio', targetAudio)
    formData.append('quality', options?.quality || 'high')
    formData.append('preserve_content', String(options?.preserveContent !== false))
    formData.append('preserve_emotion', String(options?.preserveEmotion !== false))
    formData.append('blend_ratio', String(options?.blendRatio || 0.8))
    
    return api.post('/voice-cloning/audio-driven', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 音色相似度分析
  analyzeSimilarity: (audio1: File, audio2: File, analysisType?: 'basic' | 'comprehensive') => {
    const formData = new FormData()
    formData.append('audio1', audio1)
    formData.append('audio2', audio2)
    formData.append('analysis_type', analysisType || 'comprehensive')
    
    return api.post('/voice-cloning/similarity-analysis', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 音色特征提取
  extractFeatures: (file: File, featureType?: 'basic' | 'advanced' | 'all') => {
    const formData = new FormData()
    formData.append('audio_file', file)
    formData.append('feature_type', featureType || 'all')
    
    return api.post('/voice-cloning/extract-features', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ============ 系统 API ============

export const systemAPI = {
  // 健康检查
  healthCheck: () => {
    return api.get('/health')
  },

  // 获取系统信息
  getSystemInfo: () => {
    return api.get('/info')
  },
}

// 数字嘉庚相关接口
export interface DigitalJiagengChatRequest {
  audio_file?: File
  text_input?: string
  settings: {
    enable_role_play: boolean
    input_language: LanguageType
    output_language: LanguageType
    voice_gender: 'male' | 'female'
    speaking_speed: number
    show_subtitles: boolean
  }
}

export interface DigitalJiagengChatResponse {
  response_text: string
  response_audio_url?: string
  emotion: string
  confidence: number
  processing_time: number
  subtitle_text?: string
  subtitles: Array<{
    text: string
    start_time: number  // 开始时间(秒)
    end_time: number    // 结束时间(秒)
  }>
}

// 数字嘉庚API
export const digitalJiagengAPI = {
  // 与嘉庚对话（真实后端）
  chatWithJiageng: async (data: DigitalJiagengChatRequest): Promise<ApiResponse<DigitalJiagengChatResponse>> => {
    const formData = new FormData()
    if (data.audio_file) formData.append('audio_file', data.audio_file)
    if (data.text_input) formData.append('text_input', data.text_input)
    formData.append('enable_role_play', String(data.settings.enable_role_play))
    formData.append('input_language', data.settings.input_language)
    formData.append('output_language', data.settings.output_language)
    formData.append('voice_gender', data.settings.voice_gender)
    formData.append('speaking_speed', String(data.settings.speaking_speed))
    formData.append('show_subtitles', String(data.settings.show_subtitles))

    return api.post('/digital-jiageng/chat', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 获取嘉庚信息（真实后端）
  getJiagengInfo: async (): Promise<ApiResponse<any>> => {
    return api.get('/digital-jiageng/info')
  }
}

export default api 