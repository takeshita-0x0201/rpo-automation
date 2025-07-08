-- ============================================
-- updated_at自動更新用トリガーの作成
-- ============================================

-- 1. トリガー関数の作成（または更新）
-- この関数は全てのテーブルで共通で使用されます
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- NEWは更新後のレコード
    -- updated_atカラムを現在時刻に設定
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 関数にコメントを追加
COMMENT ON FUNCTION update_updated_at_column() IS 
'各テーブルのupdated_atカラムを自動的に現在時刻に更新するトリガー関数';

-- ============================================
-- 2. 各テーブルにトリガーを設定
-- ============================================

-- requirements テーブル用トリガー
DROP TRIGGER IF EXISTS update_requirements_updated_at ON requirements;
CREATE TRIGGER update_requirements_updated_at
    BEFORE UPDATE ON requirements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- candidates テーブル用トリガー
DROP TRIGGER IF EXISTS update_candidates_updated_at ON candidates;
CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- clients テーブル用トリガー（既存テーブルにも追加）
DROP TRIGGER IF EXISTS update_clients_updated_at ON clients;
CREATE TRIGGER update_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- profiles テーブル用トリガー（既存テーブルにも追加）
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- search_jobs テーブル用トリガー（既存テーブルにも追加）
DROP TRIGGER IF EXISTS update_search_jobs_updated_at ON search_jobs;
CREATE TRIGGER update_search_jobs_updated_at
    BEFORE UPDATE ON search_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. トリガーの動作確認用クエリ
-- ============================================

-- トリガーが正しく設定されているか確認
SELECT 
    trigger_name AS "トリガー名",
    event_object_table AS "対象テーブル",
    action_timing AS "実行タイミング",
    event_manipulation AS "イベント",
    action_statement AS "実行される関数"
FROM information_schema.triggers
WHERE trigger_schema = 'public'
AND trigger_name LIKE '%updated_at%'
ORDER BY event_object_table;

-- ============================================
-- 4. 動作テスト用のサンプル
-- ============================================

-- 以下はテスト用（実行は任意）
/*
-- テスト1: requirementsテーブルでの動作確認
-- まず現在のデータを確認
SELECT id, position_name, updated_at FROM requirements LIMIT 1;

-- データを更新（updated_atは指定しない）
UPDATE requirements 
SET position_name = position_name || ' (更新テスト)'
WHERE id = (SELECT id FROM requirements LIMIT 1);

-- updated_atが自動更新されたことを確認
SELECT id, position_name, updated_at FROM requirements 
WHERE position_name LIKE '%(更新テスト)%';

-- テスト2: candidatesテーブルでの動作確認
-- 候補者データがある場合
UPDATE candidates 
SET current_position = 'シニアエンジニア'
WHERE id = (SELECT id FROM candidates LIMIT 1);

-- updated_atが更新されているか確認
SELECT id, current_position, updated_at FROM candidates 
WHERE current_position = 'シニアエンジニア';
*/

-- ============================================
-- 5. トリガーの無効化/削除（必要な場合のみ）
-- ============================================

-- トリガーを一時的に無効化したい場合
-- ALTER TABLE requirements DISABLE TRIGGER update_requirements_updated_at;

-- トリガーを完全に削除したい場合
-- DROP TRIGGER IF EXISTS update_requirements_updated_at ON requirements;

-- トリガー関数自体を削除したい場合（全てのトリガーを削除後に実行）
-- DROP FUNCTION IF EXISTS update_updated_at_column();