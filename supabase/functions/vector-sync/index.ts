import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.4'
import { GoogleGenerativeAI } from "https://esm.sh/@google/generative-ai@0.1.3"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// 環境変数
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const GEMINI_API_KEY = Deno.env.get('GEMINI_API_KEY')!
const PINECONE_API_KEY = Deno.env.get('PINECONE_API_KEY')!
const PINECONE_INDEX_HOST = Deno.env.get('PINECONE_INDEX_HOST')!

// 設定
const BATCH_SIZE = 5 // Gemini無料枠に合わせて
const EMBEDDING_MODEL = "embedding-001"
const DIMENSION = 768

interface ClientEvaluation {
  candidate_id: string
  requirement_id: string
  client_evaluation: string
  client_feedback: string
  evaluation_date: string
  created_by: string
  sync_retry_count?: number
}

serve(async (req) => {
  // CORS対応
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Supabaseクライアントを初期化
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    // Gemini APIを初期化
    const genAI = new GoogleGenerativeAI(GEMINI_API_KEY)
    
    console.log('Vector sync started')
    
    // 1. 未同期の評価を取得
    const { data: evaluations, error: fetchError } = await supabase
      .from('client_evaluations')
      .select('*')
      .eq('synced_to_pinecone', false)
      .limit(BATCH_SIZE)
    
    if (fetchError) throw fetchError
    
    if (!evaluations || evaluations.length === 0) {
      return new Response(JSON.stringify({ 
        message: 'No evaluations to sync',
        processed: 0 
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200
      })
    }
    
    console.log(`Found ${evaluations.length} evaluations to sync`)
    
    const results = {
      processed: 0,
      success: 0,
      failed: 0,
      errors: [] as any[]
    }
    
    // 2. 各評価を処理
    for (const evaluation of evaluations) {
      try {
        // 関連データを収集
        const relatedData = await collectRelatedData(supabase, evaluation)
        if (!relatedData) {
          throw new Error('Failed to collect related data')
        }
        
        // ベクトルテキストを準備
        const vectorTexts = prepareVectorTexts(relatedData)
        
        // エンベディングを生成
        const embeddings = await generateEmbeddings(genAI, vectorTexts)
        
        // Pineconeに保存
        const vectors = prepareVectorsForPinecone(relatedData, embeddings)
        await upsertToPinecone(vectors)
        
        // 同期完了をマーク
        await markAsSynced(supabase, evaluation)
        
        results.success++
      } catch (error) {
        console.error(`Error processing evaluation: ${error}`)
        results.failed++
        results.errors.push({
          candidate_id: evaluation.candidate_id,
          error: error.message
        })
        
        // エラーを記録
        await recordSyncError(supabase, evaluation, error.message)
      }
      
      results.processed++
    }
    
    console.log(`Sync completed: ${results.success} success, ${results.failed} failed`)
    
    return new Response(JSON.stringify(results), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200
    })
    
  } catch (error) {
    console.error('Fatal error:', error)
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500
    })
  }
})

// 関連データを収集
async function collectRelatedData(supabase: any, evaluation: ClientEvaluation) {
  try {
    // 候補者データを取得
    const { data: candidates } = await supabase
      .from('candidates')
      .select('*')
      .eq('candidate_id', evaluation.candidate_id)
      .single()
    
    if (!candidates) return null
    
    // 求人要件データを取得
    const { data: requirement } = await supabase
      .from('job_requirements')
      .select('*, clients(*)')
      .eq('requirement_id', evaluation.requirement_id)
      .single()
    
    if (!requirement) return null
    
    // AI評価データを取得
    // ai_evaluationsテーブルはcandidate_idとrequirement_idを外部キーとして持つ
    console.log(`Searching AI evaluation for candidate: ${candidates.id}, requirement: ${requirement.id}`)
    const { data: aiEvaluation } = await supabase
      .from('ai_evaluations')
      .select('*')
      .eq('candidate_id', candidates.id)
      .eq('requirement_id', requirement.id)
      .single()
    
    if (aiEvaluation) {
      console.log(`Found AI evaluation with score: ${aiEvaluation.score}, recommendation: ${aiEvaluation.recommendation}`)
    } else {
      console.log('No AI evaluation found')
    }
    
    return {
      evaluation,
      candidate: candidates,
      requirement,
      aiEvaluation,
      client: requirement.clients
    }
  } catch (error) {
    console.error('Error collecting data:', error)
    return null
  }
}

// ベクトルテキストを準備
function prepareVectorTexts(data: any) {
  const { evaluation, candidate, requirement, aiEvaluation, client } = data
  
  // 1. 求人側ベクトル
  const jobSideText = `
ポジション: ${requirement.title || ''}
クライアント: ${client?.name || ''}

求人詳細:
${requirement.job_description || ''}

求人メモ:
${requirement.memo || ''}
`
  
  // 2. 候補者ベクトル
  const candidateText = `
候補者: ${candidate.candidate_id || ''}
所属企業: ${candidate.candidate_company || ''}

レジュメ:
${candidate.candidate_resume || ''}

AI評価スコア: ${aiEvaluation?.score || 'N/A'}
推奨度: ${aiEvaluation?.recommendation || 'N/A'}

強み:
${aiEvaluation?.strengths?.join(', ') || ''}

懸念点:
${aiEvaluation?.concerns?.join(', ') || ''}

クライアント評価: ${evaluation.client_evaluation || ''}
評価者: ${evaluation.created_by || ''}
フィードバック: ${evaluation.client_feedback || ''}
`
  
  // 3. 統合ベクトル
  const combinedText = `${jobSideText}\n\n${candidateText}`
  
  return {
    job_side: jobSideText,
    candidate: candidateText,
    combined: combinedText
  }
}

// エンベディングを生成
async function generateEmbeddings(genAI: any, texts: any) {
  const model = genAI.getGenerativeModel({ model: EMBEDDING_MODEL })
  const embeddings: any = {}
  
  for (const [key, text] of Object.entries(texts)) {
    try {
      const result = await model.embedContent(text as string)
      // embeddingがvaluesプロパティを持つオブジェクトの場合、値の配列を取得
      console.log(`Embedding structure for ${key}:`, typeof result.embedding, Array.isArray(result.embedding))
      embeddings[key] = result.embedding.values || result.embedding
      
      // レート制限対応
      await new Promise(resolve => setTimeout(resolve, 4000)) // 4秒待機
    } catch (error) {
      console.error(`Error generating embedding for ${key}:`, error)
      embeddings[key] = null
    }
  }
  
  return embeddings
}

// Pinecone用のベクトルを準備
function prepareVectorsForPinecone(data: any, embeddings: any) {
  const { evaluation, candidate, requirement, aiEvaluation, client } = data
  const baseId = `${evaluation.candidate_id}_${evaluation.requirement_id}_${evaluation.evaluation_date || new Date().toISOString().split('T')[0]}`
  
  const vectors = []
  
  for (const [type, embedding] of Object.entries(embeddings)) {
    if (!embedding) continue
    
    const metadata = {
      case_id: `${baseId}_${type}`,
      vector_type: type,
      created_at: new Date().toISOString(),
      position: requirement.title || '',
      client_id: client?.id || '',
      client_name: client?.name || '',
      ai_recommendation: aiEvaluation?.recommendation || '',
      client_evaluation: evaluation.client_evaluation || '',
      score: aiEvaluation?.score || 0,
      evaluation_match: aiEvaluation?.recommendation === evaluation.client_evaluation,
      is_high_quality: (aiEvaluation?.score || 0) >= 80,
      has_client_feedback: !!evaluation.client_feedback,
      is_sharable: true
    }
    
    vectors.push({
      id: metadata.case_id,
      values: embedding,
      metadata
    })
  }
  
  return vectors
}

// Pineconeにアップサート
async function upsertToPinecone(vectors: any[]) {
  // PINECONE_INDEX_HOSTがhttps://を含む場合はそのまま使用
  const url = PINECONE_INDEX_HOST.startsWith('https://') 
    ? `${PINECONE_INDEX_HOST}/vectors/upsert`
    : `https://${PINECONE_INDEX_HOST}/vectors/upsert`
  
  const requestBody = {
    vectors,
    namespace: 'historical-cases'
  }
  
  console.log(`Sending to Pinecone: ${url}`)
  console.log(`Vector count: ${vectors.length}`)
  console.log(`First vector: ${JSON.stringify(vectors[0], null, 2)}`)
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Api-Key': PINECONE_API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestBody)
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    console.error(`Pinecone error: ${response.status} ${response.statusText}`)
    console.error(`Error details: ${errorText}`)
    throw new Error(`Pinecone error: ${response.statusText}`)
  }
}

// 同期完了をマーク
async function markAsSynced(supabase: any, evaluation: ClientEvaluation) {
  const { error } = await supabase
    .from('client_evaluations')
    .update({
      synced_to_pinecone: true,
      synced_at: new Date().toISOString(),
      sync_error: null
    })
    .eq('candidate_id', evaluation.candidate_id)
    .eq('requirement_id', evaluation.requirement_id)
  
  if (error) throw error
}

// エラーを記録
async function recordSyncError(supabase: any, evaluation: ClientEvaluation, errorMessage: string) {
  await supabase
    .from('client_evaluations')
    .update({
      sync_error: errorMessage,
      sync_retry_count: (evaluation.sync_retry_count || 0) + 1
    })
    .eq('candidate_id', evaluation.candidate_id)
    .eq('requirement_id', evaluation.requirement_id)
}