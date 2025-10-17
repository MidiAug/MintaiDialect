import React from 'react'
import { Layout, Typography, Space, Divider } from 'antd'
import { GithubOutlined, MailOutlined, HeartFilled } from '@ant-design/icons'

const { Footer } = Layout
const { Text, Link } = Typography

const AppFooter: React.FC = () => {
  return (
    <Footer
      style={{
        textAlign: 'center',
        background: '#001529',
        color: 'rgba(255, 255, 255, 0.65)',
        padding: '24px 50px',
      }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        {/* 主要信息 */}
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text style={{ color: 'rgba(255, 255, 255, 0.85)', fontSize: '16px' }}>
              闽台方言大模型系统
            </Text>
            <br />
            <Text style={{ color: 'rgba(255, 255, 255, 0.65)' }}>
              让方言在AI时代焕发新生，传承闽台文化瑰宝
            </Text>
          </div>

          {/* 功能链接 */}
          <Space split={<Divider type="vertical" style={{ borderColor: 'rgba(255, 255, 255, 0.3)' }} />}>
            <Link href="/asr-tts" style={{ color: 'rgba(255, 255, 255, 0.65)' }}>
              语音识别
            </Link>
            <Link href="/speech-translation" style={{ color: 'rgba(255, 255, 255, 0.65)' }}>
              语音翻译
            </Link>
            <Link href="/voice-interaction" style={{ color: 'rgba(255, 255, 255, 0.65)' }}>
              智能对话
            </Link>
            <Link href="/voice-cloning" style={{ color: 'rgba(255, 255, 255, 0.65)' }}>
              音色克隆
            </Link>
          </Space>

          {/* 技术栈信息 */}
          <div>
            <Text style={{ color: 'rgba(255, 255, 255, 0.45)', fontSize: '12px' }}>
              技术栈: React 18 + TypeScript + FastAPI + Python
            </Text>
            <br />
            <Text style={{ color: 'rgba(255, 255, 255, 0.45)', fontSize: '12px' }}>
              支持格式: WAV, MP3, FLAC, M4A, OGG | 支持方言: 闽南话, 客家话, 台湾话, 普通话
            </Text>
          </div>

          {/* 联系方式 */}
          <Space>
            <Link 
              href="#" 
              style={{ color: 'rgba(255, 255, 255, 0.65)' }}
              title="GitHub项目地址"
            >
              <GithubOutlined style={{ fontSize: '16px' }} />
            </Link>
            <Link 
              href="mailto:contact@example.com" 
              style={{ color: 'rgba(255, 255, 255, 0.65)' }}
              title="联系邮箱"
            >
              <MailOutlined style={{ fontSize: '16px' }} />
            </Link>
          </Space>

          {/* 版权信息 */}
          <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: '16px' }}>
            <Text style={{ color: 'rgba(255, 255, 255, 0.45)', fontSize: '12px' }}>
              © 2024 闽台方言大模型团队. All rights reserved.
            </Text>
            <br />
            <Text style={{ color: 'rgba(255, 255, 255, 0.45)', fontSize: '12px' }}>
              Built with <HeartFilled style={{ color: '#ff4d4f', margin: '0 4px' }} /> for dialect preservation
            </Text>
          </div>
        </Space>
      </div>
    </Footer>
  )
}

export default AppFooter 