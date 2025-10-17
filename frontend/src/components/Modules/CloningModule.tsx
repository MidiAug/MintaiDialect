import React, { useState } from 'react'
import { 
  Typography, 
  Card, 
  Upload, 
  Button, 
  Select, 
  Input, 
  message, 
  Space, 
  Row,
  Col,
  Progress,
  Alert,
  Tag,
  Switch,
  Slider,
  List
} from 'antd'
import { 
  UploadOutlined, 
  AudioOutlined, 
  PlayCircleOutlined,
  DownloadOutlined,
  ClearOutlined,
  UserOutlined,
  ExperimentOutlined,
  SoundOutlined,
  BarChartOutlined,
  SettingOutlined
} from '@ant-design/icons'
import { voiceCloningAPI, LanguageType } from '@/services/api'

const { Title, Paragraph, Text } = Typography
const { TextArea } = Input

interface CloningResult {
  cloned_audio_url: string
  similarity_score: number
  quality_score: number
  processing_time: number
  audio_duration: number
}

interface SimilarityResult {
  audio1_filename: string
  audio2_filename: string
  basic_analysis: {
    overall_similarity: number
    pitch_similarity: number
    timbre_similarity: number
    rhythm_similarity: number
    confidence: number
  }
  comprehensive_analysis?: any
  similarity_level: string
  recommendations: string[]
}

interface VoiceFeatures {
  filename: string
  duration: number
  basic_features: {
    fundamental_frequency: number
    pitch_range: number
    speaking_rate: number
    volume_mean: number
    volume_variance: number
  }
  voice_description: {
    gender_prediction: string
    age_estimation: string
    voice_quality: string
    emotional_tone: string
    accent_strength: string
  }
}

const CloningModule: React.FC = () => {
  // 文本驱动克隆状态
  const [textCloningLoading, setTextCloningLoading] = useState(false)
  const [refAudioFile, setRefAudioFile] = useState<File | null>(null)
  const [targetText, setTargetText] = useState('')
  const [textCloningResult, setTextCloningResult] = useState<CloningResult | null>(null)
  
  // 音频驱动克隆状态
  const [audioCloningLoading, setAudioCloningLoading] = useState(false)
  const [refAudioFile2, setRefAudioFile2] = useState<File | null>(null)
  const [targetAudioFile, setTargetAudioFile] = useState<File | null>(null)
  const [audioCloningResult, setAudioCloningResult] = useState<CloningResult | null>(null)
  
  // 相似度分析状态
  const [similarityLoading, setSimilarityLoading] = useState(false)
  const [audio1File, setAudio1File] = useState<File | null>(null)
  const [audio2File, setAudio2File] = useState<File | null>(null)
  const [similarityResult, setSimilarityResult] = useState<SimilarityResult | null>(null)
  
  // 特征提取状态
  const [featureLoading, setFeatureLoading] = useState(false)
  const [featureAudioFile, setFeatureAudioFile] = useState<File | null>(null)
  const [featureResult, setFeatureResult] = useState<VoiceFeatures | null>(null)

  // 通用设置
  const [language, setLanguage] = useState<LanguageType>(LanguageType.MINNAN)
  const [quality, setQuality] = useState<'low' | 'medium' | 'high'>('high')
  const [voiceSpeed, setVoiceSpeed] = useState(1.0)
  const [voicePitch, setVoicePitch] = useState(1.0)
  const [preserveEmotion, setPreserveEmotion] = useState(true)
  const [blendRatio, setBlendRatio] = useState(0.8)
  const [activeTab, setActiveTab] = useState('text-driven')

  // 语言选项
  const languageOptions = [
    { label: '闽南话', value: LanguageType.MINNAN },
    { label: '客家话', value: LanguageType.HAKKA },
    { label: '台湾话', value: LanguageType.TAIWANESE },
    { label: '普通话', value: LanguageType.MANDARIN },
  ]

  // 文本驱动克隆
  const handleTextDrivenCloning = async () => {
    if (!refAudioFile) {
      message.warning('请上传参考音频文件')
      return
    }
    if (!targetText.trim()) {
      message.warning('请输入目标文本')
      return
    }

    setTextCloningLoading(true)
    try {
      const response = await voiceCloningAPI.textDrivenCloning({
        reference_audio: refAudioFile,
        target_text: targetText,
        language,
        quality,
        preserve_emotion: preserveEmotion,
        voice_speed: voiceSpeed,
        voice_pitch: voicePitch
      })

      if (response.success) {
        setTextCloningResult(response.data)
        message.success('文本驱动音色克隆完成！')
      } else {
        message.error(response.message || '音色克隆失败')
      }
    } catch (error) {
      console.error('Text cloning error:', error)
      message.error('音色克隆服务异常，请稍后重试')
    } finally {
      setTextCloningLoading(false)
    }
  }

  // 音频驱动克隆
  const handleAudioDrivenCloning = async () => {
    if (!refAudioFile2 || !targetAudioFile) {
      message.warning('请上传参考音频和目标音频文件')
      return
    }

    setAudioCloningLoading(true)
    try {
      const response = await voiceCloningAPI.audioDrivenCloning(
        refAudioFile2,
        targetAudioFile,
        {
          quality,
          preserveEmotion,
          blendRatio
        }
      )

      if (response.success) {
        setAudioCloningResult(response.data)
        message.success('音频驱动音色克隆完成！')
      } else {
        message.error(response.message || '音色克隆失败')
      }
    } catch (error) {
      console.error('Audio cloning error:', error)
      message.error('音色克隆服务异常，请稍后重试')
    } finally {
      setAudioCloningLoading(false)
    }
  }

  // 相似度分析
  const handleSimilarityAnalysis = async () => {
    if (!audio1File || !audio2File) {
      message.warning('请上传两个音频文件进行对比')
      return
    }

    setSimilarityLoading(true)
    try {
      const response = await voiceCloningAPI.analyzeSimilarity(
        audio1File,
        audio2File,
        'comprehensive'
      )

      if (response.success) {
        setSimilarityResult(response.data)
        message.success('音色相似度分析完成！')
      } else {
        message.error(response.message || '相似度分析失败')
      }
    } catch (error) {
      console.error('Similarity analysis error:', error)
      message.error('相似度分析服务异常，请稍后重试')
    } finally {
      setSimilarityLoading(false)
    }
  }

  // 特征提取
  const handleFeatureExtraction = async () => {
    if (!featureAudioFile) {
      message.warning('请上传音频文件')
      return
    }

    setFeatureLoading(true)
    try {
      const response = await voiceCloningAPI.extractFeatures(featureAudioFile, 'all')

      if (response.success) {
        setFeatureResult(response.data)
        message.success('音色特征提取完成！')
      } else {
        message.error(response.message || '特征提取失败')
      }
    } catch (error) {
      console.error('Feature extraction error:', error)
      message.error('特征提取服务异常，请稍后重试')
    } finally {
      setFeatureLoading(false)
    }
  }

  // 音频上传配置生成器
  const createUploadProps = (setter: (file: File | null) => void, currentFile: File | null) => ({
    name: 'file',
    accept: '.wav,.mp3,.flac,.m4a,.ogg',
    fileList: currentFile ? [{
      uid: '1',
      name: currentFile.name,
      status: 'done' as const,
      size: currentFile.size
    }] : [],
    beforeUpload: (file: File) => {
      const isAudio = file.type.startsWith('audio/') || 
                     ['wav', 'mp3', 'flac', 'm4a', 'ogg'].some(ext => 
                       file.name.toLowerCase().endsWith(`.${ext}`))
      
      if (!isAudio) {
        message.error('请上传音频文件！')
        return false
      }

      const isLt20M = file.size / 1024 / 1024 < 20
      if (!isLt20M) {
        message.error('文件大小不能超过 20MB！')
        return false
      }

      setter(file)
      return false
    },
    onRemove: () => setter(null),
  })

  // 渲染文本驱动克隆
  const renderTextDrivenCloning = () => (
    <Row gutter={[32, 32]}>
      <Col xs={24} lg={12}>
        <Card className="input-card" bordered={false}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {/* 参考音频上传 */}
            <div className="upload-section">
              <Text strong className="section-label">参考音频文件</Text>
              <Upload.Dragger {...createUploadProps(setRefAudioFile, refAudioFile)} className="audio-upload">
                <p className="ant-upload-drag-icon">
                  <AudioOutlined />
                </p>
                <p className="ant-upload-text">上传参考音频文件</p>
                <p className="ant-upload-hint">
                  上传您想要克隆音色的参考音频 (WAV, MP3, FLAC, M4A, OGG)
                </p>
              </Upload.Dragger>
              {refAudioFile && (
                <Alert
                  message={`已选择: ${refAudioFile.name}`}
                  type="info"
                  className="file-info"
                  closable
                  onClose={() => setRefAudioFile(null)}
                />
              )}
            </div>

            {/* 目标文本 */}
            <div className="input-section">
              <Text strong className="section-label">目标文本</Text>
              <TextArea
                value={targetText}
                onChange={(e) => setTargetText(e.target.value)}
                placeholder="请输入要用克隆音色合成的文本内容..."
                autoSize={{ minRows: 4, maxRows: 8 }}
                maxLength={500}
                showCount
                className="text-input"
              />
            </div>

            {/* 克隆设置 */}
            <div className="settings-section">
              <Text strong className="section-label">克隆设置</Text>
              <div className="setting-item">
                <Text>语言:</Text>
                <Select
                  value={language}
                  onChange={setLanguage}
                  options={languageOptions}
                  className="language-select"
                />
              </div>
              <div className="setting-item">
                <Text>质量:</Text>
                <Select
                  value={quality}
                  onChange={setQuality}
                  className="quality-select"
                  options={[
                    { label: '高质量', value: 'high' },
                    { label: '中等质量', value: 'medium' },
                    { label: '快速模式', value: 'low' }
                  ]}
                />
              </div>
              <div className="setting-item">
                <Text>语音速度: {voiceSpeed}x</Text>
                <Slider
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={voiceSpeed}
                  onChange={setVoiceSpeed}
                  className="speed-slider"
                />
              </div>
              <div className="setting-item">
                <Text>音调: {voicePitch}x</Text>
                <Slider
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={voicePitch}
                  onChange={setVoicePitch}
                  className="pitch-slider"
                />
              </div>
              <div className="setting-item">
                <Space>
                  <Switch
                    checked={preserveEmotion}
                    onChange={setPreserveEmotion}
                  />
                  <Text>保持情感特征</Text>
                </Space>
              </div>
            </div>

            <Button
              type="primary"
              size="large"
              loading={textCloningLoading}
              onClick={handleTextDrivenCloning}
              disabled={!refAudioFile || !targetText.trim()}
              icon={<ExperimentOutlined />}
              className="primary-button"
              block
            >
              开始克隆
            </Button>
          </Space>
        </Card>
      </Col>

      <Col xs={24} lg={12}>
        <Card className="result-card" bordered={false}>
          {textCloningLoading && (
            <div className="loading-container">
              <Progress type="circle" percent={70} />
              <div className="loading-text">正在克隆音色，请稍候...</div>
            </div>
          )}

          {textCloningResult && !textCloningLoading && (
            <div className="result-container">
              <div className="result-item">
                <div className="result-label">克隆音频:</div>
                <div className="result-content">
                  <audio controls className="audio-player">
                    <source src={textCloningResult.cloned_audio_url} type="audio/wav" />
                    您的浏览器不支持音频播放
                  </audio>
                </div>
              </div>

              <div className="result-item">
                <div className="result-label">相似度评分:</div>
                <div className="result-content">
                  <Progress 
                    percent={Math.round(textCloningResult.similarity_score * 100)} 
                    strokeColor={{
                      '0%': '#108ee9',
                      '100%': '#87d068',
                    }}
                  />
                </div>
              </div>

              <div className="result-item">
                <div className="result-label">质量评分:</div>
                <div className="result-content">
                  <Progress 
                    percent={Math.round(textCloningResult.quality_score * 100)} 
                    strokeColor={{
                      '0%': '#ffa940',
                      '100%': '#52c41a',
                    }}
                  />
                </div>
              </div>

              <div className="result-item">
                <div className="result-label">处理信息:</div>
                <div className="result-content">
                  <Space wrap>
                    <Tag color="blue">处理时间: {textCloningResult.processing_time.toFixed(2)} 秒</Tag>
                    <Tag color="green">音频时长: {textCloningResult.audio_duration.toFixed(2)} 秒</Tag>
                  </Space>
                </div>
              </div>

              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={() => {
                  const link = document.createElement('a')
                  link.href = textCloningResult.cloned_audio_url
                  link.download = `cloned_voice_${Date.now()}.wav`
                  link.click()
                }}
                className="download-button"
                block
              >
                下载克隆音频
              </Button>
            </div>
          )}

          {!textCloningResult && !textCloningLoading && (
            <div className="empty-state">
              <UserOutlined className="empty-icon" />
              <div className="empty-text">上传参考音频和输入文本开始克隆</div>
            </div>
          )}
        </Card>
      </Col>
    </Row>
  )

  return (
    <div className="module-container">
      <div className="module-header">
        <div className="module-icon">
          <ExperimentOutlined />
        </div>
        <div className="module-title-section">
          <Title level={2} className="module-title">方言音色克隆</Title>
          <Paragraph className="module-description">
            基于深度学习的音色克隆技术，保持方言特色和个人声音特征，支持文本驱动和音频驱动两种模式
          </Paragraph>
        </div>
      </div>

      {/* 功能切换标签 */}
      <div className="tab-navigation">
        <Button.Group>
          <Button 
            type={activeTab === 'text-driven' ? 'primary' : 'default'}
            onClick={() => setActiveTab('text-driven')}
            icon={<UserOutlined />}
          >
            文本驱动克隆
          </Button>
          <Button 
            type={activeTab === 'audio-driven' ? 'primary' : 'default'}
            onClick={() => setActiveTab('audio-driven')}
            icon={<SoundOutlined />}
          >
            音频驱动克隆
          </Button>
          <Button 
            type={activeTab === 'similarity' ? 'primary' : 'default'}
            onClick={() => setActiveTab('similarity')}
            icon={<BarChartOutlined />}
          >
            相似度分析
          </Button>
          <Button 
            type={activeTab === 'features' ? 'primary' : 'default'}
            onClick={() => setActiveTab('features')}
            icon={<SettingOutlined />}
          >
            特征提取
          </Button>
        </Button.Group>
      </div>

      <div className="module-content">
        {activeTab === 'text-driven' && renderTextDrivenCloning()}
        
        {activeTab === 'audio-driven' && (
          <Row gutter={[32, 32]}>
            <Col xs={24} lg={12}>
              <Card className="input-card" bordered={false}>
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                  {/* 参考音频 */}
                  <div className="upload-section">
                    <Text strong className="section-label">参考音频 (提供音色)</Text>
                    <Upload.Dragger {...createUploadProps(setRefAudioFile2, refAudioFile2)} className="audio-upload">
                      <p className="ant-upload-drag-icon">
                        <AudioOutlined />
                      </p>
                      <p className="ant-upload-text">上传参考音频</p>
                      <p className="ant-upload-hint">提供目标音色的音频文件</p>
                    </Upload.Dragger>
                    {refAudioFile2 && (
                      <Alert message={`参考音频: ${refAudioFile2.name}`} type="info" className="file-info" />
                    )}
                  </div>

                  {/* 目标音频 */}
                  <div className="upload-section">
                    <Text strong className="section-label">目标音频 (提供内容)</Text>
                    <Upload.Dragger {...createUploadProps(setTargetAudioFile, targetAudioFile)} className="audio-upload">
                      <p className="ant-upload-drag-icon">
                        <PlayCircleOutlined />
                      </p>
                      <p className="ant-upload-text">上传目标音频</p>
                      <p className="ant-upload-hint">提供语音内容的音频文件</p>
                    </Upload.Dragger>
                    {targetAudioFile && (
                      <Alert message={`目标音频: ${targetAudioFile.name}`} type="success" className="file-info" />
                    )}
                  </div>

                  {/* 音频克隆设置 */}
                  <div className="settings-section">
                    <Text strong className="section-label">克隆设置</Text>
                    <div className="setting-item">
                      <Text>音色混合比例: {Math.round(blendRatio * 100)}%</Text>
                      <Slider
                        min={0}
                        max={1}
                        step={0.1}
                        value={blendRatio}
                        onChange={setBlendRatio}
                        className="blend-slider"
                        marks={{
                          0: '保持原音色',
                          0.5: '混合',
                          1: '完全转换'
                        }}
                      />
                    </div>
                    <div className="setting-item">
                      <Text>处理质量:</Text>
                      <Select
                        value={quality}
                        onChange={setQuality}
                        className="quality-select"
                        options={[
                          { label: '高质量', value: 'high' },
                          { label: '中等质量', value: 'medium' },
                          { label: '快速模式', value: 'low' }
                        ]}
                      />
                    </div>
                    <div className="setting-item">
                      <Space>
                        <Switch
                          checked={preserveEmotion}
                          onChange={setPreserveEmotion}
                        />
                        <Text>保持情感</Text>
                      </Space>
                    </div>
                  </div>

                  <Button
                    type="primary"
                    size="large"
                    loading={audioCloningLoading}
                    onClick={handleAudioDrivenCloning}
                    disabled={!refAudioFile2 || !targetAudioFile}
                    icon={<ExperimentOutlined />}
                    className="primary-button"
                    block
                  >
                    开始音频克隆
                  </Button>
                </Space>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card className="result-card" bordered={false}>
                {audioCloningLoading && (
                  <div className="loading-container">
                    <Progress type="circle" percent={80} />
                    <div className="loading-text">正在进行音色转换...</div>
                  </div>
                )}

                {audioCloningResult && !audioCloningLoading && (
                  <div className="result-container">
                    <div className="result-item">
                      <div className="result-label">转换音频:</div>
                      <div className="result-content">
                        <audio controls className="audio-player">
                          <source src={audioCloningResult.cloned_audio_url} type="audio/wav" />
                          您的浏览器不支持音频播放
                        </audio>
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">音色相似度:</div>
                      <div className="result-content">
                        <Progress 
                          percent={Math.round(audioCloningResult.similarity_score * 100)} 
                          strokeColor="#722ed1"
                        />
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">转换质量:</div>
                      <div className="result-content">
                        <Progress 
                          percent={Math.round(audioCloningResult.quality_score * 100)} 
                          strokeColor="#eb2f96"
                        />
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">处理信息:</div>
                      <div className="result-content">
                        <Space wrap>
                          <Tag color="blue">处理时间: {audioCloningResult.processing_time.toFixed(2)} 秒</Tag>
                          <Tag color="green">音频时长: {audioCloningResult.audio_duration.toFixed(2)} 秒</Tag>
                        </Space>
                      </div>
                    </div>

                  </div>
                )}

                {!audioCloningResult && !audioCloningLoading && (
                  <div className="empty-state">
                    <SoundOutlined className="empty-icon" />
                    <div className="empty-text">上传参考音频和目标音频开始转换</div>
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        )}

        {/* 其他功能标签页的实现可以继续添加... */}
      </div>

      {/* 使用说明 */}
      <Card className="instructions-card" bordered={false}>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Title level={4}>文本驱动克隆</Title>
            <ul className="feature-list">
              <li>基于参考音频提取音色特征</li>
              <li>将目标文本转换为指定音色</li>
              <li>保持原有情感和韵律特征</li>
              <li>适用于个性化语音合成</li>
              <li>支持多种方言音色克隆</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <Title level={4}>音频驱动克隆</Title>
            <ul className="feature-list">
              <li>基于两个音频文件进行转换</li>
              <li>保持目标音频的语言内容</li>
              <li>转换为参考音频的音色</li>
              <li>支持音色混合比例调节</li>
              <li>适用于音色风格转换</li>
            </ul>
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default CloningModule
