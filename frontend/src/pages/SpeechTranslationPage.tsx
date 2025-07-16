import React, { useState, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Upload, 
  Button, 
  Select, 
  message, 
  Space, 
  Row,
  Col,
  Progress,
  Alert,
  Tag,
  Divider,
  Switch,
  Tooltip
} from 'antd'
import { 
  UploadOutlined, 
  SwapOutlined, 
  PlayCircleOutlined,
  DownloadOutlined,
  ClearOutlined,
  TranslationOutlined,
  AudioOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import { speechTranslationAPI, LanguageType } from '@/services/api'

const { Title, Paragraph, Text } = Typography

interface TranslationResult {
  source_text: string
  target_text: string
  target_audio_url?: string
  confidence: number
  source_language: LanguageType
  target_language: LanguageType
}

interface LanguagePair {
  source: LanguageType
  target: LanguageType
  quality: string
}

const SpeechTranslationPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [result, setResult] = useState<TranslationResult | null>(null)
  const [sourceLanguage, setSourceLanguage] = useState<LanguageType>(LanguageType.MINNAN)
  const [targetLanguage, setTargetLanguage] = useState<LanguageType>(LanguageType.MANDARIN)
  const [returnAudio, setReturnAudio] = useState(true)
  const [returnText, setReturnText] = useState(true)
  const [supportedPairs, setSupportedPairs] = useState<LanguagePair[]>([])
  const [detectingLanguage, setDetectingLanguage] = useState(false)

  // 语言选项
  const languageOptions = [
    { label: '闽南话', value: LanguageType.MINNAN },
    { label: '客家话', value: LanguageType.HAKKA },
    { label: '台湾话', value: LanguageType.TAIWANESE },
    { label: '普通话', value: LanguageType.MANDARIN },
  ]

  // 获取支持的语言对
  useEffect(() => {
    const fetchSupportedPairs = async () => {
      try {
        const response = await speechTranslationAPI.getSupportedPairs()
        if (response.success) {
          setSupportedPairs(response.data.supported_pairs)
        }
      } catch (error) {
        console.error('Error fetching supported pairs:', error)
      }
    }
    fetchSupportedPairs()
  }, [])

  // 语音翻译处理函数
  const handleTranslation = async () => {
    if (!audioFile) {
      message.warning('请先上传音频文件')
      return
    }

    if (sourceLanguage === targetLanguage) {
      message.warning('源语言和目标语言不能相同')
      return
    }

    setLoading(true)
    try {
      const response = await speechTranslationAPI.translateSpeech({
        audio_file: audioFile,
        source_language: sourceLanguage,
        target_language: targetLanguage,
        return_audio: returnAudio,
        return_text: returnText,
      })

      if (response.success) {
        setResult(response.data)
        message.success('语音翻译完成！')
      } else {
        message.error(response.message || '语音翻译失败')
      }
    } catch (error) {
      console.error('Translation Error:', error)
      message.error('语音翻译服务异常，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  // 语言检测
  const detectLanguage = async () => {
    if (!audioFile) {
      message.warning('请先上传音频文件')
      return
    }

    setDetectingLanguage(true)
    try {
      const response = await speechTranslationAPI.detectLanguage(audioFile)
      if (response.success) {
        const detected = response.data.detected_language
        setSourceLanguage(detected)
        message.success(`检测到语言: ${languageOptions.find(l => l.value === detected)?.label}`)
      } else {
        message.error('语言检测失败')
      }
    } catch (error) {
      console.error('Language detection error:', error)
      message.error('语言检测服务异常')
    } finally {
      setDetectingLanguage(false)
    }
  }

  // 交换源语言和目标语言
  const swapLanguages = () => {
    const temp = sourceLanguage
    setSourceLanguage(targetLanguage)
    setTargetLanguage(temp)
  }

  // 音频上传配置
  const uploadProps = {
    name: 'file',
    multiple: false,
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

      const isLt50M = file.size / 1024 / 1024 < 50
      if (!isLt50M) {
        message.error('文件大小不能超过 50MB！')
        return false
      }

      setAudioFile(file)
      return false
    },
    onRemove: () => {
      setAudioFile(null)
      setResult(null)
    },
  }

  // 清空结果
  const clearResult = () => {
    setResult(null)
    setAudioFile(null)
  }

  // 获取翻译质量
  const getTranslationQuality = (source: LanguageType, target: LanguageType) => {
    const pair = supportedPairs.find(p => p.source === source && p.target === target)
    return pair?.quality || '未知'
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div className="text-center mb-24">
        <Title level={2}>🌐 方言语音互译</Title>
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          方言与普通话之间的双向语音翻译，支持多种闽台方言，提供高质量的跨语言交流体验
        </Paragraph>
      </div>

      <Row gutter={[24, 24]}>
        {/* 左侧：上传和设置 */}
        <Col xs={24} lg={12}>
          <Card title="音频上传与翻译设置" className="mb-16">
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
                    支持 WAV, MP3, FLAC, M4A, OGG 格式，最大 50MB
                  </p>
                </Upload.Dragger>
                {audioFile && (
                  <Alert
                    message={`已选择文件: ${audioFile.name}`}
                    description={`大小: ${(audioFile.size / 1024 / 1024).toFixed(2)} MB`}
                    type="info"
                    showIcon
                    style={{ marginTop: 8 }}
                  />
                )}
              </div>

              <Divider />

              {/* 语言设置 */}
              <div>
                <Text strong>翻译语言设置</Text>
                <div style={{ marginTop: 12 }}>
                  <Row gutter={[16, 16]} align="middle">
                    <Col span={10}>
                      <Text>源语言:</Text>
                      <Select
                        value={sourceLanguage}
                        onChange={setSourceLanguage}
                        options={languageOptions}
                        style={{ width: '100%', marginTop: 4 }}
                      />
                      <Button
                        size="small"
                        icon={<ReloadOutlined />}
                        loading={detectingLanguage}
                        onClick={detectLanguage}
                        style={{ marginTop: 4, width: '100%' }}
                        disabled={!audioFile}
                      >
                        自动检测
                      </Button>
                    </Col>
                    <Col span={4} className="text-center">
                      <Tooltip title="交换语言">
                        <Button 
                          icon={<SwapOutlined />} 
                          onClick={swapLanguages}
                          shape="circle"
                        />
                      </Tooltip>
                    </Col>
                    <Col span={10}>
                      <Text>目标语言:</Text>
                      <Select
                        value={targetLanguage}
                        onChange={setTargetLanguage}
                        options={languageOptions}
                        style={{ width: '100%', marginTop: 4 }}
                      />
                    </Col>
                  </Row>
                  
                  {/* 翻译质量提示 */}
                  <Alert
                    message={`翻译质量: ${getTranslationQuality(sourceLanguage, targetLanguage)}`}
                    type={getTranslationQuality(sourceLanguage, targetLanguage) === '高' ? 'success' : 'warning'}
                    showIcon
                    style={{ marginTop: 12 }}
                  />
                </div>
              </div>

              <Divider />

              {/* 输出选项 */}
              <div>
                <Text strong>输出选项</Text>
                <div style={{ marginTop: 12 }}>
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Space>
                        <Switch
                          checked={returnText}
                          onChange={setReturnText}
                        />
                        <Text>返回文本</Text>
                      </Space>
                    </Col>
                    <Col span={12}>
                      <Space>
                        <Switch
                          checked={returnAudio}
                          onChange={setReturnAudio}
                        />
                        <Text>返回语音</Text>
                      </Space>
                    </Col>
                  </Row>
                </div>
              </div>

              <Divider />

              {/* 操作按钮 */}
              <Space>
                <Button
                  type="primary"
                  size="large"
                  loading={loading}
                  onClick={handleTranslation}
                  disabled={!audioFile || sourceLanguage === targetLanguage}
                  icon={<TranslationOutlined />}
                >
                  开始翻译
                </Button>
                <Button
                  onClick={clearResult}
                  icon={<ClearOutlined />}
                >
                  清空结果
                </Button>
              </Space>
            </Space>
          </Card>

          {/* 支持的语言对 */}
          <Card title="支持的翻译语言对" size="small">
            <div style={{ maxHeight: 200, overflowY: 'auto' }}>
              {supportedPairs.map((pair, index) => (
                <div key={index} style={{ marginBottom: 8, display: 'flex', alignItems: 'center' }}>
                  <Tag color="blue" style={{ minWidth: 60 }}>
                    {languageOptions.find(l => l.value === pair.source)?.label}
                  </Tag>
                  <SwapOutlined style={{ margin: '0 8px', color: '#8c8c8c' }} />
                  <Tag color="green" style={{ minWidth: 60 }}>
                    {languageOptions.find(l => l.value === pair.target)?.label}
                  </Tag>
                  <Tag 
                    color={pair.quality === '高' ? 'success' : pair.quality === '中' ? 'warning' : 'default'}
                    style={{ marginLeft: 8 }}
                  >
                    {pair.quality}
                  </Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        {/* 右侧：翻译结果 */}
        <Col xs={24} lg={12}>
          <Card title="翻译结果" className="mb-16">
            {loading && (
              <div className="loading-container">
                <Progress type="circle" percent={65} />
                <div className="loading-text">正在翻译语音，请稍候...</div>
              </div>
            )}

            {result && !loading && (
              <div className="result-container">
                {/* 源文本 */}
                <div className="result-item">
                  <div className="result-label">原文:</div>
                  <div className="result-content">
                    <div style={{ 
                      background: '#f8f9fa', 
                      padding: '12px', 
                      borderRadius: '6px', 
                      border: '1px solid #e9ecef' 
                    }}>
                      {result.source_text}
                    </div>
                    <Tag color="blue" style={{ marginTop: 8 }}>
                      {languageOptions.find(l => l.value === result.source_language)?.label}
                    </Tag>
                  </div>
                </div>

                {/* 译文 */}
                <div className="result-item">
                  <div className="result-label">译文:</div>
                  <div className="result-content">
                    <div style={{ 
                      background: '#f6ffed', 
                      padding: '12px', 
                      borderRadius: '6px', 
                      border: '1px solid #b7eb8f' 
                    }}>
                      {result.target_text}
                    </div>
                    <Tag color="green" style={{ marginTop: 8 }}>
                      {languageOptions.find(l => l.value === result.target_language)?.label}
                    </Tag>
                  </div>
                </div>

                {/* 翻译质量 */}
                <div className="result-item">
                  <div className="result-label">翻译质量:</div>
                  <div className="result-content">
                    <Progress 
                      percent={Math.round(result.confidence * 100)} 
                      size="small"
                      status={result.confidence > 0.8 ? 'success' : 'normal'}
                    />
                  </div>
                </div>

                {/* 翻译后的音频 */}
                {result.target_audio_url && (
                  <div className="result-item">
                    <div className="result-label">翻译语音:</div>
                    <div className="result-content">
                      <audio controls style={{ width: '100%', marginBottom: 8 }}>
                        <source src={result.target_audio_url} type="audio/wav" />
                        您的浏览器不支持音频播放
                      </audio>
                      <Button
                        type="primary"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => {
                          const link = document.createElement('a')
                          link.href = result.target_audio_url!
                          link.download = `translation_${Date.now()}.wav`
                          link.click()
                        }}
                      >
                        下载音频
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!result && !loading && (
              <div className="text-center" style={{ padding: '40px 0', color: '#8c8c8c' }}>
                <TranslationOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                <div>上传音频文件开始翻译</div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 使用说明 */}
      <Card title="使用说明与注意事项" className="mt-24">
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Title level={4}>功能特点</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>支持多种闽台方言与普通话互译</li>
              <li>提供文本和语音双重输出</li>
              <li>智能语言检测功能</li>
              <li>实时翻译质量评估</li>
              <li>支持音频文件下载保存</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <Title level={4}>使用建议</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>录音环境尽量安静，避免背景噪音</li>
              <li>发音清晰，语速适中</li>
              <li>选择合适的翻译语言对以获得最佳效果</li>
              <li>短句翻译效果通常优于长段落</li>
              <li>可使用语言检测功能确认源语言</li>
            </ul>
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default SpeechTranslationPage 