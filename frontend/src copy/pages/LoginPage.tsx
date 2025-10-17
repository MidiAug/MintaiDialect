import React from 'react'
import { Button, Card, Form, Input, Typography, message } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

const { Title, Text } = Typography

const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { loginWithPassword } = useAuth()

  const from = (location.state as any)?.from?.pathname || '/'

  const onFinish = async (values: { username: string; password: string }) => {
    const ok = await loginWithPassword(values.username, values.password)
    if (ok) {
      message.success('登录成功')
      navigate(from, { replace: true })
    } else {
      message.error('登录失败，请检查用户名或密码')
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
      <Card style={{ width: 420 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>登录</Title>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>登录</Button>
          </Form.Item>
          <Text type="secondary">还没有账户？</Text>
          <Button type="link" onClick={() => navigate('/register')}>去注册</Button>
        </Form>
      </Card>
    </div>
  )
}

export default LoginPage


