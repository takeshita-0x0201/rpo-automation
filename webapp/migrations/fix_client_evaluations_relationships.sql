-- このSQLをSupabaseのSQL Editorで実行してください

-- 1. まず、client_evaluationsテーブルの構造を確認
-- もしテーブルが存在しない場合は作成
CREATE TABLE IF NOT EXISTS public.client_evaluations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    candidate_id UUID NOT NULL,
    requirement_id UUID NOT NULL,
    client_evaluation VARCHAR(1) CHECK (client_evaluation IN ('A', 'B', 'C', 'D')),
    client_feedback TEXT,
    evaluation_date DATE,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 外部キー制約を追加（まだ存在しない場合）
DO $$ 
BEGIN
    -- candidates テーブルへの外部キー
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'client_evaluations_candidate_id_fkey'
        AND table_name = 'client_evaluations'
    ) THEN
        ALTER TABLE public.client_evaluations
        ADD CONSTRAINT client_evaluations_candidate_id_fkey 
        FOREIGN KEY (candidate_id) REFERENCES public.candidates(id);
    END IF;

    -- job_requirements テーブルへの外部キー
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'client_evaluations_requirement_id_fkey'
        AND table_name = 'client_evaluations'
    ) THEN
        ALTER TABLE public.client_evaluations
        ADD CONSTRAINT client_evaluations_requirement_id_fkey 
        FOREIGN KEY (requirement_id) REFERENCES public.job_requirements(id);
    END IF;

    -- profiles テーブルへの外部キー（created_by用）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'client_evaluations_created_by_fkey'
        AND table_name = 'client_evaluations'
    ) THEN
        ALTER TABLE public.client_evaluations
        ADD CONSTRAINT client_evaluations_created_by_fkey 
        FOREIGN KEY (created_by) REFERENCES public.profiles(id);
    END IF;
END $$;

-- 3. インデックスを作成（パフォーマンス向上のため）
CREATE INDEX IF NOT EXISTS idx_client_evaluations_candidate_id ON public.client_evaluations(candidate_id);
CREATE INDEX IF NOT EXISTS idx_client_evaluations_requirement_id ON public.client_evaluations(requirement_id);
CREATE INDEX IF NOT EXISTS idx_client_evaluations_created_by ON public.client_evaluations(created_by);
CREATE INDEX IF NOT EXISTS idx_client_evaluations_evaluation_date ON public.client_evaluations(evaluation_date);

-- 4. RLSポリシーの設定
ALTER TABLE public.client_evaluations ENABLE ROW LEVEL SECURITY;

-- 認証されたユーザーは読み取り可能
CREATE POLICY IF NOT EXISTS "client_evaluations_select_policy" ON public.client_evaluations
    FOR SELECT TO authenticated USING (true);

-- admin と manager は挿入・更新・削除可能
CREATE POLICY IF NOT EXISTS "client_evaluations_admin_policy" ON public.client_evaluations
    FOR ALL TO authenticated 
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- 5. 権限の付与
GRANT SELECT ON public.client_evaluations TO authenticated;
GRANT INSERT, UPDATE, DELETE ON public.client_evaluations TO authenticated;

-- 6. 同期関連のカラムを追加（まだ存在しない場合）
ALTER TABLE public.client_evaluations 
ADD COLUMN IF NOT EXISTS synced_to_pinecone BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS synced_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS sync_error TEXT,
ADD COLUMN IF NOT EXISTS sync_retry_count INTEGER DEFAULT 0;

-- 7. 確認用クエリ
SELECT 
    tc.constraint_name,
    tc.constraint_type,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'client_evaluations' 
    AND tc.constraint_type = 'FOREIGN KEY';