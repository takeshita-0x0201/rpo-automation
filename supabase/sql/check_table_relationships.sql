-- テーブル間のリレーションシップと実際のデータを確認

-- 1. client_evaluationsテーブルのサンプル
SELECT 
    candidate_id,
    requirement_id,
    client_evaluation,
    synced_to_pinecone
FROM client_evaluations
WHERE synced_to_pinecone = true
LIMIT 3;

-- 2. candidatesテーブルの構造確認
SELECT 
    id,
    candidate_id,
    candidate_company
FROM candidates
WHERE candidate_id IN (
    SELECT DISTINCT candidate_id 
    FROM client_evaluations 
    WHERE synced_to_pinecone = true
)
LIMIT 3;

-- 3. job_requirementsテーブルの構造確認
SELECT 
    id,
    requirement_id,
    title
FROM job_requirements
WHERE requirement_id IN (
    SELECT DISTINCT requirement_id 
    FROM client_evaluations 
    WHERE synced_to_pinecone = true
)
LIMIT 3;

-- 4. ai_evaluationsテーブルの構造とデータ確認
-- まず、どのようなカラムがあるか確認
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'ai_evaluations'
ORDER BY ordinal_position;

-- 5. ai_evaluationsのデータサンプル
SELECT 
    id,
    candidate_id,
    requirement_id,
    ai_score,
    recommendation,
    created_at
FROM ai_evaluations
LIMIT 5;

-- 6. 正しい結合条件を見つける
-- client_evaluationsと他のテーブルの結合テスト
SELECT 
    ce.candidate_id as ce_candidate_id,
    ce.requirement_id as ce_requirement_id,
    c.id as candidate_uuid,
    c.candidate_id as candidate_text_id,
    jr.id as requirement_uuid,
    jr.requirement_id as requirement_text_id,
    ae.id as ai_eval_id,
    ae.candidate_id as ae_candidate_id,
    ae.requirement_id as ae_requirement_id,
    ae.ai_score,
    ae.recommendation
FROM client_evaluations ce
LEFT JOIN candidates c ON c.candidate_id = ce.candidate_id
LEFT JOIN job_requirements jr ON jr.requirement_id = ce.requirement_id
LEFT JOIN ai_evaluations ae ON ae.candidate_id = c.id AND ae.requirement_id = jr.id
WHERE ce.synced_to_pinecone = true
LIMIT 5;