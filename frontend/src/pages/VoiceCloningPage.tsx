import React, { useState } from 'react'
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
  Progress,
  Alert,
  Tag,
  Switch,
  Slider,
  Tooltip,
  List,
  Avatar
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
const { TabPane } = Tabs

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

const VoiceCloningPage: React.FC = () => {
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

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div className="text-center mb-24">
        <Title level={2}>🎭 方言音色克隆</Title>
        <Paragraph type="secondary" style={{ fontSize: '16px' }}>
          基于深度学习的音色克隆技术，保持方言特色和个人声音特征，支持文本驱动和音频驱动两种模式
        </Paragraph>
      </div>

      <Tabs defaultActiveKey="text-driven" size="large">
        {/* 文本驱动克隆 */}
        <TabPane tab={<span><UserOutlined />文本驱动克隆</span>} key="text-driven">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="参考音频与文本设置" className="mb-16">
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {/* 参考音频上传 */}
                  <div>
                    <Text strong>参考音频文件</Text>
                    <Upload.Dragger {...createUploadProps(setRefAudioFile, refAudioFile)} style={{ marginTop: 8 }}>
                      <p className="ant-upload-drag-icon">
                        <AudioOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
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
                        style={{ marginTop: 8 }}
                        closable
                        onClose={() => setRefAudioFile(null)}
                      />
                    )}
                  </div>

                  <Divider />

                  {/* 目标文本 */}
                  <div>
                    <Text strong>目标文本</Text>
                    <TextArea
                      value={targetText}
                      onChange={(e) => setTargetText(e.target.value)}
                      placeholder="请输入要用克隆音色合成的文本内容..."
                      autoSize={{ minRows: 4, maxRows: 8 }}
                      maxLength={500}
                      showCount
                      style={{ marginTop: 8 }}
                    />
                  </div>

                  <Divider />

                  {/* 克隆设置 */}
                  <div>
                    <Text strong>克隆设置</Text>
                    <div style={{ marginTop: 12 }}>
                      <Row gutter={[16, 16]}>
                        <Col span={12}>
                          <Text>语言:</Text>
                          <Select
                            value={language}
                            onChange={setLanguage}
                            options={languageOptions}
                            style={{ width: '100%', marginTop: 4 }}
                          />
                        </Col>
                        <Col span={12}>
                          <Text>质量:</Text>
                          <Select
                            value={quality}
                            onChange={setQuality}
                            style={{ width: '100%', marginTop: 4 }}
                            options={[
                              { label: '高质量', value: 'high' },
                              { label: '中等质量', value: 'medium' },
                              { label: '快速模式', value: 'low' }
                            ]}
                          />
                        </Col>
                        <Col span={12}>
                          <Text>语音速度: {voiceSpeed}x</Text>
                          <Slider
                            min={0.5}
                            max={2.0}
                            step={0.1}
                            value={voiceSpeed}
                            onChange={setVoiceSpeed}
                            style={{ marginTop: 8 }}
                          />
                        </Col>
                        <Col span={12}>
                          <Text>音调: {voicePitch}x</Text>
                          <Slider
                            min={0.5}
                            max={2.0}
                            step={0.1}
                            value={voicePitch}
                            onChange={setVoicePitch}
                            style={{ marginTop: 8 }}
                          />
                        </Col>
                        <Col span={24}>
                          <Space>
                            <Switch
                              checked={preserveEmotion}
                              onChange={setPreserveEmotion}
                            />
                            <Text>保持情感特征</Text>
                          </Space>
                        </Col>
                      </Row>
                    </div>
                  </div>

                  <Divider />

                  <Button
                    type="primary"
                    size="large"
                    loading={textCloningLoading}
                    onClick={handleTextDrivenCloning}
                    disabled={!refAudioFile || !targetText.trim()}
                    icon={<ExperimentOutlined />}
                    block
                  >
                    开始克隆
                  </Button>
                </Space>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="克隆结果" className="mb-16">
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
                        <audio controls style={{ width: '100%' }}>
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
                      <div className="result-label">处理时间:</div>
                      <div className="result-content">
                        {textCloningResult.processing_time.toFixed(2)} 秒
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">音频时长:</div>
                      <div className="result-content">
                        {textCloningResult.audio_duration.toFixed(2)} 秒
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">下载:</div>
                      <div className="result-content">
                        <Button
                          type="primary"
                          icon={<DownloadOutlined />}
                          onClick={() => {
                            const link = document.createElement('a')
                            link.href = textCloningResult.cloned_audio_url
                            link.download = `cloned_voice_${Date.now()}.wav`
                            link.click()
                          }}
                        >
                          下载克隆音频
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                {!textCloningResult && !textCloningLoading && (
                  <div className="text-center" style={{ padding: '40px 0', color: '#8c8c8c' }}>
                    <UserOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                    <div>上传参考音频和输入文本开始克隆</div>
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 音频驱动克隆 */}
        <TabPane tab={<span><SoundOutlined />音频驱动克隆</span>} key="audio-driven">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="音频文件上传" className="mb-16">
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {/* 参考音频 */}
                  <div>
                    <Text strong>参考音频 (提供音色)</Text>
                    <Upload.Dragger {...createUploadProps(setRefAudioFile2, refAudioFile2)} style={{ marginTop: 8 }}>
                      <p className="ant-upload-drag-icon">
                        <AudioOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
                      </p>
                      <p className="ant-upload-text">上传参考音频</p>
                      <p className="ant-upload-hint">提供目标音色的音频文件</p>
                    </Upload.Dragger>
                    {refAudioFile2 && (
                      <Alert message={`参考音频: ${refAudioFile2.name}`} type="info" style={{ marginTop: 8 }} />
                    )}
                  </div>

                  <Divider />

                  {/* 目标音频 */}
                  <div>
                    <Text strong>目标音频 (提供内容)</Text>
                    <Upload.Dragger {...createUploadProps(setTargetAudioFile, targetAudioFile)} style={{ marginTop: 8 }}>
                      <p className="ant-upload-drag-icon">
                        <PlayCircleOutlined style={{ fontSize: '32px', color: '#52c41a' }} />
                      </p>
                      <p className="ant-upload-text">上传目标音频</p>
                      <p className="ant-upload-hint">提供语音内容的音频文件</p>
                    </Upload.Dragger>
                    {targetAudioFile && (
                      <Alert message={`目标音频: ${targetAudioFile.name}`} type="success" style={{ marginTop: 8 }} />
                    )}
                  </div>

                  <Divider />

                  {/* 音频克隆设置 */}
                  <div>
                    <Text strong>克隆设置</Text>
                    <div style={{ marginTop: 12 }}>
                      <Row gutter={[16, 16]}>
                        <Col span={24}>
                          <Text>音色混合比例: {Math.round(blendRatio * 100)}%</Text>
                          <Slider
                            min={0}
                            max={1}
                            step={0.1}
                            value={blendRatio}
                            onChange={setBlendRatio}
                            style={{ marginTop: 8 }}
                            marks={{
                              0: '保持原音色',
                              0.5: '混合',
                              1: '完全转换'
                            }}
                          />
                        </Col>
                        <Col span={12}>
                          <Text>处理质量:</Text>
                          <Select
                            value={quality}
                            onChange={setQuality}
                            style={{ width: '100%', marginTop: 4 }}
                            options={[
                              { label: '高质量', value: 'high' },
                              { label: '中等质量', value: 'medium' },
                              { label: '快速模式', value: 'low' }
                            ]}
                          />
                        </Col>
                        <Col span={12}>
                          <Space>
                            <Switch
                              checked={preserveEmotion}
                              onChange={setPreserveEmotion}
                            />
                            <Text>保持情感</Text>
                          </Space>
                        </Col>
                      </Row>
                    </div>
                  </div>

                  <Divider />

                  <Button
                    type="primary"
                    size="large"
                    loading={audioCloningLoading}
                    onClick={handleAudioDrivenCloning}
                    disabled={!refAudioFile2 || !targetAudioFile}
                    icon={<ExperimentOutlined />}
                    block
                  >
                    开始音频克隆
                  </Button>
                </Space>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="转换结果" className="mb-16">
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
                        <audio controls style={{ width: '100%' }}>
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
                      <div className="result-label">处理时间:</div>
                      <div className="result-content">
                        {audioCloningResult.processing_time.toFixed(2)} 秒
                      </div>
                    </div>

                    <Button
                      type="primary"
                      icon={<DownloadOutlined />}
                      onClick={() => {
                        const link = document.createElement('a')
                        link.href = audioCloningResult.cloned_audio_url
                        link.download = `voice_converted_${Date.now()}.wav`
                        link.click()
                      }}
                      style={{ marginTop: 16 }}
                      block
                    >
                      下载转换音频
                    </Button>
                  </div>
                )}

                {!audioCloningResult && !audioCloningLoading && (
                  <div className="text-center" style={{ padding: '40px 0', color: '#8c8c8c' }}>
                    <SoundOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                    <div>上传参考音频和目标音频开始转换</div>
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 相似度分析 */}
        <TabPane tab={<span><BarChartOutlined />相似度分析</span>} key="similarity">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="音频文件对比" className="mb-16">
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <div>
                    <Text strong>音频文件 1</Text>
                    <Upload {...createUploadProps(setAudio1File, audio1File)} style={{ marginTop: 8 }}>
                      <Button icon={<AudioOutlined />} block>选择第一个音频文件</Button>
                    </Upload>
                    {audio1File && (
                      <Alert message={`文件1: ${audio1File.name}`} type="info" style={{ marginTop: 8 }} />
                    )}
                  </div>

                  <div>
                    <Text strong>音频文件 2</Text>
                    <Upload {...createUploadProps(setAudio2File, audio2File)} style={{ marginTop: 8 }}>
                      <Button icon={<AudioOutlined />} block>选择第二个音频文件</Button>
                    </Upload>
                    {audio2File && (
                      <Alert message={`文件2: ${audio2File.name}`} type="success" style={{ marginTop: 8 }} />
                    )}
                  </div>

                  <Button
                    type="primary"
                    size="large"
                    loading={similarityLoading}
                    onClick={handleSimilarityAnalysis}
                    disabled={!audio1File || !audio2File}
                    icon={<BarChartOutlined />}
                    block
                  >
                    分析相似度
                  </Button>
                </Space>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="相似度分析结果" className="mb-16">
                {similarityLoading && (
                  <div className="loading-container">
                    <Progress type="circle" percent={60} />
                    <div className="loading-text">正在分析音色相似度...</div>
                  </div>
                )}

                {similarityResult && !similarityLoading && (
                  <div className="result-container">
                    <div className="result-item">
                      <div className="result-label">整体相似度:</div>
                      <div className="result-content">
                        <Progress 
                          percent={Math.round(similarityResult.basic_analysis.overall_similarity * 100)} 
                          strokeColor="#1890ff"
                        />
                        <Tag color="blue" style={{ marginTop: 8 }}>
                          {similarityResult.similarity_level}
                        </Tag>
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">详细分析:</div>
                      <div className="result-content">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <div>
                            <Text>音调相似度: </Text>
                            <Progress 
                              percent={Math.round(similarityResult.basic_analysis.pitch_similarity * 100)} 
                              size="small"
                            />
                          </div>
                          <div>
                            <Text>音色相似度: </Text>
                            <Progress 
                              percent={Math.round(similarityResult.basic_analysis.timbre_similarity * 100)} 
                              size="small"
                            />
                          </div>
                          <div>
                            <Text>节奏相似度: </Text>
                            <Progress 
                              percent={Math.round(similarityResult.basic_analysis.rhythm_similarity * 100)} 
                              size="small"
                            />
                          </div>
                        </Space>
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">分析建议:</div>
                      <div className="result-content">
                        <List
                          size="small"
                          dataSource={similarityResult.recommendations}
                          renderItem={(item) => (
                            <List.Item>
                              <Text type="secondary">{item}</Text>
                            </List.Item>
                          )}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {!similarityResult && !similarityLoading && (
                  <div className="text-center" style={{ padding: '40px 0', color: '#8c8c8c' }}>
                    <BarChartOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                    <div>上传两个音频文件进行相似度分析</div>
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 特征提取 */}
        <TabPane tab={<span><SettingOutlined />特征提取</span>} key="features">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="音频特征分析" className="mb-16">
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <div>
                    <Text strong>音频文件</Text>
                    <Upload {...createUploadProps(setFeatureAudioFile, featureAudioFile)} style={{ marginTop: 8 }}>
                      <Button icon={<AudioOutlined />} block>选择音频文件</Button>
                    </Upload>
                    {featureAudioFile && (
                      <Alert message={`文件: ${featureAudioFile.name}`} type="info" style={{ marginTop: 8 }} />
                    )}
                  </div>

                  <Button
                    type="primary"
                    size="large"
                    loading={featureLoading}
                    onClick={handleFeatureExtraction}
                    disabled={!featureAudioFile}
                    icon={<SettingOutlined />}
                    block
                  >
                    提取特征
                  </Button>
                </Space>
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="特征分析结果" className="mb-16">
                {featureLoading && (
                  <div className="loading-container">
                    <Progress type="circle" percent={50} />
                    <div className="loading-text">正在提取音色特征...</div>
                  </div>
                )}

                {featureResult && !featureLoading && (
                  <div className="result-container">
                    <div className="result-item">
                      <div className="result-label">基础特征:</div>
                      <div className="result-content">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <div>基频: {featureResult.basic_features.fundamental_frequency.toFixed(1)} Hz</div>
                          <div>音调范围: {featureResult.basic_features.pitch_range.toFixed(1)}</div>
                          <div>语速: {featureResult.basic_features.speaking_rate} 词/分钟</div>
                          <div>平均音量: {(featureResult.basic_features.volume_mean * 100).toFixed(1)}%</div>
                        </Space>
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">音色描述:</div>
                      <div className="result-content">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <div>
                            <Tag color="blue">性别: {featureResult.voice_description.gender_prediction}</Tag>
                            <Tag color="green">年龄: {featureResult.voice_description.age_estimation}</Tag>
                          </div>
                          <div>
                            <Tag color="orange">质量: {featureResult.voice_description.voice_quality}</Tag>
                            <Tag color="purple">情感: {featureResult.voice_description.emotional_tone}</Tag>
                          </div>
                          <div>
                            <Tag color="cyan">口音: {featureResult.voice_description.accent_strength}</Tag>
                          </div>
                        </Space>
                      </div>
                    </div>

                    <div className="result-item">
                      <div className="result-label">音频信息:</div>
                      <div className="result-content">
                        <div>时长: {featureResult.duration.toFixed(2)} 秒</div>
                      </div>
                    </div>
                  </div>
                )}

                {!featureResult && !featureLoading && (
                  <div className="text-center" style={{ padding: '40px 0', color: '#8c8c8c' }}>
                    <SettingOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                    <div>上传音频文件开始特征提取</div>
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>

      {/* 使用说明 */}
      <Card title="音色克隆技术说明" className="mt-24">
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Title level={4}>文本驱动克隆</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>基于参考音频提取音色特征</li>
              <li>将目标文本转换为指定音色</li>
              <li>保持原有情感和韵律特征</li>
              <li>适用于个性化语音合成</li>
              <li>支持多种方言音色克隆</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <Title level={4}>音频驱动克隆</Title>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
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

export default VoiceCloningPage 