import React from 'react'
import { Layout, Menu, Typography, Button, Dropdown } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  HomeOutlined,
  SoundOutlined,
  TranslationOutlined,
  MessageOutlined,
  UserOutlined,
  ExperimentOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useAuth } from '@/contexts/AuthContext'

const { Header } = Layout
const { Title } = Typography

const AppHeader: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, user, logout } = useAuth()

  // 菜单项配置
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    ...(isAuthenticated
      ? [
          { key: '/asr-tts', icon: <SoundOutlined />, label: '语音文本互转' },
          { key: '/speech-translation', icon: <TranslationOutlined />, label: '语音互译' },
          { key: '/voice-interaction', icon: <MessageOutlined />, label: '语音交互' },
          { key: '/voice-cloning', icon: <ExperimentOutlined />, label: '音色克隆' },
          { key: '/digital-jiageng', icon: <UserOutlined />, label: '数字嘉庚' },
        ]
      : [])
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

      {/* 右侧：登录/注册 或 用户下拉 */}
      {isAuthenticated ? (
        <Dropdown
          menu={{
            items: [
              {
                key: 'account',
                icon: <UserOutlined />,
                label: '个人信息',
                onClick: () => navigate('/account'),
              },
              {
                type: 'divider' as const,
              },
              {
                key: 'logout',
                icon: <LogoutOutlined />,
                label: '退出登录',
                onClick: () => logout(),
              },
            ],
          }}
        >
          <Button type="text" icon={<UserOutlined />}>
            {user?.username || '用户'}
          </Button>
        </Dropdown>
      ) : (
        <div style={{ display: 'flex', gap: 8 }}>
          <Button onClick={() => navigate('/login')}>登录</Button>
          <Button type="primary" onClick={() => navigate('/register')}>注册</Button>
        </div>
      )}
    </Header>
  )
}

export default AppHeader 