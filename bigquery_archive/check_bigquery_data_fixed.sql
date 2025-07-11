-- BigQueryでスクレイピングされた候補者データを確認

-- まず、recruitment_dataデータセットのテーブルを確認
-- BigQuery Consoleで以下を実行:
-- SELECT table_name FROM `rpo-automation.recruitment_data.INFORMATION_SCHEMA.TABLES`;

-- 最新の候補者データを10件取得（テーブル名を確認後、適切に変更してください）
SELECT 
  candidate_id,
  name,
  current_company,
  current_position,
  bizreach_url,
  client_id,
  requirement_id,
  session_id,
  scraped_at,
  created_at
FROM 
  `rpo-automation.recruitment_data.scraped_candidates`
ORDER BY 
  created_at DESC
LIMIT 10;

-- セッションごとの候補者数を確認
SELECT 
  session_id,
  COUNT(*) as candidate_count,
  MIN(created_at) as first_scraped,
  MAX(created_at) as last_scraped
FROM 
  `rpo-automation.recruitment_data.scraped_candidates`
GROUP BY 
  session_id
ORDER BY 
  MAX(created_at) DESC
LIMIT 10;

-- 今日スクレイピングされた候補者の総数
SELECT 
  COUNT(*) as total_candidates_today
FROM 
  `rpo-automation.recruitment_data.scraped_candidates`
WHERE 
  DATE(created_at) = CURRENT_DATE();