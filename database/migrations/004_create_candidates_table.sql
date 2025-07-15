-- candidatesテーブルの作成（Supabase版）
-- Chrome拡張機能でスクレイピングした候補者データを格納

-- テーブル作成
CREATE TABLE IF NOT EXISTS candidates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- セッション情報
  search_id TEXT,
  session_id TEXT,
  
  -- 候補者基本情報
  name TEXT,
  bizreach_id TEXT,
  bizreach_url TEXT,
  current_title TEXT,
  current_position TEXT,
  current_company TEXT,
  
  -- スキルと経験
  experience_years INTEGER,
  skills TEXT[],
  education TEXT,
  
  -- プロフィール
  profile_url TEXT,
  profile_summary TEXT,
  
  -- スクレイピング情報
  scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  scraped_by TEXT,
  platform TEXT DEFAULT 'bizreach',
  
  -- 追加データ（JSON形式）
  -- client_id, requirement_id, age, salary_range等を格納
  scraped_data JSONB,
  
  -- メタデータ
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックスの作成（パフォーマンス最適化）
CREATE INDEX idx_candidates_scraped_at ON candidates(scraped_at DESC);
CREATE INDEX idx_candidates_company ON candidates(current_company);
CREATE INDEX idx_candidates_search_id ON candidates(search_id);
CREATE INDEX idx_candidates_client_id ON candidates((scraped_data->>'client_id'));
CREATE INDEX idx_candidates_skills ON candidates USING GIN(skills);

-- RLS (Row Level Security) の設定
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

-- 認証されたユーザーのみアクセス可能
CREATE POLICY "Authenticated users can view candidates" ON candidates
  FOR SELECT TO authenticated
  USING (true);

-- 管理者とマネージャーのみ作成・更新・削除可能
CREATE POLICY "Admin and manager can manage candidates" ON candidates
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users 
      WHERE users.email = auth.email() 
      AND users.role IN ('admin', 'manager')
    )
  );

-- 更新時のタイムスタンプ自動更新
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_candidates_updated_at
  BEFORE UPDATE ON candidates
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- テーブルコメント
COMMENT ON TABLE candidates IS 'BizReachからスクレイピングした候補者データ';
COMMENT ON COLUMN candidates.scraped_data IS 'client_id, requirement_id等の追加情報をJSON形式で格納';