import React, { useState, useRef, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Button, 
  Input, 
  message, 
  Space, 
  Divider,
  Row,
  Col,
  Select,
  Upload,
  List,
  Avatar,
  Tag,
  Alert,
  Switch,
  Tooltip,
  Empty
} from 'antd'
import { 
  MessageOutlined, 
  AudioOutlined, 
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  ClearOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  MicrophoneIcon,
  DownloadOutlined,
  DeleteOutlined,
  HeartOutlined
} from '@ant-design/icons'
import { voiceInteractionAPI, LanguageType } from '@/services/api'

const { Title, Paragraph, Text } = Typography
const { TextArea } = Input

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  audioUrl?: string
  timestamp: string
  emotion?: string
  intent?: string
}

interface ConversationHistory {
  conversation_id: string
  history: any[]
  total_turns: number
  created_at: string
  last_updated: string
}

const VoiceInteractionPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [textInput, setTextInput] = useState('')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [conversationId, setConversationId] = useState<string>('')
  const [userLanguage, setUserLanguage] = useState<LanguageType>(LanguageType.MINNAN)
  const [responseLanguage, setResponseLanguage] = useState<LanguageType>(LanguageType.MINNAN)
  const [responseMode, setResponseMode] = useState<'text' | 'audio' | 'both'>('both')
  const [conversations, setConversations] = useState<ConversationHistory[]>([])
  const [recording, setRecording] = useState(false)
  const [currentTab, setCurrentTab] = useState<'chat' | 'qa'>('chat')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 语言选项
  const languageOptions = [
    { label: '闽南话', value: LanguageType.MINNAN },
    { label: '客家话', value: LanguageType.HAKKA },
    { label: '台湾话', value: LanguageType.TAIWANESE },
    { label: '普通话', value: LanguageType.MANDARIN },
  ]

  // 滚动到消息底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    // 只有当有消息时才滚动到底部，避免页面初始加载时滚动
    if (messages.length > 0) {
      scrollToBottom()
    }
  }, [messages])

  // 发送文本消息
  const sendTextMessage = async () => {
    if (!textInput.trim()) {
      message.warning('请输入消息内容')
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: textInput,
      timestamp: new Date().toLocaleTimeString()
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    try {
      const response = await voiceInteractionAPI.voiceChat({
        text_input: textInput,
        conversation_id: conversationId || undefined,
        user_language: userLanguage,
        response_language: responseLanguage,
        response_mode: responseMode
      })

      if (response.success) {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: response.data.response_text,
          audioUrl: response.data.response_audio_url,
          timestamp: new Date().toLocaleTimeString(),
          emotion: response.data.emotion,
          intent: response.data.intent
        }

        setMessages(prev => [...prev, assistantMessage])
        
        // 更新对话ID
        if (!conversationId) {
          setConversationId(response.data.conversation_id)
        }
        
        message.success('对话回复完成！')
      } else {
        message.error(response.message || '对话处理失败')
      }
    } catch (error) {
      console.error('Chat Error:', error)
      message.error('对话服务异常，请稍后重试')
    } finally {
      setLoading(false)
      setTextInput('')
    }
  }

  // 发送语音消息
  const sendAudioMessage = async () => {
    if (!audioFile) {
      message.warning('请先录制或上传音频')
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: '[语音消息]',
      audioUrl: URL.createObjectURL(audioFile),
      timestamp: new Date().toLocaleTimeString()
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    try {
      const response = await voiceInteractionAPI.voiceChat({
        audio_file: audioFile,
        conversation_id: conversationId || undefined,
        user_language: userLanguage,
        response_language: responseLanguage,
        response_mode: responseMode
      })

      if (response.success) {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: response.data.response_text,
          audioUrl: response.data.response_audio_url,
          timestamp: new Date().toLocaleTimeString(),
          emotion: response.data.emotion,
          intent: response.data.intent
        }

        setMessages(prev => [...prev, assistantMessage])
        
        if (!conversationId) {
          setConversationId(response.data.conversation_id)
        }
        
        message.success('语音对话完成！')
      } else {
        message.error(response.message || '语音对话失败')
      }
    } catch (error) {
      console.error('Voice Chat Error:', error)
      message.error('语音对话服务异常，请稍后重试')
    } finally {
      setLoading(false)
      setAudioFile(null)
    }
  }

  // 方言问答
  const handleDialectQA = async () => {
    if (!textInput.trim()) {
      message.warning('请输入问题')
      return
    }

    setLoading(true)
    try {
      const response = await voiceInteractionAPI.dialectQA(
        textInput,
        userLanguage,
        responseLanguage,
        responseMode === 'audio' || responseMode === 'both'
      )

      if (response.success) {
        const questionMessage: ChatMessage = {
          id: Date.now().toString(),
          type: 'user',
          content: textInput,
          timestamp: new Date().toLocaleTimeString()
        }

        const answerMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: response.data.answer,
          audioUrl: response.data.answer_audio_url,
          timestamp: new Date().toLocaleTimeString()
        }

        setMessages(prev => [...prev, questionMessage, answerMessage])
        message.success('问答完成！')
      } else {
        message.error(response.message || '问答处理失败')
      }
    } catch (error) {
      console.error('QA Error:', error)
      message.error('问答服务异常，请稍后重试')
    } finally {
      setLoading(false)
      setTextInput('')
    }
  }

  // 清空对话
  const clearConversation = () => {
    setMessages([])
    setConversationId('')
    message.success('对话已清空')
  }

  // 获取对话历史
  const loadConversationHistory = async (convId: string) => {
    try {
      const response = await voiceInteractionAPI.getConversationHistory(convId)
      if (response.success) {
        // 转换历史记录为消息格式
        const history = response.data.history.map((item: any, index: number) => ([
          {
            id: `${index}_user`,
            type: 'user' as const,
            content: item.user,
            timestamp: new Date(item.timestamp).toLocaleTimeString()
          },
          {
            id: `${index}_assistant`,
            type: 'assistant' as const,
            content: item.assistant,
            timestamp: new Date(item.timestamp).toLocaleTimeString()
          }
        ])).flat()
        
        setMessages(history)
        setConversationId(convId)
        message.success('对话历史已加载')
      }
    } catch (error) {
      console.error('Load history error:', error)
      message.error('加载对话历史失败')
    }
  }

  // 音频上传配置
  const uploadProps = {
    name: 'file',
    accept: '.wav,.mp3,.flac,.m4a,.ogg',
    fileList: audioFile ? [{
      uid: '1',
      name: audioFile.name,
      status: 'done' as const,
      size: audioFile.size
    }] : [],
    beforeUpload: (file: File) => {
      const isAudio = file.type.startsWith('audio/') || 
                     ['wav', 'mp3', 'flac', 'm4a', 'ogg'].some(ext => 
                       file.name.toLowerCase().endsWith(`.${ext}`))
      
      if (!isAudio) {
        message.error('请上传音频文件！')
        return false
      }

      const isLt10M = file.size / 1024 / 1024 < 10
      if (!isLt10M) {
        message.error('音频文件大小不能超过 10MB！')
        return false
      }

      setAudioFile(file)
      return false
    },
    onRemove: () => {
      setAudioFile(null)
    },
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div className="text-center mb-24">
        <Title level={2}>💬 智能语音交互</Title>
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          与AI进行自然的方言对话交流，支持语音和文本输入，提供问答和聊天功能
        </Paragraph>
      </div>

      <Row gutter={[24, 24]}>
        {/* 左侧：设置面板 */}
        <Col xs={24} lg={8}>
          <Card title="交互设置" className="mb-16">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* 功能模式 */}
              <div>
                <Text strong>功能模式</Text>
                <Select
                  value={currentTab}
                  onChange={setCurrentTab}
                  style={{ width: '100%', marginTop: 8 }}
                  options={[
                    { label: '💬 智能对话', value: 'chat' },
                    { label: '❓ 方言问答', value: 'qa' }
                  ]}
                />
              </div>

              <Divider />

              {/* 语言设置 */}
              <div>
                <Text strong>语言设置</Text>
                <div style={{ marginTop: 8 }}>
                  <Text>用户语言:</Text>
                  <Select
                    value={userLanguage}
                    onChange={setUserLanguage}
                    options={languageOptions}
                    style={{ width: '100%', marginTop: 4, marginBottom: 12 }}
                  />
                  
                  <Text>回复语言:</Text>
                  <Select
                    value={responseLanguage}
                    onChange={setResponseLanguage}
                    options={languageOptions}
                    style={{ width: '100%', marginTop: 4 }}
                  />
                </div>
              </div>

              <Divider />

              {/* 回复模式 */}
              <div>
                <Text strong>回复模式</Text>
                <Select
                  value={responseMode}
                  onChange={setResponseMode}
                  style={{ width: '100%', marginTop: 8 }}
                  options={[
                    { label: '文本 + 语音', value: 'both' },
                    { label: '仅文本', value: 'text' },
                    { label: '仅语音', value: 'audio' }
                  ]}
                />
              </div>

              <Divider />

              {/* 音频上传 */}
              <div>
                <Text strong>语音输入</Text>
                <Upload {...uploadProps} style={{ marginTop: 8 }}>
                  <Button icon={<AudioOutlined />} block>
                    上传音频文件
                  </Button>
                </Upload>
                {audioFile && (
                  <Alert
                    message={`已选择: ${audioFile.name}`}
                    type="info"
                    style={{ marginTop: 8 }}
                    closable
                    onClose={() => setAudioFile(null)}
                  />
                )}
              </div>

              <Divider />

              {/* 操作按钮 */}
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  type="primary"
                  danger
                  icon={<ClearOutlined />}
                  onClick={clearConversation}
                  disabled={messages.length === 0}
                  block
                >
                  清空对话
                </Button>
                {conversationId && (
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    对话ID: {conversationId.slice(0, 8)}...
                  </Text>
                )}
              </Space>
            </Space>
          </Card>

          {/* 对话统计 */}
          {messages.length > 0 && (
            <Card title="对话统计" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>消息数量:</Text>
                  <Text strong>{messages.length}</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>用户消息:</Text>
                  <Text>{messages.filter(m => m.type === 'user').length}</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>AI回复:</Text>
                  <Text>{messages.filter(m => m.type === 'assistant').length}</Text>
                </div>
              </Space>
            </Card>
          )}
        </Col>

        {/* 右侧：对话界面 */}
        <Col xs={24} lg={16}>
          <Card title={currentTab === 'chat' ? '智能对话' : '方言问答'} className="mb-16">
            {/* 消息列表 */}
            <div 
              style={{ 
                height: 400, 
                overflowY: 'auto', 
                border: '1px solid #f0f0f0', 
                borderRadius: '6px',
                padding: '12px',
                background: '#fafafa'
              }}
            >
              {messages.length === 0 ? (
                <Empty
                  description={
                    currentTab === 'chat' 
                      ? '开始与AI进行方言对话吧！' 
                      : '有什么问题想要了解？'
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ) : (
                <List
                  dataSource={messages}
                  renderItem={(item) => (
                    <List.Item style={{ border: 'none', padding: '8px 0' }}>
                      <div 
                        style={{ 
                          width: '100%',
                          display: 'flex',
                          justifyContent: item.type === 'user' ? 'flex-end' : 'flex-start'
                        }}
                      >
                        <div
                          style={{
                            maxWidth: '70%',
                            padding: '12px 16px',
                            borderRadius: '18px',
                            background: item.type === 'user' ? '#1890ff' : '#ffffff',
                            color: item.type === 'user' ? '#ffffff' : '#000000',
                            border: item.type === 'assistant' ? '1px solid #e8e8e8' : 'none',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
                          }}
                        >
                          <div style={{ marginBottom: '4px' }}>
                            <Space>
                              {item.type === 'user' ? (
                                <UserOutlined style={{ fontSize: '14px' }} />
                              ) : (
                                <RobotOutlined style={{ fontSize: '14px' }} />
                              )}
                              <Text 
                                style={{ 
                                  fontSize: '12px', 
                                  opacity: 0.8,
                                  color: item.type === 'user' ? '#ffffff' : '#8c8c8c'
                                }}
                              >
                                {item.timestamp}
                              </Text>
                            </Space>
                          </div>
                          
                          <div style={{ marginBottom: '8px' }}>
                            {item.content}
                          </div>

                          {/* 语音播放 */}
                          {item.audioUrl && (
                            <div style={{ marginTop: '8px' }}>
                              <audio controls style={{ width: '100%', height: '32px' }}>
                                <source src={item.audioUrl} type="audio/wav" />
                              </audio>
                            </div>
                          )}

                          {/* 情感和意图标签 */}
                          {item.emotion && item.intent && (
                            <div style={{ marginTop: '8px' }}>
                              <Space size="small">
                                <Tag color="orange" size="small">
                                  {item.emotion}
                                </Tag>
                                <Tag color="blue" size="small">
                                  {item.intent}
                                </Tag>
                              </Space>
                            </div>
                          )}
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div style={{ marginTop: '16px' }}>
              <Space.Compact style={{ width: '100%' }}>
                <TextArea
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder={
                    currentTab === 'chat' 
                      ? "输入消息与AI对话..." 
                      : "输入您想了解的问题..."
                  }
                  autoSize={{ minRows: 2, maxRows: 4 }}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault()
                      if (currentTab === 'chat') {
                        textInput.trim() ? sendTextMessage() : sendAudioMessage()
                      } else {
                        handleDialectQA()
                      }
                    }
                  }}
                  style={{ flex: 1 }}
                />
              </Space.Compact>
              
              <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <Space>
                  {audioFile && (
                    <Button
                      type="primary"
                      icon={<AudioOutlined />}
                      loading={loading}
                      onClick={sendAudioMessage}
                      disabled={currentTab === 'qa'}
                    >
                      发送语音
                    </Button>
                  )}
                </Space>
                
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  loading={loading}
                  onClick={currentTab === 'chat' ? sendTextMessage : handleDialectQA}
                  disabled={!textInput.trim()}
                >
                  {currentTab === 'chat' ? '发送消息' : '提问'}
                </Button>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 使用说明 */}
      <Card title="功能说明" className="mt-24">
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Title level={4}>智能对话</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>支持文本和语音双向交流</li>
              <li>多轮对话上下文理解</li>
              <li>情感和意图识别</li>
              <li>跨语言对话支持</li>
              <li>对话历史保存和管理</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <Title level={4}>方言问答</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>方言文化知识问答</li>
              <li>语言学习辅助</li>
              <li>智能关键词提取</li>
              <li>问题分类和推荐</li>
              <li>多语言回答支持</li>
            </ul>
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default VoiceInteractionPage 