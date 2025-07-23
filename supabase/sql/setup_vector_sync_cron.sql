-- vector-sync Edge Functionの定期実行を設定するSQL
-- SupabaseのSQL Editorで実行してください

-- 1. pg_cron拡張を有効化（まだの場合）
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. 既存のジョブを削除（再実行の場合）
SELECT cron.unschedule('vector-sync-hourly');

-- 3. 1時間ごとに実行するcronジョブを作成
SELECT
  cron.schedule(
    'vector-sync-hourly',           -- ジョブ名
    '0 * * * *',                    -- 毎時0分に実行
    $$
    SELECT
      net.http_post(
        url:='https://agpoeoexuirxzdszdtlu.supabase.co/functions/v1/vector-sync',
        headers:=jsonb_build_object(
          'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
          'Content-Type', 'application/json'
        ),
        body:='{}'::jsonb
      ) AS request_id;
    $$
  );

-- 4. 登録されたcronジョブを確認
SELECT 
  jobname,
  schedule,
  active,
  command
FROM cron.job
WHERE jobname = 'vector-sync-hourly';

-- 5. 手動で即座に実行してテストする場合
-- SELECT
--   net.http_post(
--     url:='https://agpoeoexuirxzdszdtlu.supabase.co/functions/v1/vector-sync',
--     headers:=jsonb_build_object(
--       'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
--       'Content-Type', 'application/json'
--     ),
--     body:='{}'::jsonb
--   ) AS request_id;

-- 注意事項：
-- 1. このクエリはSupabaseのSQL Editorで実行してください
-- 2. pg_cron拡張が有効になっている必要があります
-- 3. cronジョブは毎時0分に実行されます（例：1:00, 2:00, 3:00...）
-- 4. 実行頻度を変更したい場合は、cron式を変更してください：
--    - '*/30 * * * *' = 30分ごと
--    - '0 */2 * * *' = 2時間ごと
--    - '0 9 * * *' = 毎日午前9時