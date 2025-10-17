import React, { useState, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Table,
  Input
} from 'antd'
import { 
  PlayCircleOutlined
} from '@ant-design/icons'
import { fetchCsv } from '@/utils/csv'

const { Title, Paragraph } = Typography
const { TextArea } = Input

interface TTSRowData {
  key: string
  instruction: string
  inputText: string
  outputAudio: string
}

const TTSModule: React.FC = () => {
  const [tableData, setTableData] = useState<TTSRowData[]>([])

  useEffect(() => {
    ;(async () => {
      try {
        const rows = await fetchCsv<{instruction: string; inputText: string; outputAudio?: string}>('/data/tts_data.csv')
        const mapped: TTSRowData[] = rows.map((r, idx) => ({
          key: String(idx + 1),
          instruction: r.instruction,
          inputText: r.inputText,
          outputAudio: r.outputAudio || ''
        }))
        setTableData(mapped)
      } catch (err) {
        console.error('Load TTS CSV failed', err)
      }
    })()
  }, [])

  // 语言与格式控制面板已移除
  // API 处理逻辑已移除
  // 批量与清空操作已移除

  // 渲染音频播放器
  const renderAudioPlayer = (audioUrl: string) => {
    if (audioUrl) {
      return (
        <div className="audio-player-container">
          <audio 
            controls 
            className="table-audio-player"
            preload="metadata"
            controlsList="nodownload noplaybackrate noremoteplayback"
          >
            <source src={audioUrl} type="audio/wav" />
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
      title: '输入文本',
      dataIndex: 'inputText',
      key: 'inputText',
      width: 300,
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
      title: '合成结果',
      dataIndex: 'outputAudio',
      key: 'outputAudio',
      render: (audioUrl: string) => renderAudioPlayer(audioUrl)
    }
  ]

  return (
    <div className="module-container">
      <Card className="tts-module-card" bordered={true}>
        <div className="module-header">
          <div className="module-icon">
            <PlayCircleOutlined />
          </div>
          <div className="module-title-section">
            <Title level={2} className="module-title">方言语音合成</Title>
            <Paragraph className="module-description">
              将文字转换为自然的方言语音，保持方言特色和语调
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
            className="tts-table"
          />
        </div>
      </Card>
    </div>
  )
}

export default TTSModule
