-- 同期されていないclient_evaluationsを確認

-- 未同期のレコード数を確認
SELECT COUNT(*) as unsynced_count
FROM client_evaluations
WHERE synced_to_pinecone = false;

-- 未同期のレコードの詳細を表示（最初の5件）
SELECT 
  candidate_id,
  requirement_id,
  client_evaluation,
  client_feedback,
  evaluation_date,
  created_by,
  created_at,
  synced_to_pinecone,
  sync_error
FROM client_evaluations
WHERE synced_to_pinecone = false
ORDER BY created_at DESC
LIMIT 5;