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
  Progress,
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
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null)
  const [currentSubtitleText, setCurrentSubtitleText] = useState<string>('')
  const [audioCurrentTime, setAudioCurrentTime] = useState<number>(0)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  
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
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)


  // 语言选项
  const languageOptions = [
    { label: '闽南话', value: LanguageType.MINNAN },
    { label: '客家话', value: LanguageType.HAKKA },
    { label: '台湾话', value: LanguageType.TAIWANESE },
    { label: '普通话', value: LanguageType.MANDARIN },
  ]

  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      // 清理录音计时器
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
      }
      // 清理动画帧
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      // 清理音频上下文
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
      // 清理音频播放
      if (currentAudioRef.current) {
        currentAudioRef.current.pause()
        currentAudioRef.current = null
      }
    }
  }, [])



  // 初始化音频上下文
  const initAudioContext = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      
      analyserRef.current.fftSize = 256
      const bufferLength = analyserRef.current.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)
      
      const updateAudioLevel = () => {
        if (analyserRef.current && isRecording) {
          analyserRef.current.getByteFrequencyData(dataArray)
          const average = dataArray.reduce((a, b) => a + b) / bufferLength
          setAudioLevel(average)
          animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
        }
      }
      
      if (isRecording) {
        updateAudioLevel()
      }
      
      return stream
    } catch (error) {
      console.error('音频权限获取失败:', error)
      message.error('无法获取麦克风权限，请检查浏览器设置')
      return null
    }
  }

  // 开始录音
  const startRecording = async () => {
    if (isRecording) return // 防止重复开始录音
    
    try {
      const stream = await initAudioContext()
      if (!stream) return

      recordingChunksRef.current = []
      mediaRecorderRef.current = new MediaRecorder(stream)
      
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
      recordingTimerRef.current = setInterval(() => {
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
      setAudioLevel(0)
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
      }
      
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(recordingChunksRef.current, { type: 'audio/wav' })
        handleAudioMessage(audioBlob)
      }

      // 停止所有音频轨道
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }

  // 处理音频消息
  const handleAudioMessage = async (audioBlob: Blob) => {
    if (recordingTime < 1) {
      message.warning('录音时间太短，请重新录制')
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: '[语音消息]',
      audioUrl: URL.createObjectURL(audioBlob),
      audioBlob,
      timestamp: new Date().toLocaleTimeString()
    }

    setMessages(prev => [...prev, userMessage])
    setIsProcessing(true)

    try {
      const response = await digitalJiagengAPI.chatWithJiageng({
        audio_file: audioBlob,
        settings: {
          enable_role_play: settings.enableRolePlay,
          input_language: settings.inputLanguage,
          output_language: settings.outputLanguage,
          voice_gender: settings.voiceGender,
          speaking_speed: settings.speakingSpeed
        }
      })

      if (response.success) {
        const jiagengMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'jiageng',
          content: response.data.response_text,
          audioUrl: response.data.response_audio_url,
          timestamp: new Date().toLocaleTimeString(),
          subtitles: response.data.subtitles
        }

        setMessages(prev => [...prev, jiagengMessage])
        
        // 自动播放嘉庚的回复
        if (response.data.response_audio_url) {
          playAudio(jiagengMessage.id, response.data.response_audio_url)
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
  const playAudio = (messageId: string, audioUrl: string) => {
    if (currentlyPlaying === messageId) {
      // 停止播放
      if (currentAudioRef.current) {
        currentAudioRef.current.pause()
        currentAudioRef.current = null
      }
      setCurrentlyPlaying(null)
      setCurrentSubtitleText('')
      setAudioCurrentTime(0)
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, isPlaying: false } : msg
      ))
    } else {
      // 开始播放
      setCurrentlyPlaying(messageId)
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, isPlaying: true } : { ...msg, isPlaying: false }
      ))

      const audio = new Audio(audioUrl)
      currentAudioRef.current = audio

      // 获取消息的字幕数据
      const message = messages.find(msg => msg.id === messageId)
      const subtitles = message?.subtitles || []

      // 监听播放时间更新
      audio.ontimeupdate = () => {
        const currentTime = audio.currentTime
        setAudioCurrentTime(currentTime)
        
        // 根据当前时间找到对应的字幕
        const currentSubtitle = subtitles.find(
          subtitle => currentTime >= subtitle.start_time && currentTime <= subtitle.end_time
        )
        
        setCurrentSubtitleText(currentSubtitle?.text || '')
      }

      audio.onended = () => {
        setCurrentlyPlaying(null)
        setCurrentSubtitleText('')
        setAudioCurrentTime(0)
        currentAudioRef.current = null
        setMessages(prev => prev.map(msg => 
          msg.id === messageId ? { ...msg, isPlaying: false } : msg
        ))
      }

      audio.play()
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
      `}</style>
      
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div className="text-center mb-24">
        <Title level={2}>🎭 数字嘉庚</Title>
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
              <div>
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

              <Divider />

              {/* 语言设置 */}
              <div>
                <Text strong>输入语言</Text>
                <Select
                  value={settings.inputLanguage}
                  onChange={(value) => setSettings(prev => ({ ...prev, inputLanguage: value }))}
                  options={languageOptions}
                  style={{ width: '100%', marginTop: 4 }}
                />
              </div>

              <div>
                <Text strong>输出语言</Text>
                <Select
                  value={settings.outputLanguage}
                  onChange={(value) => setSettings(prev => ({ ...prev, outputLanguage: value }))}
                  options={languageOptions}
                  style={{ width: '100%', marginTop: 4 }}
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
                    <Button size="small" onClick={() => setSettings(prev => ({ ...prev, speakingSpeed: 0.8 }))}>慢</Button>
                    <Button size="small" onClick={() => setSettings(prev => ({ ...prev, speakingSpeed: 1.0 }))}>正常</Button>
                    <Button size="small" onClick={() => setSettings(prev => ({ ...prev, speakingSpeed: 1.2 }))}>快</Button>
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
                height: 500, 
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: '12px',
                position: 'relative',
                padding: '40px 20px'
              }}
            >
              {/* 嘉庚头像 */}
              <div style={{ marginBottom: '40px', textAlign: 'center' }}>
                <Avatar 
                  size={120} 
                  icon={<UserOutlined />} 
                  style={{ 
                    backgroundColor: '#ffffff',
                    color: '#1890ff',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.2)'
                  }} 
                />
                <div style={{ marginTop: '16px' }}>
                  <Text style={{ color: '#ffffff', fontSize: '18px', fontWeight: 'bold' }}>
                    {settings.enableRolePlay ? '陈嘉庚先生' : 'AI助手'}
                  </Text>
                </div>
              </div>

              {/* 状态显示区域 */}
              <div style={{ minHeight: '80px', textAlign: 'center', marginBottom: '40px' }}>
                {isProcessing && (
                  <div>
                    {/* 思考动画 */}
                    <div style={{ 
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      height: '60px',
                      gap: '8px',
                      marginBottom: '12px'
                    }}>
                      {[...Array(3)].map((_, i) => (
                        <div
                          key={i}
                          style={{
                            width: '12px',
                            height: '12px',
                            backgroundColor: '#ffffff',
                            borderRadius: '50%',
                            animation: 'thinking 1.4s ease-in-out infinite both',
                            animationDelay: `${i * 0.16}s`
                          }}
                        />
                      ))}
                    </div>
                    <div style={{ marginTop: '12px' }}>
                      <Text style={{ color: '#ffffff', fontSize: '16px' }}>
                        {settings.enableRolePlay ? '嘉庚正在思考...' : 'AI正在处理...'}
                      </Text>
                    </div>
                  </div>
                )}

                {isRecording && (
                  <div>
                    {/* 声波可视化 */}
                    <div style={{ 
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'flex-end',
                      height: '60px',
                      gap: '4px',
                      marginBottom: '16px'
                    }}>
                      {[...Array(8)].map((_, i) => (
                        <div
                          key={i}
                          style={{
                            width: '6px',
                            height: `${Math.max(8, (audioLevel / 255) * 60 + Math.sin(Date.now() / 100 + i) * 10)}px`,
                            backgroundColor: '#ffffff',
                            borderRadius: '3px',
                            animation: 'waveform 0.8s ease-in-out infinite',
                            animationDelay: `${i * 0.1}s`,
                            opacity: 0.7 + (audioLevel / 255) * 0.3
                          }}
                        />
                      ))}
                    </div>
                    <Text style={{ color: '#ffffff', fontSize: '16px', fontWeight: '500' }}>
                      录音中 {recordingTime}s
                    </Text>
                  </div>
                )}

                {!isProcessing && !isRecording && (
                  <div>
                    <Text style={{ color: '#ffffff', fontSize: '16px' }}>
                      你可以开始说话
                    </Text>
                  </div>
                )}
              </div>

              {/* 录音按钮 */}
              <Button
                type="primary"
                size="large"
                shape="circle"
                icon={<AudioOutlined />}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onTouchStart={startRecording}
                onTouchEnd={stopRecording}
                disabled={isProcessing}
                style={{
                  width: '100px',
                  height: '100px',
                  fontSize: '32px',
                  backgroundColor: '#ffffff',
                  borderColor: '#ffffff',
                  color: '#667eea',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
                  ...(isRecording ? {
                    transform: 'scale(1.1)',
                    backgroundColor: '#ff4d4f',
                    borderColor: '#ff4d4f',
                    color: '#ffffff',
                    boxShadow: `0 0 ${audioLevel / 5}px rgba(255,77,79,0.8)`
                  } : {})
                }}
              />
              
              <div style={{ marginTop: '16px' }}>
                <Text style={{ color: '#ffffff', fontSize: '14px' }}>
                  {isRecording ? '松开结束录音' : '按住说话'}
                </Text>
              </div>

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

            {/* 实时字幕显示区域 */}
            {settings.showSubtitles && (
              <div 
                style={{ 
                  marginTop: '16px',
                  padding: '0',
                  minHeight: '80px',
                  textAlign: 'center',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {currentlyPlaying && currentSubtitleText ? (
                  <div
                    style={{
                      background: 'linear-gradient(135deg, rgba(0,0,0,0.8) 0%, rgba(40,40,40,0.8) 100%)',
                      padding: '12px 20px',
                      borderRadius: '25px',
                      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      backdropFilter: 'blur(10px)',
                      maxWidth: '90%',
                      minHeight: '50px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    <Text 
                      style={{ 
                        color: '#ffffff', 
                        fontSize: '16px',
                        fontWeight: '400',
                        lineHeight: '1.4',
                        textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                        textAlign: 'center'
                      }}
                    >
                      {currentSubtitleText}
                    </Text>
                  </div>
                ) : isProcessing ? (
                  <div
                    style={{
                      background: 'rgba(108, 117, 125, 0.3)',
                      padding: '10px 16px',
                      borderRadius: '20px',
                      border: '1px solid rgba(255,255,255,0.1)'
                    }}
                  >
                    <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: '14px' }}>
                      💭 {settings.enableRolePlay ? '嘉庚正在思考回复...' : 'AI正在思考回复...'}
                    </Text>
                  </div>
                ) : (
                  <div
                    style={{
                      background: 'rgba(108, 117, 125, 0.2)',
                      padding: '8px 16px',
                      borderRadius: '16px',
                      border: '1px dashed rgba(255,255,255,0.2)'
                    }}
                  >
                    <Text style={{ color: 'rgba(100,100,100,0.8)', fontSize: '13px' }}>
                      💬 字幕将在AI语音播放时显示
                    </Text>
                  </div>
                )}
              </div>
            )}
          </Card>
        </Col>

        {/* 右侧：状态信息 */}
        <Col xs={24} lg={6}>
          {/* 嘉庚介绍 */}
          {settings.enableRolePlay && (
            <Card title="陈嘉庚先生" size="small" className="mb-16">
              <div className="text-center mb-12">
                <Avatar size={80} icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
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
                <Text strong>{Math.floor(messages.length / 2)}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>我的发言:</Text>
                <Text>{messages.filter(m => m.type === 'user').length}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>嘉庚回复:</Text>
                <Text>{messages.filter(m => m.type === 'jiageng').length}</Text>
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

      {/* 功能说明 */}
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
      </Card>
    </div>
    </>
  )
}

export default DigitalJiagengPage 