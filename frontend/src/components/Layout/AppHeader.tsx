import React from 'react'
import { Layout, Menu, Typography } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  HomeOutlined,
  SoundOutlined,
  TranslationOutlined,
  MessageOutlined,
  UserOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'

const { Header } = Layout
const { Title } = Typography

const AppHeader: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  // 菜单项配置
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/asr-tts',
      icon: <SoundOutlined />,
      label: '语音文本互转',
    },
    {
      key: '/speech-translation',
      icon: <TranslationOutlined />,
      label: '语音互译',
    },
    {
      key: '/voice-interaction',
      icon: <MessageOutlined />,
      label: '语音交互',
    },
    {
      key: '/voice-cloning',
      icon: <ExperimentOutlined />,
      label: '音色克隆',
    },
    {
      key: '/digital-jiageng',
      icon: <UserOutlined />,
      label: '数字嘉庚',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        padding: '0 24px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      }}
    >
      {/* Logo 和标题 */}
      <div 
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          cursor: 'pointer',
          marginRight: 48 
        }}
        onClick={() => navigate('/')}
      >
        <div
          style={{
            width: 40,
            height: 40,
            background: 'linear-gradient(135deg, #1890ff, #52c41a)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '20px',
            fontWeight: 'bold',
            marginRight: 12,
          }}
        >
          方
        </div>
        <Title 
          level={4} 
          style={{ 
            margin: 0, 
            color: '#1890ff',
            fontWeight: 600,
          }}
        >
          闽台方言大模型
        </Title>
      </div>

      {/* 导航菜单 */}
      <Menu
        theme="light"
        mode="horizontal"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
        style={{
          flex: 1,
          border: 'none',
          fontSize: '16px',
        }}
      />

      {/* 右侧信息 */}
      <div style={{ color: '#8c8c8c', fontSize: '14px' }}>
        AI语音处理平台
      </div>
    </Header>
  )
}

export default AppHeader 