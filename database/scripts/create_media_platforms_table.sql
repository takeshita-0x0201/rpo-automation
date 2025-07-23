-- media_platforms（媒体プラットフォーム）テーブルの作成
CREATE TABLE IF NOT EXISTS media_platforms (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 初期データの投入
INSERT INTO media_platforms (name, display_name, description, sort_order) VALUES
    ('bizreach', 'ビズリーチ', '即戦力人材の転職サイト', 1),
    ('linkedin', 'LinkedIn', 'ビジネス特化型SNS', 2),
    ('green', 'Green', 'IT/Web業界の転職サイト', 3),
    ('wantedly', 'Wantedly', 'やりがいでつながる転職サイト', 4),
    ('doda', 'doda', '転職求人サイト', 5),
    ('recruit_agent', 'リクルートエージェント', '転職エージェントサービス', 6),
    ('indeed', 'Indeed', '求人検索エンジン', 7),
    ('other', 'その他', 'その他の媒体', 99)
ON CONFLICT (name) DO NOTHING;

-- clientsテーブルにmedia_platform_idカラムを追加
ALTER TABLE clients 
ADD COLUMN IF NOT EXISTS media_platform_id UUID REFERENCES media_platforms(id);

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_clients_media_platform ON clients(media_platform_id);
CREATE INDEX IF NOT EXISTS idx_media_platforms_active ON media_platforms(is_active);
CREATE INDEX IF NOT EXISTS idx_media_platforms_sort ON media_platforms(sort_order);

-- RLSポリシーの設定
ALTER TABLE media_platforms ENABLE ROW LEVEL SECURITY;

-- 全ユーザーが媒体一覧を閲覧可能
CREATE POLICY "Everyone can view media platforms" ON media_platforms
    FOR SELECT
    USING (true);

-- 管理者のみが媒体を管理可能
CREATE POLICY "Admins can manage media platforms" ON media_platforms
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM auth.users
            WHERE auth.users.id = auth.uid()
            AND auth.users.raw_user_meta_data->>'role' = 'admin'
        )
    );

-- コメント
COMMENT ON TABLE media_platforms IS '媒体プラットフォームマスタ';
COMMENT ON COLUMN media_platforms.name IS '媒体の識別子（システム内部で使用）';
COMMENT ON COLUMN media_platforms.display_name IS '表示名';
COMMENT ON COLUMN media_platforms.description IS '媒体の説明';
COMMENT ON COLUMN media_platforms.sort_order IS '表示順序';
COMMENT ON COLUMN clients.media_platform_id IS '使用する媒体プラットフォームのID';