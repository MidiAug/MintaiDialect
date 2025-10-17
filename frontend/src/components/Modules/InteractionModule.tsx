import React, { useState, useRef, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Button, 
  Input, 
  message, 
  Space, 
  Row,
  Col,
  Select,
  Upload,
  List,
  Tag,
  Alert,
  Switch,
  Empty
} from 'antd'
import { 
  MessageOutlined, 
  AudioOutlined, 
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  ClearOutlined,
  PlayCircleOutlined,
  DownloadOutlined
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

const InteractionModule: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [textInput, setTextInput] = useState('')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [conversationId, setConversationId] = useState<string>('')
  const [userLanguage, setUserLanguage] = useState<LanguageType>(LanguageType.MINNAN)
  const [responseLanguage, setResponseLanguage] = useState<LanguageType>(LanguageType.MINNAN)
  const [responseMode, setResponseMode] = useState<'text' | 'audio' | 'both'>('both')
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
    <div className="module-container">
      <div className="module-header">
        <div className="module-icon">
          <MessageOutlined />
        </div>
        <div className="module-title-section">
          <Title level={2} className="module-title">智能语音交互</Title>
          <Paragraph className="module-description">
            与AI进行自然的方言对话交流，支持语音和文本输入，提供问答和聊天功能
          </Paragraph>
        </div>
      </div>

      <Row gutter={[32, 32]} className="module-content">
        {/* 左侧：设置面板 */}
        <Col xs={24} lg={8}>
          <Card className="settings-card" bordered={false}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 功能模式 */}
              <div className="setting-section">
                <Text strong className="section-label">功能模式</Text>
                <Select
                  value={currentTab}
                  onChange={setCurrentTab}
                  className="mode-select"
                  options={[
                    { label: '💬 智能对话', value: 'chat' },
                    { label: '❓ 方言问答', value: 'qa' }
                  ]}
                />
              </div>

              {/* 语言设置 */}
              <div className="setting-section">
                <Text strong className="section-label">语言设置</Text>
                <div className="language-settings">
                  <div className="setting-item">
                    <Text>用户语言:</Text>
                    <Select
                      value={userLanguage}
                      onChange={setUserLanguage}
                      options={languageOptions}
                      className="language-select"
                    />
                  </div>
                  
                  <div className="setting-item">
                    <Text>回复语言:</Text>
                    <Select
                      value={responseLanguage}
                      onChange={setResponseLanguage}
                      options={languageOptions}
                      className="language-select"
                    />
                  </div>
                </div>
              </div>

              {/* 回复模式 */}
              <div className="setting-section">
                <Text strong className="section-label">回复模式</Text>
                <Select
                  value={responseMode}
                  onChange={setResponseMode}
                  className="response-select"
                  options={[
                    { label: '文本 + 语音', value: 'both' },
                    { label: '仅文本', value: 'text' },
                    { label: '仅语音', value: 'audio' }
                  ]}
                />
              </div>

              {/* 音频上传 */}
              <div className="setting-section">
                <Text strong className="section-label">语音输入</Text>
                <Upload {...uploadProps}>
                  <Button icon={<AudioOutlined />} block className="upload-button">
                    上传音频文件
                  </Button>
                </Upload>
                {audioFile && (
                  <Alert
                    message={`已选择: ${audioFile.name}`}
                    type="info"
                    className="file-alert"
                    closable
                    onClose={() => setAudioFile(null)}
                  />
                )}
              </div>

              {/* 操作按钮 */}
              <div className="action-buttons">
                <Button
                  type="primary"
                  danger
                  icon={<ClearOutlined />}
                  onClick={clearConversation}
                  disabled={messages.length === 0}
                  block
                  className="clear-button"
                >
                  清空对话
                </Button>
                {conversationId && (
                  <Text type="secondary" className="conversation-id">
                    对话ID: {conversationId.slice(0, 8)}...
                  </Text>
                )}
              </div>
            </Space>
          </Card>

          {/* 对话统计 */}
          {messages.length > 0 && (
            <Card className="stats-card" bordered={false}>
              <Title level={4}>对话统计</Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div className="stat-item">
                  <Text>消息数量:</Text>
                  <Text strong>{messages.length}</Text>
                </div>
                <div className="stat-item">
                  <Text>用户消息:</Text>
                  <Text>{messages.filter(m => m.type === 'user').length}</Text>
                </div>
                <div className="stat-item">
                  <Text>AI回复:</Text>
                  <Text>{messages.filter(m => m.type === 'assistant').length}</Text>
                </div>
              </Space>
            </Card>
          )}
        </Col>

        {/* 右侧：对话界面 */}
        <Col xs={24} lg={16}>
          <Card className="chat-card" bordered={false}>
            <div className="chat-header">
              <Title level={4}>{currentTab === 'chat' ? '智能对话' : '方言问答'}</Title>
            </div>
            
            {/* 消息列表 */}
            <div className="messages-container">
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
                    <List.Item className="message-item">
                      <div className={`message ${item.type}`}>
                        <div className="message-header">
                          <Space>
                            {item.type === 'user' ? (
                              <UserOutlined className="message-icon" />
                            ) : (
                              <RobotOutlined className="message-icon" />
                            )}
                            <Text className="message-time">{item.timestamp}</Text>
                          </Space>
                        </div>
                        
                        <div className="message-content">
                          {item.content}
                        </div>

                        {/* 语音播放 */}
                        {item.audioUrl && (
                          <div className="message-audio">
                            <audio controls className="audio-player">
                              <source src={item.audioUrl} type="audio/wav" />
                            </audio>
                          </div>
                        )}

                        {/* 情感和意图标签 */}
                        {item.emotion && item.intent && (
                          <div className="message-tags">
                            <Space size="small">
                              <Tag color="orange" size="small">{item.emotion}</Tag>
                              <Tag color="blue" size="small">{item.intent}</Tag>
                            </Space>
                          </div>
                        )}
                      </div>
                    </List.Item>
                  )}
                />
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div className="input-area">
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
                className="message-input"
              />
              
              <div className="input-actions">
                <Space>
                  {audioFile && (
                    <Button
                      type="primary"
                      icon={<AudioOutlined />}
                      loading={loading}
                      onClick={sendAudioMessage}
                      disabled={currentTab === 'qa'}
                      className="audio-send-button"
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
                  className="send-button"
                >
                  {currentTab === 'chat' ? '发送消息' : '提问'}
                </Button>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 使用说明 */}
      <Card className="instructions-card" bordered={false}>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Title level={4}>智能对话</Title>
            <ul className="feature-list">
              <li>支持文本和语音双向交流</li>
              <li>多轮对话上下文理解</li>
              <li>情感和意图识别</li>
              <li>跨语言对话支持</li>
              <li>对话历史保存和管理</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <Title level={4}>方言问答</Title>
            <ul className="feature-list">
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

export default InteractionModule
