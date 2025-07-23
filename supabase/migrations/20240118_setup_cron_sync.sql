-- Enable pg_cron extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Grant usage on cron schema to postgres user
GRANT USAGE ON SCHEMA cron TO postgres;

-- Create a function to call the Edge Function
CREATE OR REPLACE FUNCTION public.trigger_evaluation_sync()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  service_role_key text;
  project_url text;
  response jsonb;
BEGIN
  -- Get the service role key and project URL from configuration
  -- Note: You'll need to set these as database configurations
  service_role_key := current_setting('app.settings.service_role_key', true);
  project_url := current_setting('app.settings.supabase_url', true);
  
  -- Call the Edge Function
  SELECT
    net.http_post(
      url := project_url || '/functions/v1/sync-evaluations',
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || service_role_key,
        'Content-Type', 'application/json'
      ),
      body := jsonb_build_object(
        'batchSize', 50,
        'trigger', 'cron'
      )
    ) INTO response;
    
  -- Log the result
  INSERT INTO public.sync_logs (
    sync_type,
    trigger_source,
    started_at,
    completed_at,
    status,
    details
  ) VALUES (
    'client_evaluations_to_pinecone',
    'pg_cron',
    NOW() - INTERVAL '1 minute',
    NOW(),
    CASE 
      WHEN response->>'status_code' = '200' THEN 'success'
      ELSE 'failed'
    END,
    response
  );
END;
$$;

-- Create sync logs table for monitoring
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

-- Add index for efficient querying
CREATE INDEX IF NOT EXISTS idx_sync_logs_created_at ON public.sync_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON public.sync_logs(status);

-- Schedule the cron job to run every 10 minutes
SELECT cron.schedule(
  'sync-client-evaluations-to-pinecone',  -- Job name
  '*/10 * * * *',                          -- Every 10 minutes
  $$SELECT public.trigger_evaluation_sync();$$
);

-- Alternative: Direct HTTP call without wrapper function (simpler but less logging)
-- SELECT cron.schedule(
--   'sync-client-evaluations-direct',
--   '*/10 * * * *',
--   $$
--   SELECT net.http_post(
--     url := current_setting('app.settings.supabase_url') || '/functions/v1/sync-evaluations',
--     headers := jsonb_build_object(
--       'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'),
--       'Content-Type', 'application/json'
--     ),
--     body := jsonb_build_object('batchSize', 50, 'trigger', 'cron')
--   );
--   $$
-- );

-- Function to manually trigger sync (useful for testing and manual sync)
CREATE OR REPLACE FUNCTION public.manual_sync_evaluations(batch_size int DEFAULT 50)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  service_role_key text;
  project_url text;
  response jsonb;
BEGIN
  service_role_key := current_setting('app.settings.service_role_key', true);
  project_url := current_setting('app.settings.supabase_url', true);
  
  SELECT
    net.http_post(
      url := project_url || '/functions/v1/sync-evaluations',
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || service_role_key,
        'Content-Type', 'application/json'
      ),
      body := jsonb_build_object(
        'batchSize', batch_size,
        'trigger', 'manual',
        'forceSync', true
      )
    ) INTO response;
    
  RETURN response;
END;
$$;

-- Grant execute permission to authenticated users for manual sync
GRANT EXECUTE ON FUNCTION public.manual_sync_evaluations TO authenticated;

-- View to check sync status
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

-- Comment for documentation
COMMENT ON FUNCTION public.trigger_evaluation_sync() IS 'Triggers the Edge Function to sync client evaluations to Pinecone';
COMMENT ON FUNCTION public.manual_sync_evaluations(int) IS 'Manually triggers sync of client evaluations to Pinecone with specified batch size';
COMMENT ON VIEW public.sync_status IS 'Shows current synchronization status of client evaluations';