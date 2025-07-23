-- このSQLをSupabaseのSQL Editorで実行してください

-- 1. sync_logs テーブルの作成
CREATE TABLE IF NOT EXISTS public.sync_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  sync_type TEXT NOT NULL,
  trigger_source TEXT NOT NULL,
  started_at TIMESTAMP WITH TIME ZONE NOT NULL,
  completed_at TIMESTAMP WITH TIME ZONE,
  status TEXT NOT NULL,
  details JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- sync_logs用のインデックス
CREATE INDEX IF NOT EXISTS idx_sync_logs_created_at ON public.sync_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON public.sync_logs(status);

-- 権限設定
GRANT SELECT ON public.sync_logs TO authenticated;
GRANT INSERT ON public.sync_logs TO authenticated;

-- 2. client_evaluations テーブルに同期カラムを追加
ALTER TABLE public.client_evaluations 
ADD COLUMN IF NOT EXISTS synced_to_pinecone BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS synced_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS sync_error TEXT,
ADD COLUMN IF NOT EXISTS sync_retry_count INTEGER DEFAULT 0;

-- client_evaluations用のインデックス
CREATE INDEX IF NOT EXISTS idx_client_evaluations_synced_to_pinecone 
ON public.client_evaluations(synced_to_pinecone);

CREATE INDEX IF NOT EXISTS idx_client_evaluations_sync_retry_count 
ON public.client_evaluations(sync_retry_count);

-- 3. sync_status ビューの作成
CREATE OR REPLACE VIEW public.sync_status AS
SELECT
  COUNT(*) FILTER (WHERE synced_to_pinecone = false) AS pending_count,
  COUNT(*) FILTER (WHERE synced_to_pinecone = true) AS synced_count,
  COUNT(*) FILTER (WHERE sync_error IS NOT NULL) AS error_count,
  MAX(synced_at) AS last_sync_at,
  NOW() AS current_time
FROM public.client_evaluations;

-- ビューへの権限設定
GRANT SELECT ON public.sync_status TO authenticated;

-- 確認用: テーブルとビューが正しく作成されたか確認
SELECT 'sync_logs table' as object_type, EXISTS (
  SELECT FROM information_schema.tables 
  WHERE table_schema = 'public' 
  AND table_name = 'sync_logs'
) as exists;

SELECT 'sync columns in client_evaluations' as object_type, EXISTS (
  SELECT FROM information_schema.columns 
  WHERE table_schema = 'public' 
  AND table_name = 'client_evaluations'
  AND column_name = 'synced_to_pinecone'
) as exists;

SELECT 'sync_status view' as object_type, EXISTS (
  SELECT FROM information_schema.views 
  WHERE table_schema = 'public' 
  AND table_name = 'sync_status'
) as exists;