import React, { useState, useEffect } from 'react'
import { 
  Typography, 
  Card, 
  Table
} from 'antd'
import { 
  SoundOutlined
} from '@ant-design/icons'
// API 相关操作与批量控制已移除
import { fetchCsv } from '@/utils/csv'

const { Title, Paragraph } = Typography

interface ASRRowData {
  key: string
  instruction: string
  inputAudio: string
  outputText: string
}

const ASRModule: React.FC = () => {
  // 控制面板与批量操作已移除
  const [tableData, setTableData] = useState<ASRRowData[]>([])

  useEffect(() => {
    ;(async () => {
      try {
        const rows = await fetchCsv<{instruction: string; inputAudio: string; outputText?: string}>('/data/asr_data.csv')
        const mapped: ASRRowData[] = rows.map((r, idx) => ({
          key: String(idx + 1),
          instruction: r.instruction,
          inputAudio: r.inputAudio,
          outputText: r.outputText || ''
        }))
        setTableData(mapped)
      } catch (err) {
        console.error('Load ASR CSV failed', err)
      }
    })()
  }, [])

  // 语言选项（控制面板已移除，不再需要）

  // 单行识别操作已移除

  // 批量与清空操作已移除

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
      title: '输入音频',
      dataIndex: 'inputAudio',
      key: 'inputAudio',
      width: 250,
      render: (audioUrl: string) => renderAudioPlayer(audioUrl)
    },
    {
      title: '识别结果',
      dataIndex: 'outputText',
      key: 'outputText',
      render: (text: string) => {
        const normalizedText = (text || '')
          .replace(/\\n/g, '\n')
          .replace(/\/n/g, '\n')
        return (
          <div className="output-cell">
            <div className="result-text" style={{ whiteSpace: 'pre-wrap' }}>{normalizedText}</div>
          </div>
        )
      }
    }
  ]

  return (
    <div className="module-container">
      <Card className="asr-module-card" bordered={true}>
        <div className="module-header">
          <div className="module-icon">
            <SoundOutlined />
          </div>
          <div className="module-title-section">
            <Title level={2} className="module-title">方言语音识别</Title>
            <Paragraph className="module-description">
              高精度的闽台方言语音转文字，支持多种方言
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
            className="asr-table"
          />
        </div>
      </Card>
    </div>
  )
}

export default ASRModule
