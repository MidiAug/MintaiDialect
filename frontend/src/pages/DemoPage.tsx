import React, { useEffect, useState } from 'react'
import { Typography, Card, Button, Row, Col } from 'antd'
import { 
  SoundOutlined, 
  PlayCircleOutlined, 
  TranslationOutlined, 
  MessageOutlined, 
  ArrowDownOutlined,
  StarOutlined
} from '@ant-design/icons'
import '@/styles/new-home.css'

const { Title, Paragraph } = Typography

// 功能模块组件
import ASRModule from '@/components/Modules/ASRModule'
import TTSModule from '@/components/Modules/TTSModule'
import ContentUnderstandingModule from '@/components/Modules/ContentUnderstandingModule'
import AIDialogueModule from '@/components/Modules/AIDialogueModule'

interface FeatureCard {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  color: string
  gradient: string
}

const NewHomePage: React.FC = () => {
  const [activeSection, setActiveSection] = useState('hero')
  
  // 功能卡片数据
  const features: FeatureCard[] = [
    {
      id: 'asr',
      title: '方言语音识别',
      description: '高精度闽台方言语音转文字，支持多种方言和音频格式',
      icon: <SoundOutlined />,
      color: '#1890ff',
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    {
      id: 'tts',
      title: '方言语音合成',
      description: '将文字转换为自然的方言语音，保持方言特色和语调',
      icon: <PlayCircleOutlined />,
      color: '#52c41a',
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
    },
    {
      id: 'content',
      title: '音频内容理解',
      description: '基于多模态大模型，智能分析音频内容，生成摘要和关键信息',
      icon: <MessageOutlined />,
      color: '#fa8c16',
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
    },
    {
      id: 'dialogue',
      title: '智能对话音频',
      description: '输入文本问题，AI生成回答并转换为方言音频',
      icon: <TranslationOutlined />,
      color: '#eb2f96',
      gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
    }
  ]

  // 滚动到指定区域
  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId)
    if (element) {
      element.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      })
    }
  }

  // 监听滚动位置
  useEffect(() => {
    const handleScroll = () => {
      const sections = ['hero', 'features', 'asr', 'tts', 'content', 'dialogue']
      const scrollPosition = window.scrollY + 100

      for (const section of sections) {
        const element = document.getElementById(section)
        if (element) {
          const { offsetTop, offsetHeight } = element
          if (scrollPosition >= offsetTop && scrollPosition < offsetTop + offsetHeight) {
            setActiveSection(section)
            break
          }
        }
      }
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div className="new-home-page">
      {/* Hero 区域 */}
      <section id="hero" className="hero-section">
        <div className="hero-background">
          <div className="stars"></div>
          <div className="moon"></div>
        </div>
        
        <div className="hero-content">
          
          <div className="hero-text">
            <Title className="hero-title">
              <span className="brand-name">闽音智聆</span>
              <br />
              <span className="main-title">智能语音处理平台</span>
            </Title>
            
            <Paragraph className="hero-subtitle">
              XMU DeepLIT
            </Paragraph>
            
            <div className="hero-actions">
              <Button 
                type="primary" 
                size="large" 
                icon={<ArrowDownOutlined />}
                onClick={() => scrollToSection('features')}
                className="scroll-button"
              >
                探索功能
              </Button>
              <Button 
                size="large" 
                icon={<StarOutlined />}
                className="demo-button"
              >
                查看演示
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* 所有功能模块的大容器 */}
      <div className="all-modules-wrapper">
        <Card className="all-modules-container" bordered={true}>
          {/* 功能概览区域 */}
          <section id="features" className="features-section">
            <div className="features-container">
              <div className="section-header">
                <Title level={2} className="section-title">
                  核心功能
                </Title>
                <Paragraph className="section-description">
                  基于先进的语音AI技术，为闽台方言提供全方位的智能语音处理服务
                </Paragraph>
              </div>

              <Card className="features-main-card" bordered={true}>
                <Row gutter={[24, 24]} className="features-grid">
                  {features.map((feature) => (
                    <Col xs={24} sm={12} md={6} lg={6} key={feature.id}>
                      <Card 
                        className="feature-card"
                        hoverable
                        onClick={() => scrollToSection(feature.id)}
                        bordered={true}
                        style={{
                          background: feature.gradient,
                          borderRadius: '12px',
                          overflow: 'hidden',
                          height: '280px'
                        }}
                      >
                        <div className="feature-card-content">
                          <div className="feature-icon">
                            {feature.icon}
                          </div>
                          <Title level={4} className="feature-title">
                            {feature.title}
                          </Title>
                          <Paragraph className="feature-description">
                            {feature.description}
                          </Paragraph>
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card>
            </div>
          </section>

          {/* 功能模块区域 */}
          <section id="asr" className="module-section">
            <div className="module-container">
              <ASRModule />
            </div>
          </section>

          <section id="tts" className="module-section">
            <div className="module-container">
              <TTSModule />
            </div>
          </section>

          <section id="content" className="module-section">
            <div className="module-container">
              <ContentUnderstandingModule />
            </div>
          </section>

          <section id="dialogue" className="module-section">
            <div className="module-container">
              <AIDialogueModule />
            </div>
          </section>
        </Card>
      </div>

      {/* 导航指示器 */}
      <div className="scroll-indicator">
        <div className="indicator-dots">
          {['hero', 'features', 'asr', 'tts', 'content', 'dialogue'].map((section) => (
            <div 
              key={section}
              className={`indicator-dot ${activeSection === section ? 'active' : ''}`}
              onClick={() => scrollToSection(section)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default NewHomePage
