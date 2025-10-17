import React from 'react'
import { Typography, Row, Col, Card, Button, Space, Statistic, Tag } from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  SoundOutlined,
  TranslationOutlined,
  MessageOutlined,
  UserOutlined,
  RocketOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
} from '@ant-design/icons'

const { Title, Paragraph, Text } = Typography

const HomePage: React.FC = () => {
  const navigate = useNavigate()

  // 主要功能卡片
  const features = [
    {
      icon: <SoundOutlined className="card-icon" />,
      title: '语音文本互转',
      description: '高精度的方言语音识别和文本转语音服务，支持实时和批量处理',
      path: '/asr-tts',
      tags: ['ASR', 'TTS', '实时处理'],
    },
    {
      icon: <TranslationOutlined className="card-icon" />,
      title: '方言语音互译',
      description: '方言与普通话之间的双向语音翻译，支持多种闽台方言',
      path: '/speech-translation',
      tags: ['语音翻译', '方言转换', '跨语言'],
    },
    {
      icon: <MessageOutlined className="card-icon" />,
      title: '智能语音交互',
      description: '方言语音对话和问答系统，支持多轮对话和情感识别',
      path: '/voice-interaction',
      tags: ['智能对话', '问答系统', '情感分析'],
    },
    {
      icon: <UserOutlined className="card-icon" />,
      title: '方言音色克隆',
      description: '基于深度学习的音色克隆技术，保持方言特色和个人声音特征',
      path: '/voice-cloning',
      tags: ['音色克隆', '声纹识别', '个性化'],
    },
  ]

  // 技术特色
  const highlights = [
    {
      icon: <ThunderboltOutlined style={{ color: '#faad14', fontSize: '24px' }} />,
      title: '高性能处理',
      description: '采用最新AI技术，毫秒级响应',
    },
    {
      icon: <SafetyOutlined style={{ color: '#52c41a', fontSize: '24px' }} />,
      title: '数据安全',
      description: '本地化部署，隐私数据不上云',
    },
    {
      icon: <GlobalOutlined style={{ color: '#1890ff', fontSize: '24px' }} />,
      title: '多方言支持',
      description: '支持闽南话、客家话、台湾话等',
    },
    {
      icon: <RocketOutlined style={{ color: '#722ed1', fontSize: '24px' }} />,
      title: '持续优化',
      description: '模型持续训练，性能不断提升',
    },
  ]

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* 头部介绍区域 */}
      <div className="text-center mb-24" style={{ padding: '40px 0' }}>
        <div
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: '16px',
            padding: '60px 40px',
            color: 'white',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* 背景装饰 */}
          <div
            style={{
              position: 'absolute',
              top: '-50%',
              right: '-20%',
              width: '200px',
              height: '200px',
              background: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '50%',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: '-30%',
              left: '-10%',
              width: '150px',
              height: '150px',
              background: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '50%',
            }}
          />
          
          <Title level={1} style={{ color: 'white', marginBottom: '16px', fontSize: '48px' }}>
            🎤 闽台方言大模型系统
          </Title>
          <Paragraph 
            style={{ 
              color: 'rgba(255, 255, 255, 0.9)', 
              fontSize: '20px', 
              marginBottom: '32px',
              maxWidth: '800px',
              margin: '0 auto 32px'
            }}
          >
            基于先进人工智能技术的方言语音处理平台，致力于传承和发扬闽台方言文化，
            提供语音识别、语音合成、语音翻译、智能对话和音色克隆等全方位服务。
          </Paragraph>
          
          <Space size="large">
            <Button 
              type="primary" 
              size="large" 
              icon={<RocketOutlined />}
              onClick={() => navigate('/asr-tts')}
              style={{
                background: 'rgba(255, 255, 255, 0.2)',
                borderColor: 'rgba(255, 255, 255, 0.3)',
                backdropFilter: 'blur(10px)',
              }}
            >
              立即体验
            </Button>
            <Button 
              size="large" 
              ghost
              onClick={() => navigate('/demo')}
            >
              查看演示
            </Button>
          </Space>
        </div>
      </div>

      {/* 统计数据 */}
      <Row gutter={[24, 24]} className="mb-24">
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="支持方言"
              value={4}
              suffix="种"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="音频格式"
              value={5}
              suffix="种"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="识别准确率"
              value={95}
              suffix="%"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="响应时间"
              value={200}
              suffix="ms"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 核心功能展示 */}
      <div id="features" className="mb-24">
        <Title level={2} className="text-center mb-24">
          🚀 核心功能
        </Title>
        <Row gutter={[24, 24]}>
          {features.map((feature, index) => (
            <Col xs={24} sm={12} lg={6} key={index}>
              <Card
                hoverable
                className="feature-card fade-in"
                style={{ 
                  height: '100%',
                  animationDelay: `${index * 0.1}s`,
                }}
                onClick={() => navigate(feature.path)}
              >
                <div className="text-center">
                  {feature.icon}
                  <Title level={4} className="card-title">
                    {feature.title}
                  </Title>
                  <Paragraph className="card-description">
                    {feature.description}
                  </Paragraph>
                  <div style={{ marginTop: '16px' }}>
                    {feature.tags.map((tag, tagIndex) => (
                      <Tag key={tagIndex} color="blue" style={{ margin: '2px' }}>
                        {tag}
                      </Tag>
                    ))}
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      {/* 技术特色 */}
      <div className="mb-24">
        <Title level={2} className="text-center mb-24">
          ✨ 技术特色
        </Title>
        <Row gutter={[24, 24]}>
          {highlights.map((highlight, index) => (
            <Col xs={24} sm={12} lg={6} key={index}>
              <Card
                style={{ 
                  height: '100%', 
                  textAlign: 'center',
                  border: '1px solid #f0f0f0',
                }}
              >
                <Space direction="vertical" size="middle">
                  {highlight.icon}
                  <Title level={4} style={{ margin: 0 }}>
                    {highlight.title}
                  </Title>
                  <Text type="secondary">
                    {highlight.description}
                  </Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      {/* 应用场景 */}
      <div className="mb-24">
        <Title level={2} className="text-center mb-24">
          🎯 应用场景
        </Title>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={8}>
            <Card title="文化传承" bordered={false}>
              <ul style={{ paddingLeft: '20px', color: '#595959' }}>
                <li>方言音视频采访文字化</li>
                <li>方言有声读物制作</li>
                <li>方言影视作品配音</li>
                <li>方言教学辅助</li>
              </ul>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card title="跨地交流" bordered={false}>
              <ul style={{ paddingLeft: '20px', color: '#595959' }}>
                <li>跨方言地区沟通</li>
                <li>旅游语言服务</li>
                <li>商务会议翻译</li>
                <li>远程协作支持</li>
              </ul>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card title="智能应用" bordered={false}>
              <ul style={{ paddingLeft: '20px', color: '#595959' }}>
                <li>方言智能客服</li>
                <li>语音导航系统</li>
                <li>智能家居控制</li>
                <li>个性化语音助手</li>
              </ul>
            </Card>
          </Col>
        </Row>
      </div>

      {/* 开始使用 */}
      <Card
        style={{
          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
          border: 'none',
          color: 'white',
          textAlign: 'center',
          marginBottom: '24px',
        }}
      >
        <Title level={2} style={{ color: 'white', marginBottom: '16px' }}>
          🎉 开始您的方言AI之旅
        </Title>
        <Paragraph style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '16px', marginBottom: '24px' }}>
          选择您感兴趣的功能，立即体验先进的方言语音处理技术
        </Paragraph>
        <Space size="large" wrap>
          <Button 
            type="primary" 
            size="large"
            onClick={() => navigate('/asr-tts')}
            style={{ background: 'rgba(255, 255, 255, 0.2)', borderColor: 'transparent' }}
          >
            语音识别
          </Button>
          <Button 
            type="primary" 
            size="large"
            onClick={() => navigate('/speech-translation')}
            style={{ background: 'rgba(255, 255, 255, 0.2)', borderColor: 'transparent' }}
          >
            语音翻译
          </Button>
          <Button 
            type="primary" 
            size="large"
            onClick={() => navigate('/voice-interaction')}
            style={{ background: 'rgba(255, 255, 255, 0.2)', borderColor: 'transparent' }}
          >
            智能对话
          </Button>
          <Button 
            type="primary" 
            size="large"
            onClick={() => navigate('/voice-cloning')}
            style={{ background: 'rgba(255, 255, 255, 0.2)', borderColor: 'transparent' }}
          >
            音色克隆
          </Button>
        </Space>
      </Card>
    </div>
  )
}

export default HomePage 