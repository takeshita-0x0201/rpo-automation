import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// 環境変数
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const GEMINI_API_KEY = Deno.env.get('GEMINI_API_KEY')!
const TAVILY_API_KEY = Deno.env.get('TAVILY_API_KEY')

interface MatchingRequest {
  jobId: string
  requirementId: string
  candidateId: string
}

serve(async (req) => {
  try {
    // リクエストの検証
    if (req.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 })
    }

    const { jobId, requirementId, candidateId }: MatchingRequest = await req.json()

    // Supabase クライアント初期化
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    // ジョブステータスを processing に更新
    await updateJobStatus(supabase, jobId, 'processing', 0, 'evaluation')

    try {
      // 1. データ取得
      const { requirement, candidate } = await fetchData(supabase, requirementId, candidateId)
      
      // 2. テキスト形式に変換
      const jobDescription = formatJobDescription(requirement)
      const resume = formatResume(candidate)
      
      // 3. AI マッチング実行（簡易版）
      const result = await runSimpleMatching({
        jobDescription,
        resume,
        jobMemo: requirement.job_memo || requirement.structured_data?.job_memo || '',
        candidate,  // 候補者情報全体を渡す
        onProgress: async (progress: number, stage: string) => {
          await updateJobStatus(supabase, jobId, 'processing', progress, stage)
        }
      })

      // 4. 結果を保存
      await saveMatchingResult(supabase, jobId, result)
      
      // 5. ジョブを完了に更新
      await updateJobStatus(supabase, jobId, 'completed', 100, 'completed')

      return new Response(JSON.stringify({ success: true, jobId }), {
        headers: { 'Content-Type': 'application/json' },
      })

    } catch (error) {
      // エラー時の処理
      await updateJobStatus(supabase, jobId, 'failed', 0, null, error.message)
      throw error
    }

  } catch (error) {
    console.error('Error processing matching:', error)
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
})

// ジョブステータス更新
async function updateJobStatus(
  supabase: any,
  jobId: string,
  status: string,
  progress: number,
  stage: string | null,
  error?: string
) {
  const updates: any = {
    status,
    progress,
    current_stage: stage,
  }

  if (status === 'processing' && !updates.started_at) {
    updates.started_at = new Date().toISOString()
  }

  if (status === 'completed' || status === 'failed') {
    updates.completed_at = new Date().toISOString()
  }

  if (error) {
    updates.error_message = error
  }

  const { error: updateError } = await supabase
    .from('matching_jobs')
    .update(updates)
    .eq('id', jobId)

  if (updateError) {
    console.error('Failed to update job status:', updateError)
  }
}

// データ取得
async function fetchData(supabase: any, requirementId: string, candidateId: string) {
  // 要件情報を取得
  const { data: requirement, error: reqError } = await supabase
    .from('job_requirements')
    .select('*, client:clients(*)')
    .eq('id', requirementId)
    .single()

  if (reqError) throw new Error(`Failed to fetch requirement: ${reqError.message}`)

  // 候補者情報を取得
  const { data: candidate, error: candError } = await supabase
    .from('candidates')
    .select('*')
    .eq('id', candidateId)
    .single()

  if (candError) throw new Error(`Failed to fetch candidate: ${candError.message}`)

  return { requirement, candidate }
}

// ジョブ記述文のフォーマット
function formatJobDescription(requirement: any): string {
  // structured_dataに完全なjob_descriptionがある場合はそれを使用
  // なければ、個別フィールドから構築
  if (requirement.structured_data?.job_description_full) {
    return requirement.structured_data.job_description_full
  }
  
  // job_descriptionフィールドがある場合（完全なテキスト）
  if (requirement.job_description) {
    return requirement.job_description
  }
  
  // 個別フィールドから構築（フォールバック）
  const sections = []
  
  // 基本情報
  sections.push(`【ポジション】${requirement.title}`)
  
  if (requirement.client?.name) {
    sections.push(`【企業名】${requirement.client.name}`)
  }
  
  // 構造化データから情報を抽出
  const structured = requirement.structured_data || {}
  
  if (structured.position_details) {
    sections.push(`【ポジション詳細】\n${structured.position_details}`)
  }
  
  if (structured.required_experience) {
    sections.push(`【必須経験】\n${structured.required_experience}`)
  }
  
  if (structured.preferred_experience) {
    sections.push(`【歓迎経験】\n${structured.preferred_experience}`)
  }
  
  if (structured.job_description) {
    sections.push(`【職務内容】\n${structured.job_description}`)
  }
  
  return sections.join('\n\n')
}

// 履歴書のフォーマット
function formatResume(candidate: any): string {
  const sections = []
  
  // 候補者IDを先頭に追加（AI側で必要な場合）
  if (candidate.candidate_id) {
    sections.push(`ID: ${candidate.candidate_id}`)
  }
  
  // 基本情報
  const basicInfo = []
  if (candidate.age) basicInfo.push(`年齢: ${candidate.age}歳`)
  if (candidate.gender) basicInfo.push(`性別: ${candidate.gender}`)
  if (candidate.candidate_company) basicInfo.push(`現在の所属: ${candidate.candidate_company}`)
  if (candidate.enrolled_company_count) basicInfo.push(`在籍企業数: ${candidate.enrolled_company_count}社`)
  
  if (basicInfo.length > 0) {
    sections.push('【基本情報】')
    sections.push(basicInfo.join('\n'))
  }
  
  // レジュメ本文
  if (candidate.candidate_resume) {
    sections.push('【経歴・スキル】')
    sections.push(candidate.candidate_resume)
  }
  
  return sections.join('\n\n')
}

// 簡易マッチング実行（Gemini APIを使用）
async function runSimpleMatching(params: {
  jobDescription: string
  resume: string
  jobMemo: string
  candidate?: any  // 候補者情報全体
  onProgress: (progress: number, stage: string) => Promise<void>
}): Promise<any> {
  const { jobDescription, resume, jobMemo, candidate, onProgress } = params
  
  // Gemini API を使用した評価（簡易版）
  const prompt = `
以下の候補者と求人のマッチング度を評価してください。

【求人情報】
${jobDescription}

【追加メモ】
${jobMemo}

【候補者情報】
${resume}

以下の形式で回答してください：
1. マッチング度スコア（0-100）
2. 推奨度（A/B/C/D）
3. 強み（3つ）
4. 懸念点（2-3つ）
5. 面接で確認すべきポイント（3つ）
`

  await onProgress(30, 'evaluation')
  
  // Gemini API 呼び出し（実装省略）
  const aiResponse = await callGeminiAPI(prompt)
  
  await onProgress(80, 'report_generation')
  
  // 結果をパース（実装省略）
  const result = parseAIResponse(aiResponse)
  
  return {
    final_score: result.score,
    recommendation: result.recommendation,
    confidence: 'Medium',
    strengths: result.strengths,
    concerns: result.concerns,
    interview_points: result.interviewPoints,
    overall_assessment: result.assessment
  }
}

// Gemini API 呼び出し（仮実装）
async function callGeminiAPI(prompt: string): Promise<string> {
  // TODO: 実際のGemini API呼び出しを実装
  return 'AI response placeholder'
}

// AI応答のパース（仮実装）
function parseAIResponse(response: string): any {
  // TODO: 実際のパース処理を実装
  return {
    score: 75,
    recommendation: 'B',
    strengths: ['経験豊富', '技術力高い', 'リーダーシップ'],
    concerns: ['業界経験不足', '転職回数多い'],
    interviewPoints: ['チームマネジメント経験', '技術選定の基準', '長期的なキャリアビジョン'],
    assessment: '総合的に見て良い候補者です。'
  }
}

// マッチング結果を保存
async function saveMatchingResult(supabase: any, jobId: string, result: any) {
  // matching_jobs テーブルに結果を保存
  const { error: jobError } = await supabase
    .from('matching_jobs')
    .update({ result })
    .eq('id', jobId)

  if (jobError) throw new Error(`Failed to update job result: ${jobError.message}`)

  // matching_results テーブルに詳細を保存
  const { error: resultError } = await supabase
    .from('matching_results')
    .insert({
      job_id: jobId,
      final_score: result.final_score,
      recommendation: result.recommendation,
      confidence: result.confidence,
      strengths: result.strengths,
      concerns: result.concerns,
      interview_points: result.interview_points,
    })

  if (resultError) throw new Error(`Failed to save matching result: ${resultError.message}`)
}