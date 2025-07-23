import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Initialize Supabase client with service role key for full access
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    )

    // Get request body
    const { batchSize = 50, forceSync = false } = await req.json().catch(() => ({}))

    console.log(`Starting sync process with batchSize: ${batchSize}`)

    // Fetch pending evaluations with all related data
    const { data: pendingEvaluations, error: fetchError } = await supabaseClient
      .from('client_evaluations')
      .select(`
        *,
        candidates!inner(
          id,
          candidate_id,
          candidate_name,
          candidate_company,
          candidate_position,
          years_of_experience,
          candidate_resume
        ),
        requirements:requirement_id!inner(
          id,
          title,
          description,
          department,
          job_type,
          structured_data,
          clients!inner(
            id,
            name,
            industry
          )
        )
      `)
      .eq('synced_to_pinecone', false)
      .lt('sync_retry_count', 3)
      .order('created_at', { ascending: true })
      .limit(batchSize)

    if (fetchError) {
      console.error('Error fetching evaluations:', fetchError)
      throw fetchError
    }

    console.log(`Found ${pendingEvaluations?.length || 0} evaluations to sync`)

    const results = {
      processed: 0,
      successful: 0,
      failed: 0,
      errors: [] as any[]
    }

    // Process each evaluation
    for (const evaluation of pendingEvaluations || []) {
      try {
        // Fetch corresponding AI evaluation
        const { data: aiEvaluation, error: aiError } = await supabaseClient
          .from('ai_evaluations')
          .select('*')
          .eq('candidate_id', evaluation.candidate_id)
          .eq('requirement_id', evaluation.requirement_id)
          .order('created_at', { ascending: false })
          .limit(1)
          .single()

        if (aiError && aiError.code !== 'PGRST116') { // PGRST116 = no rows returned
          console.error(`Error fetching AI evaluation for ${evaluation.id}:`, aiError)
          throw aiError
        }

        // Prepare data for vector generation
        const vectorData = {
          evaluation,
          aiEvaluation,
          candidate: evaluation.candidates,
          requirement: evaluation.requirements,
          client: evaluation.requirements.clients
        }

        // Generate vectors
        const vectors = await generateVectors(vectorData)

        // Upload to Pinecone
        await uploadToPinecone(vectors)

        // Mark as synced
        const { error: updateError } = await supabaseClient
          .from('client_evaluations')
          .update({
            synced_to_pinecone: true,
            synced_at: new Date().toISOString(),
            sync_error: null,
            sync_retry_count: 0
          })
          .eq('id', evaluation.id)

        if (updateError) throw updateError

        results.successful++
        console.log(`Successfully synced evaluation ${evaluation.id}`)

      } catch (error) {
        results.failed++
        const errorMessage = error instanceof Error ? error.message : String(error)
        
        // Update error status
        await supabaseClient
          .from('client_evaluations')
          .update({
            sync_error: errorMessage,
            sync_retry_count: evaluation.sync_retry_count + 1
          })
          .eq('id', evaluation.id)

        results.errors.push({
          evaluationId: evaluation.id,
          error: errorMessage
        })

        console.error(`Failed to sync evaluation ${evaluation.id}:`, errorMessage)
      }

      results.processed++
    }

    return new Response(
      JSON.stringify({
        success: true,
        timestamp: new Date().toISOString(),
        results
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200
      }
    )

  } catch (error) {
    console.error('Edge function error:', error)
    return new Response(
      JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500
      }
    )
  }
})

/**
 * Generate vectors for Pinecone
 */
async function generateVectors(data: any): Promise<any[]> {
  const { evaluation, aiEvaluation, candidate, requirement, client } = data

  // Prepare texts for embedding
  const texts = {
    combined: createCombinedText(data),
    job_side: createJobText(requirement, client),
    candidate: createCandidateText(candidate, evaluation, aiEvaluation)
  }

  // Call Gemini API to generate embeddings
  const geminiApiKey = Deno.env.get('GEMINI_API_KEY')
  if (!geminiApiKey) {
    throw new Error('GEMINI_API_KEY not configured')
  }

  const vectors = []
  const baseId = `webapp_ce_${evaluation.id}` // ce = client_evaluations

  for (const [type, text] of Object.entries(texts)) {
    try {
      const embedding = await callGeminiEmbedding(text, geminiApiKey)
      
      vectors.push({
        id: `${baseId}_${type}`,
        values: embedding,
        metadata: createMetadata(data, type)
      })
    } catch (error) {
      console.error(`Failed to generate ${type} embedding:`, error)
      throw error
    }
  }

  return vectors
}

/**
 * Create combined text for embedding
 */
function createCombinedText(data: any): string {
  const { evaluation, aiEvaluation, candidate, requirement, client } = data

  const sections = []

  // Job information
  sections.push(`【ポジション】${requirement.title}`)
  sections.push(`【企業】${client.name}`)
  sections.push(`【部署】${requirement.department || ''}`)
  
  if (requirement.description) {
    sections.push(`【職務内容】\n${requirement.description}`)
  }

  const structuredData = requirement.structured_data || {}
  if (structuredData.job_memo) {
    sections.push(`【求人メモ】\n${structuredData.job_memo}`)
  }

  // Candidate information
  sections.push(`\n【候補者情報】`)
  sections.push(`ID: ${candidate.candidate_id}`)
  sections.push(`現職: ${candidate.candidate_company} - ${candidate.candidate_position}`)
  sections.push(`経験年数: ${candidate.years_of_experience || '不明'}年`)
  
  if (candidate.candidate_resume) {
    sections.push(`【経歴】\n${candidate.candidate_resume}`)
  }

  // AI evaluation
  if (aiEvaluation) {
    sections.push(`\n【AI評価】`)
    sections.push(`スコア: ${aiEvaluation.score}/100`)
    sections.push(`推奨度: ${aiEvaluation.recommendation}`)
    sections.push(`確信度: ${aiEvaluation.confidence}`)
    
    if (aiEvaluation.strengths?.length) {
      sections.push(`強み: ${aiEvaluation.strengths.join(', ')}`)
    }
    if (aiEvaluation.concerns?.length) {
      sections.push(`懸念: ${aiEvaluation.concerns.join(', ')}`)
    }
  }

  // Client evaluation
  sections.push(`\n【クライアント評価】`)
  sections.push(`評価: ${evaluation.client_evaluation}`)
  if (evaluation.client_feedback) {
    sections.push(`フィードバック: ${evaluation.client_feedback}`)
  }

  return sections.join('\n')
}

/**
 * Create job-side text for embedding
 */
function createJobText(requirement: any, client: any): string {
  const sections = []

  sections.push(`【ポジション】${requirement.title}`)
  sections.push(`【企業】${client.name}`)
  sections.push(`【業界】${client.industry || ''}`)
  sections.push(`【部署】${requirement.department || ''}`)
  sections.push(`【雇用形態】${requirement.job_type || ''}`)

  if (requirement.description) {
    sections.push(`【職務内容】\n${requirement.description}`)
  }

  const structuredData = requirement.structured_data || {}
  
  if (structuredData.required_skills?.length) {
    sections.push(`【必須スキル】${structuredData.required_skills.join(', ')}`)
  }
  
  if (structuredData.preferred_skills?.length) {
    sections.push(`【歓迎スキル】${structuredData.preferred_skills.join(', ')}`)
  }
  
  if (structuredData.job_memo) {
    sections.push(`【求人メモ】\n${structuredData.job_memo}`)
  }

  return sections.join('\n')
}

/**
 * Create candidate-side text for embedding
 */
function createCandidateText(candidate: any, evaluation: any, aiEvaluation: any): string {
  const sections = []

  sections.push(`【候補者情報】`)
  sections.push(`ID: ${candidate.candidate_id}`)
  sections.push(`氏名: ${candidate.candidate_name}`)
  sections.push(`現職: ${candidate.candidate_company} - ${candidate.candidate_position}`)
  sections.push(`経験年数: ${candidate.years_of_experience || '不明'}年`)

  if (candidate.candidate_resume) {
    sections.push(`【経歴・スキル】\n${candidate.candidate_resume}`)
  }

  // Evaluations
  sections.push(`\n【評価結果】`)
  
  if (aiEvaluation) {
    sections.push(`AIスコア: ${aiEvaluation.score}/100 (${aiEvaluation.recommendation})`)
  }
  
  sections.push(`クライアント評価: ${evaluation.client_evaluation}`)
  
  if (evaluation.client_feedback) {
    sections.push(`クライアントフィードバック: ${evaluation.client_feedback}`)
  }

  return sections.join('\n')
}

/**
 * Create metadata for Pinecone
 */
function createMetadata(data: any, vectorType: string): any {
  const { evaluation, aiEvaluation, candidate, requirement, client } = data

  const metadata = {
    // IDs
    case_id: `webapp_ce_${evaluation.id}`,
    evaluation_id: evaluation.id,
    candidate_id: evaluation.candidate_id,
    requirement_id: evaluation.requirement_id,
    
    // Vector type
    vector_type: vectorType,
    
    // Position/Company info
    position: requirement.title,
    company: client.name,
    department: requirement.department || '',
    industry: client.industry || '',
    
    // Candidate info
    candidate_name: candidate.candidate_name,
    candidate_company: candidate.candidate_company,
    years_of_experience: candidate.years_of_experience || 0,
    
    // Evaluations
    client_evaluation: evaluation.client_evaluation,
    client_feedback: truncateText(evaluation.client_feedback || '', 500),
    evaluation_date: evaluation.evaluation_date || evaluation.created_at,
    
    // Timestamps
    created_at: evaluation.created_at,
    synced_at: new Date().toISOString(),
    
    // Quality indicators
    has_client_feedback: !!evaluation.client_feedback,
    has_detailed_feedback: (evaluation.client_feedback?.length || 0) > 50,
    is_successful: ['A', 'B'].includes(evaluation.client_evaluation),
    
    // Source
    data_source: 'client_evaluations',
    sync_version: '3.0'
  }

  // Add AI evaluation data if available
  if (aiEvaluation) {
    metadata.ai_score = aiEvaluation.score
    metadata.ai_recommendation = aiEvaluation.recommendation
    metadata.ai_confidence = aiEvaluation.confidence
    metadata.evaluation_match = aiEvaluation.recommendation === evaluation.client_evaluation
    metadata.score_difference = Math.abs(
      scoreToNumeric(aiEvaluation.recommendation) - 
      scoreToNumeric(evaluation.client_evaluation)
    )
  }

  return metadata
}

/**
 * Call Gemini Embedding API
 */
async function callGeminiEmbedding(text: string, apiKey: string): Promise<number[]> {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${apiKey}`

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'models/text-embedding-004',
      content: {
        parts: [{
          text: text
        }]
      },
      taskType: 'RETRIEVAL_DOCUMENT'
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Gemini API error: ${response.status} - ${error}`)
  }

  const result = await response.json()
  return result.embedding.values
}

/**
 * Upload vectors to Pinecone
 */
async function uploadToPinecone(vectors: any[]): Promise<void> {
  const pineconeApiKey = Deno.env.get('PINECONE_API_KEY')
  const pineconeHost = Deno.env.get('PINECONE_HOST')
  
  if (!pineconeApiKey || !pineconeHost) {
    throw new Error('Pinecone configuration missing')
  }

  const url = `https://${pineconeHost}/vectors/upsert`

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Api-Key': pineconeApiKey,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      vectors: vectors,
      namespace: 'historical-cases'
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Pinecone upload failed: ${response.status} - ${error}`)
  }
}

/**
 * Helper functions
 */
function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

function scoreToNumeric(grade: string): number {
  const mapping: { [key: string]: number } = {
    'A': 4,
    'B': 3,
    'C': 2,
    'D': 1
  }
  return mapping[grade] || 0
}