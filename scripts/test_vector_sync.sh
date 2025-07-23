#!/bin/bash

# vector-sync Edge Functionをテスト実行するスクリプト

# Supabaseの情報
SUPABASE_URL="https://agpoeoexuirxzdszdtlu.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFncG9lb2V4dWlyeHpkc3pkdGx1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE1OTMzOTEsImV4cCI6MjA2NzE2OTM5MX0.gCx3hYQLcL8wrWk7LBSK3wo-4rPWt7vyDdy-B2loByA"
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInB5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFncG9lb2V4dWlyeHpkc3pkdGx1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTU5MzM5MSwiZXhwIjoyMDY3MTY5MzkxfQ.ro0Leni7Dp9ag7DtWY-Uenrp35Y_Ybtlafb7JkCOL_0"

echo "vector-sync Edge Functionをテスト実行中..."

# Edge Functionを呼び出し
curl -i -X POST \
  "${SUPABASE_URL}/functions/v1/vector-sync" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{}'

echo -e "\n\n実行完了。ログはSupabaseダッシュボードで確認してください："
echo "https://supabase.com/dashboard/project/agpoeoexuirxzdszdtlu/functions/vector-sync/logs"