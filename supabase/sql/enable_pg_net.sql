-- pg_net拡張を有効化してからvector-syncをテスト実行

-- 1. pg_net拡張を有効化
CREATE EXTENSION IF NOT EXISTS pg_net;

-- 2. 拡張が有効になったか確認
SELECT * FROM pg_extension WHERE extname = 'pg_net';

-- 3. 少し待ってから、vector-sync Edge Functionをテスト実行
SELECT
  net.http_post(
    url:='https://agpoeoexuirxzdszdtlu.supabase.co/functions/v1/vector-sync',
    headers:=jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body:='{}'::jsonb
  ) AS request_id;