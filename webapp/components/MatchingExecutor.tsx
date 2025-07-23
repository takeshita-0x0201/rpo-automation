import React, { useState, useEffect } from 'react'
import { Button, Progress, Alert, Badge, Card, Space, message } from 'antd'
import { PlayCircleOutlined, LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { api } from '../services/api'

interface MatchingExecutorProps {
  requirementId: string
  candidateIds: string[]
  onComplete?: () => void
}

interface JobStatus {
  id: string
  candidateId: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  progress: number
  currentStage?: string
  result?: {
    finalScore: number
    recommendation: string
    confidence: string
  }
  errorMessage?: string
}

export const MatchingExecutor: React.FC<MatchingExecutorProps> = ({
  requirementId,
  candidateIds,
  onComplete
}) => {
  const [jobs, setJobs] = useState<JobStatus[]>([])
  const [isExecuting, setIsExecuting] = useState(false)
  const [polling, setPolling] = useState(false)

  // マッチング実行
  const executeMatching = async () => {
    try {
      setIsExecuting(true)
      
      // APIを呼び出してジョブを開始
      const response = await api.post('/api/matching/start', {
        requirement_id: requirementId,
        candidate_ids: candidateIds
      })

      const { job_ids } = response.data
      
      // 初期ジョブステータスを設定
      const initialJobs = job_ids.map((id: string, index: number) => ({
        id,
        candidateId: candidateIds[index],
        status: 'pending' as const,
        progress: 0
      }))
      
      setJobs(initialJobs)
      setPolling(true)
      message.success(`${job_ids.length}件のマッチング処理を開始しました`)
      
    } catch (error) {
      message.error('マッチングの開始に失敗しました')
      setIsExecuting(false)
    }
  }

  // ジョブステータスの定期確認
  useEffect(() => {
    if (!polling || jobs.length === 0) return

    const interval = setInterval(async () => {
      try {
        // 各ジョブのステータスを確認
        const updatedJobs = await Promise.all(
          jobs.map(async (job) => {
            const response = await api.get(`/api/matching/jobs/${job.id}`)
            return {
              ...job,
              ...response.data
            }
          })
        )

        setJobs(updatedJobs)

        // 全てのジョブが完了したかチェック
        const allCompleted = updatedJobs.every(
          job => ['completed', 'failed', 'cancelled'].includes(job.status)
        )

        if (allCompleted) {
          setPolling(false)
          setIsExecuting(false)
          onComplete?.()
          
          const successCount = updatedJobs.filter(j => j.status === 'completed').length
          message.success(`マッチング完了: ${successCount}/${updatedJobs.length}件成功`)
        }
      } catch (error) {
        console.error('Status polling error:', error)
      }
    }, 3000) // 3秒ごとに確認

    return () => clearInterval(interval)
  }, [polling, jobs])

  // ステータスに応じたアイコン表示
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge status="default" text="待機中" />
      case 'processing':
        return <Badge status="processing" text="処理中" />
      case 'completed':
        return <Badge status="success" text="完了" />
      case 'failed':
        return <Badge status="error" text="失敗" />
      default:
        return <Badge status="default" text={status} />
    }
  }

  // 進捗状況の説明文
  const getStageText = (stage?: string) => {
    switch (stage) {
      case 'evaluation':
        return '基本評価を実行中...'
      case 'gap_analysis':
        return '情報ギャップを分析中...'
      case 'research':
        return '追加情報を調査中...'
      case 'report_generation':
        return 'レポートを生成中...'
      default:
        return '処理中...'
    }
  }

  return (
    <div className="matching-executor">
      {!isExecuting && jobs.length === 0 && (
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={executeMatching}
          disabled={candidateIds.length === 0}
        >
          AIマッチングを実行 ({candidateIds.length}名)
        </Button>
      )}

      {jobs.length > 0 && (
        <Space direction="vertical" style={{ width: '100%' }}>
          {jobs.map((job) => (
            <Card key={job.id} size="small">
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ marginBottom: 8 }}>
                    {getStatusIcon(job.status)}
                    <span style={{ marginLeft: 8 }}>
                      候補者ID: {job.candidateId}
                    </span>
                  </div>
                  
                  {job.status === 'processing' && (
                    <>
                      <Progress 
                        percent={job.progress} 
                        size="small"
                        status="active"
                      />
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {getStageText(job.currentStage)}
                      </div>
                    </>
                  )}
                  
                  {job.status === 'completed' && job.result && (
                    <div style={{ fontSize: 14 }}>
                      スコア: <strong>{job.result.finalScore}</strong> / 
                      推奨度: <strong>{job.result.recommendation}</strong> / 
                      確信度: <strong>{job.result.confidence}</strong>
                    </div>
                  )}
                  
                  {job.status === 'failed' && (
                    <Alert
                      type="error"
                      message={job.errorMessage || 'マッチング処理に失敗しました'}
                      showIcon
                    />
                  )}
                </div>
                
                {job.status === 'completed' && (
                  <Button
                    type="link"
                    onClick={() => window.open(`/matching/result/${job.id}`, '_blank')}
                  >
                    詳細を見る
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </Space>
      )}
    </div>
  )
}