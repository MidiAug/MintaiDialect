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
  Alert,
  Tag,
  Progress,
  Switch,
  Tooltip
} from 'antd'
import { 
  TranslationOutlined,
  SwapOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  ClearOutlined,
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

const TranslationModule: React.FC = () => {
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
    <div className="module-container">
      <div className="module-header">
        <div className="module-icon">
          <TranslationOutlined />
        </div>
        <div className="module-title-section">
          <Title level={2} className="module-title">方言语音互译</Title>
          <Paragraph className="module-description">
            方言与普通话之间的双向语音翻译，支持多种闽台方言，提供高质量的跨语言交流体验
          </Paragraph>
        </div>
      </div>

      <Row gutter={[32, 32]} className="module-content">
        {/* 左侧：上传和设置 */}
        <Col xs={24} lg={12}>
          <Card className="input-card" bordered={false}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 文件上传 */}
              <div className="upload-section">
                <Text strong className="section-label">选择音频文件</Text>
                <Upload.Dragger {...uploadProps} className="audio-upload">
                  <p className="ant-upload-drag-icon">
                    <AudioOutlined />
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
                    className="file-info"
                  />
                )}
              </div>

              {/* 语言设置 */}
              <div className="settings-section">
                <Text strong className="section-label">翻译语言设置</Text>
                <div className="language-settings">
                  <div className="language-selector">
                    <Text>源语言:</Text>
                    <Select
                      value={sourceLanguage}
                      onChange={setSourceLanguage}
                      options={languageOptions}
                      className="language-select"
                    />
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={detectingLanguage}
                      onClick={detectLanguage}
                      className="detect-button"
                      disabled={!audioFile}
                    >
                      自动检测
                    </Button>
                  </div>
                  
                  <div className="language-swap">
                    <Tooltip title="交换语言">
                      <Button 
                        icon={<SwapOutlined />} 
                        onClick={swapLanguages}
                        shape="circle"
                        className="swap-button"
                      />
                    </Tooltip>
                  </div>
                  
                  <div className="language-selector">
                    <Text>目标语言:</Text>
                    <Select
                      value={targetLanguage}
                      onChange={setTargetLanguage}
                      options={languageOptions}
                      className="language-select"
                    />
                  </div>
                </div>
                
                {/* 翻译质量提示 */}
                <Alert
                  message={`翻译质量: ${getTranslationQuality(sourceLanguage, targetLanguage)}`}
                  type={getTranslationQuality(sourceLanguage, targetLanguage) === '高' ? 'success' : 'warning'}
                  showIcon
                  className="quality-alert"
                />
              </div>

              {/* 输出选项 */}
              <div className="output-section">
                <Text strong className="section-label">输出选项</Text>
                <div className="output-options">
                  <div className="output-option">
                    <Switch
                      checked={returnText}
                      onChange={setReturnText}
                    />
                    <Text>返回文本</Text>
                  </div>
                  <div className="output-option">
                    <Switch
                      checked={returnAudio}
                      onChange={setReturnAudio}
                    />
                    <Text>返回语音</Text>
                  </div>
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="action-buttons">
                <Button
                  type="primary"
                  size="large"
                  loading={loading}
                  onClick={handleTranslation}
                  disabled={!audioFile || sourceLanguage === targetLanguage}
                  icon={<TranslationOutlined />}
                  className="primary-button"
                >
                  开始翻译
                </Button>
                <Button
                  onClick={clearResult}
                  icon={<ClearOutlined />}
                  className="secondary-button"
                >
                  清空结果
                </Button>
              </div>
            </Space>
          </Card>
        </Col>

        {/* 右侧：翻译结果 */}
        <Col xs={24} lg={12}>
          <Card className="result-card" bordered={false}>
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
                    <div className="source-text">
                      {result.source_text}
                    </div>
                    <Tag color="blue" className="language-tag">
                      {languageOptions.find(l => l.value === result.source_language)?.label}
                    </Tag>
                  </div>
                </div>

                {/* 译文 */}
                <div className="result-item">
                  <div className="result-label">译文:</div>
                  <div className="result-content">
                    <div className="target-text">
                      {result.target_text}
                    </div>
                    <Tag color="green" className="language-tag">
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
                      <audio controls className="audio-player">
                        <source src={result.target_audio_url} type="audio/wav" />
                        您的浏览器不支持音频播放
                      </audio>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!result && !loading && (
              <div className="empty-state">
                <TranslationOutlined className="empty-icon" />
                <div className="empty-text">上传音频文件开始翻译</div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 支持的语言对 */}
      {supportedPairs.length > 0 && (
        <Card className="supported-pairs-card" bordered={false}>
          <Title level={4}>支持的翻译语言对</Title>
          <div className="pairs-grid">
            {supportedPairs.map((pair, index) => (
              <div key={index} className="pair-item">
                <Tag color="blue" className="pair-tag">
                  {languageOptions.find(l => l.value === pair.source)?.label}
                </Tag>
                <SwapOutlined className="pair-arrow" />
                <Tag color="green" className="pair-tag">
                  {languageOptions.find(l => l.value === pair.target)?.label}
                </Tag>
                <Tag 
                  color={pair.quality === '高' ? 'success' : pair.quality === '中' ? 'warning' : 'default'}
                  className="quality-tag"
                >
                  {pair.quality}
                </Tag>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 使用说明 */}
      <Card className="instructions-card" bordered={false}>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Title level={4}>功能特点</Title>
            <ul className="feature-list">
              <li>支持多种闽台方言与普通话互译</li>
              <li>提供文本和语音双重输出</li>
              <li>智能语言检测功能</li>
              <li>实时翻译质量评估</li>
              <li>支持音频文件下载保存</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <Title level={4}>使用建议</Title>
            <ul className="feature-list">
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

export default TranslationModule
