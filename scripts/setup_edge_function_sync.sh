#!/bin/bash

# Setup script for Supabase Edge Function sync

echo "Setting up Supabase Edge Function for client evaluations sync..."

# Check if supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "Error: Supabase CLI is not installed."
    echo "Please install it from: https://supabase.com/docs/guides/cli"
    exit 1
fi

# Deploy the Edge Function
echo "Deploying Edge Function..."
supabase functions deploy sync-evaluations

# Set secrets (you'll need to replace these with actual values)
echo "Setting up environment variables..."
echo "Please enter your API keys:"

read -p "Enter GEMINI_API_KEY: " GEMINI_API_KEY
read -p "Enter PINECONE_API_KEY: " PINECONE_API_KEY
read -p "Enter PINECONE_HOST (e.g., recruitment-matching-xxxxx.svc.us-east-1.pinecone.io): " PINECONE_HOST

# Set the secrets
supabase secrets set GEMINI_API_KEY=$GEMINI_API_KEY
supabase secrets set PINECONE_API_KEY=$PINECONE_API_KEY
supabase secrets set PINECONE_HOST=$PINECONE_HOST

echo "Edge Function deployment complete!"

# Instructions for database configuration
echo ""
echo "Next steps:"
echo "1. Go to your Supabase dashboard"
echo "2. Navigate to Database > Extensions"
echo "3. Enable 'pg_cron' and 'pg_net' extensions if not already enabled"
echo "4. Run the migration script to set up cron jobs:"
echo "   supabase db push"
echo ""
echo "5. Set database configurations in SQL Editor:"
echo "   ALTER DATABASE postgres SET app.settings.service_role_key = 'your-service-role-key';"
echo "   ALTER DATABASE postgres SET app.settings.supabase_url = 'https://your-project.supabase.co';"
echo ""
echo "6. Test the sync manually:"
echo "   SELECT public.manual_sync_evaluations(10);"