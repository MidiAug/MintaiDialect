// 厦门好食的物件真济，沙茶面、海蛎煎，讲到我就流口水矣！你敢有兴趣知影佗一味卡合汝的口味？
import React, { useState, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Table,
  Input
} from 'antd'
import { 
  MessageOutlined
} from '@ant-design/icons'
import { fetchCsv } from '@/utils/csv'

const { Title, Paragraph } = Typography
const { TextArea } = Input

interface DialogueRowData {
  key: string
  instruction: string
  inputText: string
  outputText: string
  outputAudio: string
}

const AIDialogueModule: React.FC = () => {
  // 控制面板与批量操作已移除
  const [tableData, setTableData] = useState<DialogueRowData[]>([])

  useEffect(() => {
    ;(async () => {
      try {
        const rows = await fetchCsv<{instruction: string; inputText: string; outputText?: string; outputAudio?: string}>('/data/dialogue_data.csv')
        const mapped: DialogueRowData[] = rows.map((r, idx) => ({
          key: String(idx + 1),
          instruction: r.instruction,
          inputText: r.inputText,
          outputText: r.outputText || '',
          outputAudio: r.outputAudio || ''
        }))
        setTableData(mapped)
      } catch (err) {
        console.error('Load Dialogue CSV failed', err)
      }
    })()
  }, [])

  // 语言选项（控制面板已移除，不再需要）
  // 单行对话操作已移除
  // 批量处理已移除
  // 清空结果已移除
  // API 处理逻辑已移除

  // 渲染音频播放器
  const renderAudioPlayer = (audioUrl: string) => {
    const getAudioType = (url: string) => {
      const ext = url.split('.').pop()?.toLowerCase()
      switch (ext) {
        case 'wav': return 'audio/wav'
        case 'mp3': return 'audio/mpeg'
        case 'm4a': return 'audio/mp4'
        case 'ogg': return 'audio/ogg'
        case 'flac': return 'audio/flac'
        default: return 'audio/wav'
      }
    }

    if (audioUrl) {
      return (
        <div className="audio-player-container">
          <audio 
            controls 
            className="table-audio-player"
            preload="metadata"
            controlsList="nodownload noplaybackrate noremoteplayback"
          >
            <source src={audioUrl} type={getAudioType(audioUrl)} />
            您的浏览器不支持音频播放
          </audio>
        </div>
      )
    } else {
      return <span className="no-audio-text">暂无音频</span>
    }
  }

  // 状态标签列已移除

  // 表格列定义
  const columns = [
    {
      title: '指令',
      dataIndex: 'instruction',
      key: 'instruction',
      width: 200,
      render: (text: string) => (
        <div className="instruction-cell">
          {text}
        </div>
      )
    },
    {
      title: '用户提问',
      dataIndex: 'inputText',
      key: 'inputText',
      width: 250,
      render: (text: string) => (
        <div className="input-cell">
          <TextArea
            value={text}
            autoSize={{ minRows: 2, maxRows: 4 }}
            readOnly
            className="input-textarea"
          />
        </div>
      )
    },
    {
      title: '回答音频',
      dataIndex: 'outputAudio',
      key: 'outputAudio',
      width: 280,
      render: (audioUrl: string) => renderAudioPlayer(audioUrl)
    }
  ]

  return (
    <div className="module-container">
      <Card className="dialogue-module-card" bordered={true}>
        <div className="module-header">
          <div className="module-icon">
            <MessageOutlined />
          </div>
          <div className="module-title-section">
            <Title level={2} className="module-title">智能对话音频</Title>
            <Paragraph className="module-description">
              输入文本问题，AI生成回答并转换为方言音频
            </Paragraph>
          </div>
        </div>

        {/* 控制面板移除 */}

        {/* 结果表格 */}
        <div className="results-table">
          <Table
            columns={columns}
            dataSource={tableData}
            pagination={false}
            size="middle"
            bordered
            className="dialogue-table"
          />
        </div>
      </Card>
    </div>
  )
}

export default AIDialogueModule

