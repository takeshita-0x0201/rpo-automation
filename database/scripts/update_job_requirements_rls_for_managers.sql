-- RLSポリシーを更新してmanagerロールも削除できるようにする

-- 1. 既存の削除ポリシーを削除
DROP POLICY IF EXISTS "Admin can delete job_requirements" ON job_requirements;

-- 2. 新しい削除ポリシーを作成（adminとmanagerが削除可能）
CREATE POLICY "Admin and Manager can delete job_requirements" ON job_requirements
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- 3. 更新ポリシーも同様に更新（既存のポリシーを削除して再作成）
DROP POLICY IF EXISTS "Users can update own job_requirements" ON job_requirements;

CREATE POLICY "Users can update job_requirements" ON job_requirements
    FOR UPDATE USING (
        created_by = auth.uid()
        OR EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- 4. 確認用クエリ
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'job_requirements'
ORDER BY policyname;