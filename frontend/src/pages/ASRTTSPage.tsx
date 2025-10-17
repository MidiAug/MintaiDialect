import React, { useState } from 'react'
import { Spin } from 'antd'
import { 
  Typography, 
  Card, 
  Tabs, 
  Upload, 
  Button, 
  Select, 
  Input, 
  message, 
  Space, 
  Divider,
  Row,
  Col,
  Alert,
  Tag
} from 'antd'
import { 
  AudioOutlined, 
  PlayCircleOutlined,
  DownloadOutlined,
  ClearOutlined,
  SoundOutlined
} from '@ant-design/icons'
import { asrTtsAPI, LanguageType, AudioFormat, ApiResponse } from '@/services/api'

const { Title, Paragraph, Text } = Typography
const { TextArea } = Input
const { TabPane } = Tabs

interface ASRResult {
  text: string
  language: LanguageType
  duration: number
  timestamps?: any[]
  words?: any[]
}

interface TTSResult {
  audio_url: string
  audio_duration: number
  file_size: number
  audio_format: string
  poj_text?: string
  zh_text?: string
}

const ASRTTSPage: React.FC = () => {
  // ASR 相关状态
  const [asrLoading, setAsrLoading] = useState(false)
  const [asrFile, setAsrFile] = useState<File | null>(null)
  const [asrResult, setAsrResult] = useState<ASRResult | null>(null)
  const [asrLanguage, setAsrLanguage] = useState<LanguageType>(LanguageType.MINNAN)

  // TTS 相关状态
  const [ttsLoading, setTtsLoading] = useState(false)
  const [ttsText, setTtsText] = useState('')
  const [ttsResult, setTtsResult] = useState<TTSResult | null>(null)
  const [ttsLanguage, setTtsLanguage] = useState<LanguageType>(LanguageType.MINNAN)
  const [voiceSpeed, setVoiceSpeed] = useState(1.0)
  const [audioFormat, setAudioFormat] = useState('wav')
  const [pojText, setPojText] = useState('')

  // 语言选项
  const languageOptions = [
    { label: '闽南话', value: LanguageType.MINNAN },
    { label: '客家话', value: LanguageType.HAKKA },
    { label: '台湾话', value: LanguageType.TAIWANESE },
    { label: '普通话', value: LanguageType.MANDARIN },
  ]

  // 音频格式选项
  const audioFormatOptions = [
    { label: 'WAV', value: 'wav' },
    { label: 'MP3', value: 'mp3' },
    { label: 'FLAC', value: 'flac' },
    { label: 'M4A', value: 'm4a' },
    { label: 'OGG', value: 'ogg' },
  ]

  // ASR 处理函数
  const handleASR = async () => {
    if (!asrFile) {
      message.warning('请先上传音频文件')
      return
    }

    setAsrLoading(true)
    try {
      const response = await asrTtsAPI.speechToText({
        audio_file: asrFile,
        source_language: asrLanguage,
      }) as unknown as ApiResponse<ASRResult>

      if (response.success) {
        setAsrResult(response.data)
        message.success('语音识别完成！')
      } else {
        message.error(response.message || '语音识别失败')
      }
    } catch (error) {
      console.error('ASR Error:', error)
      message.error('语音识别服务异常，请稍后重试')
    } finally {
      setAsrLoading(false)
    }
  }

  // TTS 处理函数
  const handleTTS = async () => {
    if (!ttsText.trim()) {
      message.warning('请输入要转换的文本')
      return
    }

    setTtsLoading(true)
    try {
      const response = await asrTtsAPI.textToSpeech({
        text: ttsText,
        target_language: ttsLanguage,
        speed: voiceSpeed,
        audio_format: audioFormat as AudioFormat,
      }) as unknown as ApiResponse<TTSResult>

      if (response.success) {
        setTtsResult(response.data)
        setPojText(response.data?.poj_text || '')
        message.success('语音合成完成！')
      } else {
        message.error(response.message || '语音合成失败')
      }
    } catch (error) {
      console.error('TTS Error:', error)
      message.error('语音合成服务异常，请稍后重试')
    } finally {
      setTtsLoading(false)
    }
  }

  // 支持的音频格式（与后端AudioFormat枚举保持一致）
  const supportedAudioFormats = ['wav', 'mp3', 'flac', 'm4a', 'ogg']
  
  // 音频上传配置
  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.wav,.mp3,.flac,.m4a,.ogg',
    fileList: asrFile ? [{
      uid: '1',
      name: asrFile.name,
      status: 'done' as const,
      size: asrFile.size
    }] : [],
    beforeUpload: (file: File) => {
      // 检查文件扩展名
      const fileExtension = file.name.toLowerCase().split('.').pop()
      if (!fileExtension || !supportedAudioFormats.includes(fileExtension)) {
        message.error(`不支持的音频格式: ${fileExtension || '未知'}。支持的格式: ${supportedAudioFormats.join(', ')}`)
        return false
      }

      // 检查MIME类型（额外验证）
      const isAudio = file.type.startsWith('audio/') || 
                     supportedAudioFormats.some(ext => 
                       file.name.toLowerCase().endsWith(`.${ext}`))
      
      if (!isAudio) {
        message.error('请上传有效的音频文件！')
        return false
      }

      // 文件大小校验：限制为10MB
      const maxSize = 10 * 1024 * 1024 // 10MB
      if (file.size > maxSize) {
        message.error(`文件大小不能超过 10MB！当前文件大小: ${(file.size / 1024 / 1024).toFixed(2)}MB`)
        return false
      }

      setAsrFile(file)
      return false // 阻止自动上传
    },
    onRemove: () => {
      setAsrFile(null)
      setAsrResult(null)
    },
  }

  // 清空结果
  const clearASRResult = () => {
    setAsrResult(null)
    setAsrFile(null)
  }

  const clearTTSResult = () => {
    setTtsResult(null)
    setTtsText('')
    setPojText('')
  }

  // 使用 fetch + Blob 下载，兼容跨域和现代浏览器
  const downloadAudio = async (url: string, filename: string) => {
    try {
      const response = await fetch(url)
      if (!response.ok) throw new Error('下载失败')
      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = blobUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()

      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      console.error(err)
      message.error('下载失败，请重试')
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div className="text-center mb-24">
        <Title level={2}>🎤 方言语音文本互转</Title>
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          高精度的闽台方言语音识别和文本转语音服务，支持多种方言和音频格式
        </Paragraph>
      </div>

      <Tabs defaultActiveKey="asr" size="large">
        {/* 语音识别 Tab */}
        <TabPane tab={<span><SoundOutlined />语音识别 (ASR)</span>} key="asr">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="音频上传与设置" className="mb-16">
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {/* 文件上传 */}
                  <div>
                    <Text strong>选择音频文件</Text>
                    <Upload.Dragger {...uploadProps} style={{ marginTop: 8 }}>
                      <p className="ant-upload-drag-icon">
                        <AudioOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
                      </p>
                      <p className="ant-upload-text">点击或拖拽音频文件到此区域</p>
                      <p className="ant-upload-hint">
                        支持 WAV, MP3, FLAC, M4A, OGG 格式，最大 10MB<br/>
                      </p>
                    </Upload.Dragger>
                    {asrFile && (
                      <Alert
                        message={`已选择文件: ${asrFile.name}`}
                        description={`大小: ${(asrFile.size / 1024 / 1024).toFixed(2)} MB`}
                        type="info"
                        showIcon
                        style={{ marginTop: 8 }}
                      />
                    )}
                  </div>

                  <Divider />

                  {/* 识别设置 */}
                  <div>
                    <Text strong>识别设置</Text>
                    <div style={{ marginTop: 12 }}>
                      <Row gutter={[16, 16]}>
                        <Col span={24}>
                          <Text>源语言:</Text>
                          <Select
                            value={asrLanguage}
                            onChange={setAsrLanguage}
                            options={languageOptions}
                            style={{ width: '100%', marginTop: 4 }}
                            open={false}
                            onClick={() => message.info('暂不支持其他语言')}
                          />
                        </Col>
                      </Row>
                    </div>
                  </div>

                  <Divider />

                  {/* 操作按钮 */}
                  <Space>
                    <Button
                      type="primary"
                      loading={asrLoading}
                      onClick={handleASR}
                      disabled={!asrFile}
                      icon={<SoundOutlined />}
                    >
                      开始识别
                    </Button>
                    <Button
                      onClick={clearASRResult}
                      icon={<ClearOutlined />}
                    >
                      清空结果
                    </Button>
                  </Space>
                </Space>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="识别结果" className="mb-16">
                {asrLoading && (
                  <div className="loading-container" style={{ textAlign: 'center', padding: '40px 0' }}>
                    <Spin size="large" tip="正在识别语音，请稍候..." />
                  </div>
                )}

                {asrResult && !asrLoading && (
                  <div className="result-container">
                    <div className="result-item">
                      <div className="result-label">识别文本:</div>
                      <div className="result-content">
                        <TextArea
                          value={asrResult.text}
                          autoSize={{ minRows: 3, maxRows: 6 }}
                          readOnly
                        />
                      </div>
                    </div>
                    
                    <div className="result-item">
                          <div className="result-label">音频时长:</div>
                      <div className="result-content">
                        {typeof asrResult.duration === 'number' ? asrResult.duration.toFixed(2) + ' 秒' : '—'}
                      </div>
                    </div>

                    {Array.isArray(asrResult.timestamps) && (
                      <div className="result-item">
                        <div className="result-label">时间戳:</div>
                        <div className="result-content">
                          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                            {asrResult.timestamps.map((item, index) => (
                              <div key={index} style={{ marginBottom: 4 }}>
                                <Tag>{typeof item.start === 'number' ? item.start.toFixed(1) : '-'}s-{typeof item.end === 'number' ? item.end.toFixed(1) : '-'}s</Tag>
                                {item.word}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {!asrResult && !asrLoading && (
                  <div className="text-center" style={{ padding: '40px 0', color: '#8c8c8c' }}>
                    <AudioOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                    <div>上传音频文件开始识别</div>
                  </div>
                )}
              </Card>
              {/* 使用说明（ASR）- 放在识别结果下面 */}
              <Card title="使用说明" className="mb-16">
                <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                  <li>支持 {supportedAudioFormats.map(f => f.toUpperCase()).join(', ')} 格式音频文件</li>
                  <li>文件大小限制为 10MB</li>
                  <li>非WAV格式会自动转换为WAV格式进行处理</li>
                  <li>支持闽南话、客家话、台湾话、普通话识别</li>
                  <li>高精度方言语音识别</li>
                  <li>上传前会自动校验文件格式和大小</li>
                </ul>
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 文本转语音 Tab */}
        <TabPane tab={<span><PlayCircleOutlined />文本转语音 (TTS)</span>} key="tts">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="文本输入与设置" className="mb-16">
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {/* 文本输入 */}
                  <div>
                    <Text strong>输入文本</Text>
                    <TextArea
                      value={ttsText}
                      onChange={(e) => setTtsText(e.target.value)}
                      placeholder="请输入要转换为语音的文本内容..."
                      autoSize={{ minRows: 4, maxRows: 8 }}
                      maxLength={1000}
                      showCount
                      style={{ marginTop: 8 }}
                    />
                  </div>

                  <Divider />

                  {/* 语音设置 */}
                  <div>
                    <Text strong>语音设置</Text>
                    <div style={{ marginTop: 12 }}>
                      <Row gutter={[16, 16]}>
                        <Col span={24}>
                          <Text>目标语言:</Text>
                          <Select
                            value={ttsLanguage}
                            onChange={setTtsLanguage}
                            options={languageOptions}
                            style={{ width: '100%', marginTop: 4 }}
                            open={false}
                            onClick={() => message.info('暂不支持其他语言')}
                          />
                        </Col>
                        <Col span={12}>
                          <Text>语音速度: {voiceSpeed}x</Text>
                          <div style={{ marginTop: 8 }}>
                            <Button.Group>
                              <Button size="small" onClick={() => setVoiceSpeed(0.5)}>0.5x</Button>
                              <Button size="small" onClick={() => setVoiceSpeed(1.0)}>1.0x</Button>
                              <Button size="small" onClick={() => setVoiceSpeed(1.5)}>1.5x</Button>
                              <Button size="small" onClick={() => setVoiceSpeed(2.0)}>2.0x</Button>
                            </Button.Group>
                          </div>
                        </Col>
                        <Col span={12}>
                          <Text>音频格式:</Text>
                          <Select
                            value={audioFormat}
                            onChange={setAudioFormat}
                            options={audioFormatOptions}
                            style={{ width: '100%', marginTop: 4 }}
                          />
                        </Col>
                      </Row>
                    </div>
                  </div>

                  <Divider />

                  {/* 操作按钮 */}
                  <Space>
                    <Button
                      type="primary"
                      loading={ttsLoading}
                      onClick={handleTTS}
                      disabled={!ttsText.trim()}
                      icon={<PlayCircleOutlined />}
                    >
                      生成语音
                    </Button>
                    <Button
                      onClick={clearTTSResult}
                      icon={<ClearOutlined />}
                    >
                      清空结果
                    </Button>
                  </Space>
                </Space>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="合成结果" className="mb-16">
                {ttsLoading && (
                  <div className="loading-container" style={{ textAlign: 'center', padding: '40px 0' }}>
                    <Spin size="large" tip="正在合成语音，请稍候..." />
                  </div>
                )}

                {ttsResult && !ttsLoading && (
                  <div className="result-container">
                    {pojText && (
                      <div className="result-item" style={{ marginBottom: 12 }}>
                        <div className="result-label">POJ 文本:</div>
                        <div className="result-content">
                          <TextArea
                            value={pojText}
                            autoSize={{ minRows: 2, maxRows: 6 }}
                            readOnly
                          />
                        </div>
                      </div>
                    )}
                    <div className="result-item">
                      <div className="result-label">音频播放:</div>
                      <div className="result-content">
                        <audio
                          controls
                          style={{ width: '100%' }}
                          preload="metadata"
                          // 禁用浏览器"更多"菜单项：下载/变速/投放，仅保留播放与音量
                          controlsList="nodownload noplaybackrate noremoteplayback"
                        >
                          <source src={ttsResult.audio_url} />
                          您的浏览器不支持音频播放
                        </audio>
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">音频时长:</div>
                      <div className="result-content">
                        {ttsResult.audio_duration.toFixed(2)} 秒
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">文件大小:</div>
                      <div className="result-content">
                        {(ttsResult.file_size / 1024).toFixed(2)} KB
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">音频格式:</div>
                      <div className="result-content">
                        <Tag color="green">{(ttsResult.audio_format || ttsResult.audio_url.split('.').pop() || 'wav').toUpperCase()}</Tag>
                      </div>
                    </div>

                  </div>
                )}

                {!ttsResult && !ttsLoading && (
                  <div className="text-center" style={{ padding: '40px 0', color: '#8c8c8c' }}>
                    <PlayCircleOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                    <div>输入文本开始合成语音</div>
                  </div>
                )}
              </Card>
              {/* 使用说明（TTS） */}
              <Card title="使用说明" className="mb-16">
                <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                  <li>支持多种闽台方言语音合成</li>
                  <li>文本长度限制为 1000 个字符</li>
                  <li>可调节语音速度和选择音频格式</li>
                  <li>支持 WAV、MP3、FLAC、M4A、OGG 格式</li>
                  <li>支持在线播放和下载</li>
                </ul>
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>

    </div>
  )
}

export default ASRTTSPage 