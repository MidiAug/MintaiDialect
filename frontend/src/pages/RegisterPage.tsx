import React from 'react'
import { Button, Card, Form, Input, Typography, message, Segmented } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

const { Title, Text } = Typography

const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const { register } = useAuth()
  const [scene, setScene] = React.useState<'email' | 'phone'>('email')
  const [countdown, setCountdown] = React.useState<number>(0)
  const [form] = Form.useForm()

  const onFinish = async (values: { username: string; password: string; confirm: string; email?: string; phone?: string; code?: string }) => {
    if (values.password !== values.confirm) {
      message.error('两次输入的密码不一致')
      return
    }
    if (scene === 'email' && !values.email) { message.error('请输入邮箱'); return }
    if (scene === 'phone' && !values.phone) { message.error('请输入手机号'); return }
    if (!values.code) { message.error('请输入验证码'); return }
    const payload: any = {
      username: values.username,
      password: values.password,
      email: scene === 'email' ? values.email : undefined,
      phone: scene === 'phone' ? values.phone : undefined,
    }
    if (values.code) payload.code = values.code
    const ok = await register(payload)
    if (ok) {
      message.success('注册成功，请登录')
      navigate('/login')
    } else {
      message.error('注册失败，请稍后再试')
    }
  }

  const handleSendCode = async () => {
    try {
      const email = form.getFieldValue('email')
      const phone = form.getFieldValue('phone')
      if (scene === 'email') {
        if (!email) { message.error('请先输入邮箱'); return }
        const { authAPI } = await import('@/services/api')
        await authAPI.sendEmailCode(email, 'register')
        message.success('验证码已发送至邮箱')
      } else {
        if (!phone) { message.error('请先输入手机号'); return }
        const { authAPI } = await import('@/services/api')
        await authAPI.sendSmsCode(phone, 'register')
        message.success('验证码已发送至手机')
      }
      setCountdown(60)
    } catch (e) {
      message.error('验证码发送失败，请稍后再试')
    }
  }

  React.useEffect(() => {
    if (countdown <= 0) return
    const timer = setInterval(() => setCountdown((s) => s - 1), 1000)
    return () => clearInterval(timer)
  }, [countdown])

  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
      <Card style={{ width: 420 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>注册</Title>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item>
            <Segmented
              options={[{ label: '邮箱注册', value: 'email' }, { label: '手机注册', value: 'phone' }]}
              value={scene}
              onChange={(v) => setScene(v as 'email' | 'phone')}
            />
          </Form.Item>
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="请输入用户名" />
          </Form.Item>
          {scene === 'email' ? (
            <Form.Item label="邮箱" name="email" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入正确的邮箱地址' }]}> 
              <Input placeholder="name@example.com" />
            </Form.Item>
          ) : (
            <Form.Item label="手机号" name="phone" rules={[{ required: true, message: '请输入手机号' }, { pattern: /^\+?\d{6,15}$/g, message: '请输入正确的手机号' }]}> 
              <Input placeholder="例如：+8613800138000 或 13800138000" />
            </Form.Item>
          )}
          <Form.Item label="验证码" name="code" rules={[{ required: true, message: '请输入验证码' }]}> 
            <Input
              placeholder="6位验证码"
              maxLength={6}
              inputMode="numeric"
              addonAfter={
                <Button type="link" disabled={countdown>0} onClick={(e) => { e.preventDefault(); handleSendCode() }}>
                  {countdown>0 ? `重发(${countdown}s)` : '发送验证码'}
                </Button>
              }
            />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item label="确认密码" name="confirm" dependencies={["password"]} rules={[{ required: true, message: '请再次输入密码' }]}>
            <Input.Password placeholder="请再次输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>注册</Button>
          </Form.Item>
          <Text type="secondary">已有账户？</Text>
          <Button type="link" onClick={() => navigate('/login')}>去登录</Button>
        </Form>
      </Card>
    </div>
  )
}

export default RegisterPage


