-- client_evaluationsとai_evaluationsの関連を確認

-- 1. 同期されたデータの詳細を確認
SELECT 
    ce.candidate_id,
    ce.requirement_id,
    ce.client_evaluation,
    ce.client_feedback,
    ce.created_by,
    ce.synced_to_pinecone,
    -- 候補者情報
    c.candidate_company,
    LENGTH(c.candidate_resume) as resume_length,
    -- 求人情報
    jr.title as job_title,
    LENGTH(jr.job_description) as job_desc_length,
    LENGTH(jr.memo) as memo_length,
    -- AI評価情報
    ae.ai_score,
    ae.recommendation,
    ae.strengths,
    ae.concerns
FROM client_evaluations ce
LEFT JOIN candidates c ON c.candidate_id = ce.candidate_id
LEFT JOIN job_requirements jr ON jr.requirement_id = ce.requirement_id
LEFT JOIN ai_evaluations ae ON ae.candidate_id = c.id AND ae.requirement_id = jr.id
WHERE ce.synced_to_pinecone = true
ORDER BY ce.created_at DESC
LIMIT 5;

-- 2. AI評価が存在するか確認
SELECT 
    COUNT(*) as total_synced,
    COUNT(ae.id) as with_ai_evaluation,
    COUNT(ae.ai_score) as with_ai_score
FROM client_evaluations ce
LEFT JOIN candidates c ON c.candidate_id = ce.candidate_id
LEFT JOIN job_requirements jr ON jr.requirement_id = ce.requirement_id
LEFT JOIN ai_evaluations ae ON ae.candidate_id = c.id AND ae.requirement_id = jr.id
WHERE ce.synced_to_pinecone = true;

-- 3. データの完全性を確認
SELECT 
    ce.candidate_id,
    CASE 
        WHEN c.id IS NULL THEN 'candidatesテーブルに存在しない'
        WHEN c.candidate_resume IS NULL OR c.candidate_resume = '' THEN 'レジュメが空'
        ELSE 'OK'
    END as candidate_status,
    CASE
        WHEN jr.id IS NULL THEN 'job_requirementsテーブルに存在しない'
        WHEN jr.job_description IS NULL OR jr.job_description = '' THEN '求人詳細が空'
        ELSE 'OK'
    END as job_status,
    CASE
        WHEN ae.id IS NULL THEN 'ai_evaluationsテーブルに存在しない'
        WHEN ae.ai_score IS NULL THEN 'AIスコアがNULL'
        ELSE 'OK'
    END as ai_evaluation_status
FROM client_evaluations ce
LEFT JOIN candidates c ON c.candidate_id = ce.candidate_id
LEFT JOIN job_requirements jr ON jr.requirement_id = ce.requirement_id
LEFT JOIN ai_evaluations ae ON ae.candidate_id = c.id AND ae.requirement_id = jr.id
WHERE ce.synced_to_pinecone = true;