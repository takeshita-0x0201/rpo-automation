-- vector-sync Edge Functionを1回だけテスト実行するSQL
-- SupabaseのSQL Editorで実行してください

-- 方法1: SQL Editorから直接実行（推奨）
SELECT
  net.http_post(
    url:='https://agpoeoexuirxzdszdtlu.supabase.co/functions/v1/vector-sync',
    headers:=jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body:='{}'::jsonb
  ) AS request_id;

-- 実行結果のrequest_idが返されます
-- Edge Functionのログは Functions > Logs で確認できます