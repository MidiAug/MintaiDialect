import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  message,
  Tag,
  Popconfirm,
  Typography,
  Empty,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { authAPI, type AdminUserRecord } from '@/services/api'

interface UserFormValues {
  username: string
  password?: string
  email?: string
  phone?: string
}

const AdminUsersPage: React.FC = () => {
  const [users, setUsers] = useState<AdminUserRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUserRecord | null>(null)
  const [form] = Form.useForm<UserFormValues>()

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await authAPI.listUsers()
      if (!res.success) {
        throw new Error(res.message || '获取用户失败')
      }
      setUsers(res.data?.users || [])
    } catch (err) {
      const tip = err instanceof Error ? err.message : '获取用户失败'
      message.error(tip)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const openCreateModal = () => {
    setEditingUser(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEditModal = (user: AdminUserRecord) => {
    setEditingUser(user)
    form.setFieldsValue({
      username: user.username,
      email: user.email || '',
      phone: user.phone || '',
      password: '',
    })
    setModalOpen(true)
  }

  const handleDelete = async (user: AdminUserRecord) => {
    if (user.username === 'admin') {
      message.warning('不可删除管理员账号')
      return
    }
    try {
      await authAPI.deleteUser(user.id)
      message.success('用户已删除')
      fetchUsers()
    } catch (err) {
      const tip = err instanceof Error ? err.message : '删除失败'
      message.error(tip)
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      if (editingUser) {
        const payload: UserFormValues = {
          email: values.email,
          phone: values.phone,
        }
        if (values.password) {
          payload.password = values.password
        }
        await authAPI.updateUser(editingUser.id, payload)
        message.success('用户信息已更新')
      } else {
        await authAPI.createUser({
          username: values.username,
          password: values.password || '',
          email: values.email,
          phone: values.phone,
        })
        message.success('用户已创建')
      }
      setModalOpen(false)
      fetchUsers()
    } catch (err) {
      if (err instanceof Error) {
        message.error(err.message)
      } else if ((err as any)?.errorFields) {
        // 表单校验错误已在控件内提示
      } else {
        message.error('操作失败')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const columns: ColumnsType<AdminUserRecord> = useMemo(
    () => [
      {
        title: '用户名',
        dataIndex: 'username',
        key: 'username',
        render: (text: string) => (
          <Space size={4}>
            <span>{text}</span>
            {text === 'admin' && <Tag color="gold">管理员</Tag>}
          </Space>
        ),
      },
      {
        title: '邮箱',
        dataIndex: 'email',
        key: 'email',
        render: (value: string | null | undefined) => value || <Tag color="default">未设置</Tag>,
      },
      {
        title: '手机号',
        dataIndex: 'phone',
        key: 'phone',
        render: (value: string | null | undefined) => value || <Tag color="default">未设置</Tag>,
      },
      {
        title: '操作',
        key: 'action',
        width: 200,
        render: (_: unknown, record) => (
          <Space>
            <Button type="link" onClick={() => openEditModal(record)}>
              编辑
            </Button>
            <Popconfirm
              title="确认删除该用户？"
              description="删除后不可恢复，请谨慎操作"
              onConfirm={() => handleDelete(record)}
              okText="确认"
              cancelText="取消"
              disabled={record.username === 'admin'}
            >
              <Button type="link" danger disabled={record.username === 'admin'}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    []
  )

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="用户管理"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchUsers} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              新建用户
            </Button>
          </Space>
        }
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
          仅管理员可见的用户管理界面，可快速完成增删改查操作。
        </Typography.Paragraph>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={users}
          columns={columns}
          locale={{
            emptyText: <Empty description="暂无用户数据" />,
          }}
        />
      </Card>

      <Modal
        title={editingUser ? `编辑用户：${editingUser.username}` : '创建新用户'}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false)
          form.resetFields()
        }}
        onOk={handleSubmit}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ username: '', email: '', phone: '' }}>
          <Form.Item
            label="用户名"
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名长度至少3个字符' },
            ]}
          >
            <Input placeholder="请输入用户名" disabled={Boolean(editingUser)} />
          </Form.Item>
          <Form.Item
            label={editingUser ? '重置密码（可选）' : '密码'}
            name="password"
            rules={
              editingUser
                ? [{ min: 6, message: '密码长度至少6位' }]
                : [
                    { required: true, message: '请输入密码' },
                    { min: 6, message: '密码长度至少6位' },
                  ]
            }
          >
            <Input.Password placeholder={editingUser ? '留空则不修改' : '请输入密码'} />
          </Form.Item>
          <Form.Item label="邮箱" name="email">
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item label="手机号" name="phone">
            <Input placeholder="请输入手机号" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AdminUsersPage

