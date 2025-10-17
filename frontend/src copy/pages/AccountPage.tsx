import React from 'react'
import { Card, Form, Input, Button, Typography, Space, message } from 'antd'
import { useAuth } from '@/contexts/AuthContext'

const { Title, Text } = Typography

const AccountPage: React.FC = () => {
  const { user, updateProfile, changePassword, logout } = useAuth()

  const onUpdateProfile = async (values: { email?: string; phone?: string }) => {
    const ok = await updateProfile({ email: values.email, phone: values.phone })
    if (ok) message.success('资料已更新')
  }

  const onChangePassword = async (values: { oldPassword: string; newPassword: string; confirm: string }) => {
    if (values.newPassword !== values.confirm) {
      message.error('两次输入的新密码不一致')
      return
    }
    const ok = await changePassword(values.oldPassword, values.newPassword)
    if (ok) message.success('密码已更新')
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
      <Space direction="vertical" size={24} style={{ width: 600 }}>
        <Card>
          <Title level={4}>账户资料</Title>
          <Text type="secondary">用户名：{user?.username}</Text>
          <Form layout="vertical" onFinish={onUpdateProfile} initialValues={{ email: user?.email, phone: user?.phone }} style={{ marginTop: 16 }}>
            <Form.Item label="邮箱" name="email" rules={[{ type: 'email', message: '请输入正确的邮箱地址' }]}>
              <Input placeholder="name@example.com" />
            </Form.Item>
            <Form.Item label="手机号" name="phone" rules={[{ pattern: /^\+?\d{6,15}$/g, message: '请输入正确的手机号' }]}>
              <Input placeholder="例如：+8613800138000 或 13800138000" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">保存资料</Button>
            </Form.Item>
          </Form>
        </Card>

        <Card>
          <Title level={4}>修改密码</Title>
          <Form layout="vertical" onFinish={onChangePassword}>
            <Form.Item label="当前密码" name="oldPassword" rules={[{ required: true, message: '请输入当前密码' }]}>
              <Input.Password placeholder="请输入当前密码" />
            </Form.Item>
            <Form.Item label="新密码" name="newPassword" rules={[{ required: true, message: '请输入新密码' }]}>
              <Input.Password placeholder="请输入新密码" />
            </Form.Item>
            <Form.Item label="确认新密码" name="confirm" dependencies={["newPassword"]} rules={[{ required: true, message: '请再次输入新密码' }]}>
              <Input.Password placeholder="请再次输入新密码" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">更新密码</Button>
            </Form.Item>
          </Form>
        </Card>

        <Card>
          <Title level={4}>安全</Title>
          <Button danger onClick={logout}>退出登录</Button>
        </Card>
      </Space>
    </div>
  )
}

export default AccountPage


