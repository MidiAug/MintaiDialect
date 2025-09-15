import React from 'react'
import { Layout, Menu, Typography, Button, Dropdown } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { UserOutlined, HomeOutlined, LogoutOutlined } from '@ant-design/icons'
import { useAuth } from '@/contexts/AuthContext'

const { Header } = Layout
const { Title } = Typography

const JiagengHeader: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, user, logout } = useAuth()

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
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
            background: 'linear-gradient(135deg, #667eea, #764ba2)',
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
          庚
        </div>
        <Title 
          level={4} 
          style={{ 
            margin: 0, 
            color: '#595959',
            fontWeight: 600,
          }}
        >
          数字嘉庚
        </Title>
      </div>

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

      {isAuthenticated ? (
        <Dropdown
          menu={{
            items: [
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

export default JiagengHeader


