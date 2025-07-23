-- BigQueryでスクレイピングされた候補者データを確認

-- 最新の候補者データを10件取得
SELECT 
  id,
  search_id,
  bizreach_id,
  name,
  current_title,
  current_company,
  skills,
  scraped_at,
  JSON_EXTRACT_SCALAR(raw_data, '$.client_id') as client_id,
  JSON_EXTRACT_SCALAR(raw_data, '$.requirement_id') as requirement_id
FROM 
  `rpo-automation.recruitment_data.candidates`
ORDER BY 
  scraped_at DESC
LIMIT 10;

-- セッション（search_id）ごとの候補者数を確認
SELECT 
  search_id,
  COUNT(*) as candidate_count,
  MIN(scraped_at) as first_scraped,
  MAX(scraped_at) as last_scraped
FROM 
  `rpo-automation.recruitment_data.candidates`
GROUP BY 
  search_id
ORDER BY 
  MAX(scraped_at) DESC
LIMIT 10;

-- 今日スクレイピングされた候補者の総数
SELECT 
  COUNT(*) as total_candidates_today
FROM 
  `rpo-automation.recruitment_data.candidates`
WHERE 
  DATE(scraped_at) = CURRENT_DATE();