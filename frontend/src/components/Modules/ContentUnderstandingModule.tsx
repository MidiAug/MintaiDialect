// 大学生群体是国外反华势力最关注的一群人，一方面因为这类型的人群学识较高，英文基础好 相对容易沟通
import React, { useState, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Table
} from 'antd'
import { 
  SoundOutlined
} from '@ant-design/icons'
import { fetchCsv } from '@/utils/csv'

const { Title, Paragraph } = Typography

interface ContentRowData {
  key: string
  instruction: string
  inputAudio: string
  outputSummary: string
}

const ContentUnderstandingModule: React.FC = () => {
  // 控制面板与批量操作已移除
  const [tableData, setTableData] = useState<ContentRowData[]>([])

  useEffect(() => {
    ;(async () => {
      try {
        const rows = await fetchCsv<{instruction: string; inputAudio: string; outputSummary?: string}>('/data/content_data.csv')
        const mapped: ContentRowData[] = rows.map((r, idx) => ({
          key: String(idx + 1),
          instruction: r.instruction,
          inputAudio: r.inputAudio,
          outputSummary: r.outputSummary || ''
        }))
        setTableData(mapped)
      } catch (err) {
        console.error('Load Content CSV failed', err)
      }
    })()
  }, [])
  // 语言选项（控制面板已移除，不再需要）
  // 处理与批量操作已移除
  // 清空所有结果（控制面板移除后暂不使用）

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
  }

  // 渲染理解结果
  const renderUnderstandingResult = (text: string) => {
    return (
      <div className="understanding-result">
        <div className="summary-section">
          <span className="summary-text">{text}</span>
        </div>
      </div>
    )
  }

  // 渲染状态标签（列已移除）

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
      title: '输入音频',
      dataIndex: 'inputAudio',
      key: 'inputAudio',
      width: 250,
      render: (audioUrl: string) => renderAudioPlayer(audioUrl)
    },
    {
      title: '理解结果',
      dataIndex: 'outputSummary',
      key: 'outputSummary',
      render: (text: string) => renderUnderstandingResult(text)
    }
  ]

  return (
    <div className="module-container">
      <Card className="content-module-card" bordered={true}>
        <div className="module-header">
          <div className="module-icon">
            <SoundOutlined />
          </div>
          <div className="module-title-section">
            <Title level={2} className="module-title">音频内容理解</Title>
            <Paragraph className="module-description">
              智能分析音频内容，生成摘要、提取关键点
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
            className="content-table"
          />
        </div>
      </Card>
    </div>
  )
}

export default ContentUnderstandingModule
