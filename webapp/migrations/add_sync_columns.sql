-- Add sync columns to client_evaluations table if they don't exist
ALTER TABLE public.client_evaluations 
ADD COLUMN IF NOT EXISTS synced_to_pinecone BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS synced_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS sync_error TEXT,
ADD COLUMN IF NOT EXISTS sync_retry_count INTEGER DEFAULT 0;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_client_evaluations_synced_to_pinecone 
ON public.client_evaluations(synced_to_pinecone);

CREATE INDEX IF NOT EXISTS idx_client_evaluations_sync_retry_count 
ON public.client_evaluations(sync_retry_count);

-- Create sync_status view
CREATE OR REPLACE VIEW public.sync_status AS
SELECT
  COUNT(*) FILTER (WHERE synced_to_pinecone = false) AS pending_count,
  COUNT(*) FILTER (WHERE synced_to_pinecone = true) AS synced_count,
  COUNT(*) FILTER (WHERE sync_error IS NOT NULL) AS error_count,
  MAX(synced_at) AS last_sync_at,
  NOW() AS current_time
FROM public.client_evaluations;

-- Grant select on the view
GRANT SELECT ON public.sync_status TO authenticated;

-- Create sync_logs table if it doesn't exist
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

-- Add indexes for sync_logs
CREATE INDEX IF NOT EXISTS idx_sync_logs_created_at ON public.sync_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON public.sync_logs(status);

-- Grant permissions on sync_logs
GRANT SELECT ON public.sync_logs TO authenticated;
GRANT INSERT ON public.sync_logs TO authenticated;