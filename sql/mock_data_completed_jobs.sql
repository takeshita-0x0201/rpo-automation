-- 完了したジョブの多様なモックデータ
-- 複数のクライアント、採用要件、候補者パターンを含む

-- =====================================
-- 1. クライアントデータ
-- =====================================
INSERT INTO clients (id, name, industry, company_size, is_active)
VALUES 
    -- IT企業
    ('c1111111-1111-1111-1111-111111111111', '株式会社テックイノベーション', 'IT', 'large', true),
    ('c2222222-2222-2222-2222-222222222222', 'スタートアップAI株式会社', 'IT', 'startup', true),
    
    -- 金融
    ('c3333333-3333-3333-3333-333333333333', '第一デジタル銀行', '金融', 'large', true),
    
    -- 製造業
    ('c4444444-4444-4444-4444-444444444444', '日本製造テック株式会社', '製造', 'large', true),
    
    -- 小売
    ('c5555555-5555-5555-5555-555555555555', 'ECコマース株式会社', '小売', 'medium', true)
ON CONFLICT (id) DO NOTHING;

-- =====================================
-- 2. 採用要件データ
-- =====================================
INSERT INTO job_requirements (id, client_id, title, description, created_by, structured_data, is_active)
VALUES 
    -- テックイノベーション社の要件
    ('r1111111-1111-1111-1111-111111111111', 
     'c1111111-1111-1111-1111-111111111111',
     'フルスタックエンジニア',
     'Web アプリケーション開発全般を担当',
     (SELECT id FROM profiles LIMIT 1),
     '{
       "required_skills": ["React", "Node.js", "TypeScript", "AWS"],
       "preferred_skills": ["Next.js", "GraphQL", "Docker"],
       "experience_years": "3年以上",
       "team_size": "6名",
       "salary_range": "600-900万円"
     }'::jsonb,
     true),
     
    -- スタートアップAI社の要件
    ('r2222222-2222-2222-2222-222222222222',
     'c2222222-2222-2222-2222-222222222222',
     'AIエンジニア/データサイエンティスト',
     '機械学習モデルの開発と実装',
     (SELECT id FROM profiles LIMIT 1),
     '{
       "required_skills": ["Python", "機械学習", "深層学習", "TensorFlow/PyTorch"],
       "preferred_skills": ["NLP", "Computer Vision", "MLOps"],
       "experience_years": "3年以上",
       "team_size": "4名",
       "salary_range": "700-1200万円"
     }'::jsonb,
     true),
     
    -- デジタル銀行の要件
    ('r3333333-3333-3333-3333-333333333333',
     'c3333333-3333-3333-3333-333333333333',
     'セキュリティエンジニア',
     '金融システムのセキュリティ強化',
     (SELECT id FROM profiles LIMIT 1),
     '{
       "required_skills": ["セキュリティ", "ネットワーク", "AWS Security", "監査"],
       "preferred_skills": ["CISSP", "金融業界経験", "ペネトレーションテスト"],
       "experience_years": "5年以上",
       "team_size": "5名",
       "salary_range": "800-1200万円"
     }'::jsonb,
     true),
     
    -- 製造テック社の要件
    ('r4444444-4444-4444-4444-444444444444',
     'c4444444-4444-4444-4444-444444444444',
     'IoTエンジニア',
     '工場のスマート化プロジェクト',
     (SELECT id FROM profiles LIMIT 1),
     '{
       "required_skills": ["組み込み開発", "C/C++", "IoT", "Linux"],
       "preferred_skills": ["Python", "機械学習", "エッジコンピューティング"],
       "experience_years": "4年以上",
       "team_size": "8名",
       "salary_range": "600-900万円"
     }'::jsonb,
     true),
     
    -- ECコマース社の要件
    ('r5555555-5555-5555-5555-555555555555',
     'c5555555-5555-5555-5555-555555555555',
     'プロダクトマネージャー',
     'ECプラットフォームの企画・改善',
     (SELECT id FROM profiles LIMIT 1),
     '{
       "required_skills": ["プロダクトマネジメント", "データ分析", "UX理解", "アジャイル"],
       "preferred_skills": ["SQL", "A/Bテスト", "グロースハック"],
       "experience_years": "5年以上",
       "team_size": "10名",
       "salary_range": "800-1100万円"
     }'::jsonb,
     true)
ON CONFLICT (id) DO NOTHING;

-- =====================================
-- 3. 完了したジョブデータ
-- =====================================
INSERT INTO jobs (
    id, job_type, client_id, status, priority, parameters, progress,
    started_at, completed_at, created_by, created_at
)
VALUES 
    -- ジョブ1: フルスタックエンジニア（高マッチ多数）
    ('j1111111-1111-1111-1111-111111111111',
     'ai_matching',
     'c1111111-1111-1111-1111-111111111111',
     'completed',
     'high',
     '{"requirement_id": "r1111111-1111-1111-1111-111111111111"}'::jsonb,
     100,
     NOW() - INTERVAL '3 days',
     NOW() - INTERVAL '3 days' + INTERVAL '2 hours',
     (SELECT id FROM profiles LIMIT 1),
     NOW() - INTERVAL '4 days'),
     
    -- ジョブ2: AIエンジニア（少数精鋭）
    ('j2222222-2222-2222-2222-222222222222',
     'ai_matching',
     'c2222222-2222-2222-2222-222222222222',
     'completed',
     'normal',
     '{"requirement_id": "r2222222-2222-2222-2222-222222222222"}'::jsonb,
     100,
     NOW() - INTERVAL '2 days',
     NOW() - INTERVAL '2 days' + INTERVAL '1 hour',
     (SELECT id FROM profiles LIMIT 1),
     NOW() - INTERVAL '3 days'),
     
    -- ジョブ3: セキュリティエンジニア（難易度高）
    ('j3333333-3333-3333-3333-333333333333',
     'ai_matching',
     'c3333333-3333-3333-3333-333333333333',
     'completed',
     'high',
     '{"requirement_id": "r3333333-3333-3333-3333-333333333333"}'::jsonb,
     100,
     NOW() - INTERVAL '1 day',
     NOW() - INTERVAL '1 day' + INTERVAL '3 hours',
     (SELECT id FROM profiles LIMIT 1),
     NOW() - INTERVAL '2 days'),
     
    -- ジョブ4: IoTエンジニア
    ('j4444444-4444-4444-4444-444444444444',
     'ai_matching',
     'c4444444-4444-4444-4444-444444444444',
     'completed',
     'normal',
     '{"requirement_id": "r4444444-4444-4444-4444-444444444444"}'::jsonb,
     100,
     NOW() - INTERVAL '5 hours',
     NOW() - INTERVAL '3 hours',
     (SELECT id FROM profiles LIMIT 1),
     NOW() - INTERVAL '6 hours'),
     
    -- ジョブ5: プロダクトマネージャー
    ('j5555555-5555-5555-5555-555555555555',
     'ai_matching',
     'c5555555-5555-5555-5555-555555555555',
     'completed',
     'normal',
     '{"requirement_id": "r5555555-5555-5555-5555-555555555555"}'::jsonb,
     100,
     NOW() - INTERVAL '12 hours',
     NOW() - INTERVAL '10 hours',
     (SELECT id FROM profiles LIMIT 1),
     NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

-- =====================================
-- 4. 候補者データとAI評価（各ジョブ用）
-- =====================================

-- ジョブ1用候補者（フルスタックエンジニア - 8名）
INSERT INTO candidates (id, candidate_id, candidate_link, candidate_company, candidate_resume, platform, client_id, requirement_id, created_at)
VALUES 
    ('cd111111-1111-1111-1111-111111111111', 'FS001', 'https://bizreach.jp/FS001', 
     '株式会社モダンウェブ', 'React/Node.js 5年、TypeScript 3年、AWS認定保有', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days'),
     
    ('cd111112-1111-1111-1111-111111111112', 'FS002', 'https://bizreach.jp/FS002',
     'テックスタートアップ株式会社', 'フルスタック開発4年、Next.js実務経験、GraphQL導入経験', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days'),
     
    ('cd111113-1111-1111-1111-111111111113', 'FS003', 'https://bizreach.jp/FS003',
     'フリーランス', 'Web開発6年、React/Vue.js両方経験、バックエンドはRuby中心', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days'),
     
    ('cd111114-1111-1111-1111-111111111114', 'FS004', 'https://bizreach.jp/FS004',
     '大手SIer', 'Java開発10年、最近フロントエンドも学習中', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days'),
     
    ('cd111115-1111-1111-1111-111111111115', 'FS005', 'https://bizreach.jp/FS005',
     '株式会社デジタルソリューション', 'TypeScript 4年、React/Next.js、AWS ECS/Fargate運用', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days'),
     
    ('cd111116-1111-1111-1111-111111111116', 'FS006', 'https://bizreach.jp/FS006',
     'ベンチャー企業', 'MERN Stack 3年、Docker/K8s経験あり', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days'),
     
    ('cd111117-1111-1111-1111-111111111117', 'FS007', 'https://bizreach.jp/FS007',
     'EC企業', 'フロントエンド専門5年、React/Vue.js、Node.js基礎知識', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days'),
     
    ('cd111118-1111-1111-1111-111111111118', 'FS008', 'https://bizreach.jp/FS008',
     'ゲーム会社', 'Unity開発3年、Web開発に転向希望', 'bizreach',
     'c1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', NOW() - INTERVAL '3 days')
ON CONFLICT (id) DO NOTHING;

-- ジョブ1のAI評価
INSERT INTO ai_evaluations (id, candidate_id, requirement_id, search_id, ai_score, match_reasons, concerns, recommendation, model_version, evaluated_at)
VALUES
    ('ae111111-1111-1111-1111-111111111111', 'cd111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.95, 
     ARRAY['全ての必須スキルを満たす', 'AWS認定保有で信頼性高い', '実務経験が要件を上回る'],
     ARRAY[]::text[],
     'high', 'gpt-4', NOW() - INTERVAL '3 days'),
     
    ('ae111112-1111-1111-1111-111111111112', 'cd111112-1111-1111-1111-111111111112', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.92,
     ARRAY['Next.js/GraphQLの経験が歓迎要件と合致', 'スタートアップ経験でスピード感あり'],
     ARRAY['Node.js経験がやや少ない'],
     'high', 'gpt-4', NOW() - INTERVAL '3 days'),
     
    ('ae111113-1111-1111-1111-111111111113', 'cd111113-1111-1111-1111-111111111113', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.75,
     ARRAY['フルスタック経験豊富', 'フリーランスで多様なプロジェクト経験'],
     ARRAY['Node.jsではなくRuby中心', 'TypeScript経験が不明'],
     'medium', 'gpt-4', NOW() - INTERVAL '3 days'),
     
    ('ae111114-1111-1111-1111-111111111114', 'cd111114-1111-1111-1111-111111111114', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.45,
     ARRAY['開発経験は豊富', '学習意欲あり'],
     ARRAY['フロントエンド実務経験不足', 'モダンな技術スタックの経験なし', 'SIer文化とのギャップ'],
     'low', 'gpt-4', NOW() - INTERVAL '3 days'),
     
    ('ae111115-1111-1111-1111-111111111115', 'cd111115-1111-1111-1111-111111111115', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.93,
     ARRAY['TypeScript経験豊富', 'AWS実運用経験', 'モダンな技術スタック'],
     ARRAY[]::text[],
     'high', 'gpt-4', NOW() - INTERVAL '3 days'),
     
    ('ae111116-1111-1111-1111-111111111116', 'cd111116-1111-1111-1111-111111111116', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.88,
     ARRAY['MERN Stack経験', 'コンテナ技術の知識'],
     ARRAY['経験年数が要件ギリギリ'],
     'high', 'gpt-4', NOW() - INTERVAL '3 days'),
     
    ('ae111117-1111-1111-1111-111111111117', 'cd111117-1111-1111-1111-111111111117', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.65,
     ARRAY['フロントエンド専門性高い', 'React経験豊富'],
     ARRAY['バックエンド実務経験不足', 'フルスタックとは言い難い'],
     'medium', 'gpt-4', NOW() - INTERVAL '3 days'),
     
    ('ae111118-1111-1111-1111-111111111118', 'cd111118-1111-1111-1111-111111111118', 'r1111111-1111-1111-1111-111111111111', 'j1111111-1111-1111-1111-111111111111',
     0.30,
     ARRAY['プログラミング基礎力あり'],
     ARRAY['Web開発経験なし', '必須スキル不足', '転向リスク高い'],
     'low', 'gpt-4', NOW() - INTERVAL '3 days')
ON CONFLICT (id) DO NOTHING;

-- ジョブ2用候補者（AIエンジニア - 4名）
INSERT INTO candidates (id, candidate_id, candidate_link, candidate_company, candidate_resume, platform, client_id, requirement_id, created_at)
VALUES
    ('cd222221-2222-2222-2222-222222222221', 'AI001', 'https://bizreach.jp/AI001',
     '研究機関', 'Deep Learning研究5年、論文多数、PyTorch/TensorFlow', 'bizreach',
     'c2222222-2222-2222-2222-222222222222', 'r2222222-2222-2222-2222-222222222222', NOW() - INTERVAL '2 days'),
     
    ('cd222222-2222-2222-2222-222222222222', 'AI002', 'https://bizreach.jp/AI002',
     'AI スタートアップ', 'MLエンジニア3年、NLP専門、BERT/GPT実装経験', 'bizreach',
     'c2222222-2222-2222-2222-222222222222', 'r2222222-2222-2222-2222-222222222222', NOW() - INTERVAL '2 days'),
     
    ('cd222223-2222-2222-2222-222222222223', 'AI003', 'https://bizreach.jp/AI003',
     'コンサル会社', 'データ分析3年、機械学習初級、統計学修士', 'bizreach',
     'c2222222-2222-2222-2222-222222222222', 'r2222222-2222-2222-2222-222222222222', NOW() - INTERVAL '2 days'),
     
    ('cd222224-2222-2222-2222-222222222224', 'AI004', 'https://bizreach.jp/AI004',
     '大手メーカー', 'Computer Vision 4年、製造業AI導入、エッジAI経験', 'bizreach',
     'c2222222-2222-2222-2222-222222222222', 'r2222222-2222-2222-2222-222222222222', NOW() - INTERVAL '2 days')
ON CONFLICT (id) DO NOTHING;

-- ジョブ2のAI評価
INSERT INTO ai_evaluations (id, candidate_id, requirement_id, search_id, ai_score, match_reasons, concerns, recommendation, model_version, evaluated_at)
VALUES
    ('ae222221-2222-2222-2222-222222222221', 'cd222221-2222-2222-2222-222222222221', 'r2222222-2222-2222-2222-222222222222', 'j2222222-2222-2222-2222-222222222222',
     0.90,
     ARRAY['深層学習の深い知識', '研究実績豊富', '最新技術への理解'],
     ARRAY['実務経験が研究中心', 'MLOps経験不明'],
     'high', 'gpt-4', NOW() - INTERVAL '2 days'),
     
    ('ae222222-2222-2222-2222-222222222222', 'cd222222-2222-2222-2222-222222222222', 'r2222222-2222-2222-2222-222222222222', 'j2222222-2222-2222-2222-222222222222',
     0.94,
     ARRAY['NLP実務経験', 'スタートアップでの実装経験', '最新モデルの知識'],
     ARRAY[]::text[],
     'high', 'gpt-4', NOW() - INTERVAL '2 days'),
     
    ('ae222223-2222-2222-2222-222222222223', 'cd222223-2222-2222-2222-222222222223', 'r2222222-2222-2222-2222-222222222222', 'j2222222-2222-2222-2222-222222222222',
     0.60,
     ARRAY['統計学の基礎', 'データ分析経験'],
     ARRAY['深層学習経験不足', '実装経験が少ない'],
     'medium', 'gpt-4', NOW() - INTERVAL '2 days'),
     
    ('ae222224-2222-2222-2222-222222222224', 'cd222224-2222-2222-2222-222222222224', 'r2222222-2222-2222-2222-222222222222', 'j2222222-2222-2222-2222-222222222222',
     0.85,
     ARRAY['Computer Vision専門性', '実務での AI導入経験', 'エッジAIの知識'],
     ARRAY['NLP経験なし'],
     'high', 'gpt-4', NOW() - INTERVAL '2 days')
ON CONFLICT (id) DO NOTHING;

-- ジョブ3用候補者（セキュリティエンジニア - 3名）
INSERT INTO candidates (id, candidate_id, candidate_link, candidate_company, candidate_resume, platform, client_id, requirement_id, created_at)
VALUES
    ('cd333331-3333-3333-3333-333333333331', 'SEC001', 'https://bizreach.jp/SEC001',
     '大手金融機関', 'セキュリティ8年、CISSP保有、金融CSIRT経験', 'bizreach',
     'c3333333-3333-3333-3333-333333333333', 'r3333333-3333-3333-3333-333333333333', NOW() - INTERVAL '1 day'),
     
    ('cd333332-3333-3333-3333-333333333332', 'SEC002', 'https://bizreach.jp/SEC002',
     'セキュリティベンダー', 'ペネトレーション5年、AWS Security専門', 'bizreach',
     'c3333333-3333-3333-3333-333333333333', 'r3333333-3333-3333-3333-333333333333', NOW() - INTERVAL '1 day'),
     
    ('cd333333-3333-3333-3333-333333333333', 'SEC003', 'https://bizreach.jp/SEC003',
     'IT企業', 'インフラエンジニア6年、セキュリティは独学', 'bizreach',
     'c3333333-3333-3333-3333-333333333333', 'r3333333-3333-3333-3333-333333333333', NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

-- ジョブ3のAI評価
INSERT INTO ai_evaluations (id, candidate_id, requirement_id, search_id, ai_score, match_reasons, concerns, recommendation, model_version, evaluated_at)
VALUES
    ('ae333331-3333-3333-3333-333333333331', 'cd333331-3333-3333-3333-333333333331', 'r3333333-3333-3333-3333-333333333333', 'j3333333-3333-3333-3333-333333333333',
     0.96,
     ARRAY['完璧な要件マッチ', '金融業界経験', 'CISSP保有', 'CSIRT実務経験'],
     ARRAY[]::text[],
     'high', 'gpt-4', NOW() - INTERVAL '1 day'),
     
    ('ae333332-3333-3333-3333-333333333332', 'cd333332-3333-3333-3333-333333333332', 'r3333333-3333-3333-3333-333333333333', 'j3333333-3333-3333-3333-333333333333',
     0.82,
     ARRAY['ペネトレーションテスト専門', 'AWS Security知識'],
     ARRAY['金融業界経験なし', '監査経験不明'],
     'medium', 'gpt-4', NOW() - INTERVAL '1 day'),
     
    ('ae333333-3333-3333-3333-333333333333', 'cd333333-3333-3333-3333-333333333333', 'r3333333-3333-3333-3333-333333333333', 'j3333333-3333-3333-3333-333333333333',
     0.40,
     ARRAY['インフラ知識あり'],
     ARRAY['セキュリティ実務経験なし', '資格なし', '独学レベル'],
     'low', 'gpt-4', NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

-- ジョブ4用候補者（IoTエンジニア - 5名）
INSERT INTO candidates (id, candidate_id, candidate_link, candidate_company, candidate_resume, platform, client_id, requirement_id, created_at)
VALUES
    ('cd444441-4444-4444-4444-444444444441', 'IOT001', 'https://bizreach.jp/IOT001',
     '電機メーカー', '組み込み開発6年、Linux/RTOS、C/C++、産業IoT経験', 'bizreach',
     'c4444444-4444-4444-4444-444444444444', 'r4444444-4444-4444-4444-444444444444', NOW() - INTERVAL '5 hours'),
     
    ('cd444442-4444-4444-4444-444444444442', 'IOT002', 'https://bizreach.jp/IOT002',
     'IoTスタートアップ', 'エッジコンピューティング4年、Python/機械学習統合', 'bizreach',
     'c4444444-4444-4444-4444-444444444444', 'r4444444-4444-4444-4444-444444444444', NOW() - INTERVAL '5 hours'),
     
    ('cd444443-4444-4444-4444-444444444443', 'IOT003', 'https://bizreach.jp/IOT003',
     '自動車メーカー', '車載システム5年、CAN通信、機能安全', 'bizreach',
     'c4444444-4444-4444-4444-444444444444', 'r4444444-4444-4444-4444-444444444444', NOW() - INTERVAL '5 hours'),
     
    ('cd444444-4444-4444-4444-444444444444', 'IOT004', 'https://bizreach.jp/IOT004',
     'Web企業', 'Webエンジニア4年、IoTに興味あり', 'bizreach',
     'c4444444-4444-4444-4444-444444444444', 'r4444444-4444-4444-4444-444444444444', NOW() - INTERVAL '5 hours'),
     
    ('cd444445-4444-4444-4444-444444444445', 'IOT005', 'https://bizreach.jp/IOT005',
     '研究所', '組み込みLinux専門、産業用ロボット制御', 'bizreach',
     'c4444444-4444-4444-4444-444444444444', 'r4444444-4444-4444-4444-444444444444', NOW() - INTERVAL '5 hours')
ON CONFLICT (id) DO NOTHING;

-- ジョブ4のAI評価
INSERT INTO ai_evaluations (id, candidate_id, requirement_id, search_id, ai_score, match_reasons, concerns, recommendation, model_version, evaluated_at)
VALUES
    ('ae444441-4444-4444-4444-444444444441', 'cd444441-4444-4444-4444-444444444441', 'r4444444-4444-4444-4444-444444444444', 'j4444444-4444-4444-4444-444444444444',
     0.91,
     ARRAY['組み込み開発経験豊富', '産業IoT経験あり', 'Linux精通'],
     ARRAY['機械学習経験が不明'],
     'high', 'gpt-4', NOW() - INTERVAL '3 hours'),
     
    ('ae444442-4444-4444-4444-444444444442', 'cd444442-4444-4444-4444-444444444442', 'r4444444-4444-4444-4444-444444444444', 'j4444444-4444-4444-4444-444444444444',
     0.95,
     ARRAY['エッジコンピューティング専門', 'Python/ML統合経験', '最新技術への理解'],
     ARRAY[]::text[],
     'high', 'gpt-4', NOW() - INTERVAL '3 hours'),
     
    ('ae444443-4444-4444-4444-444444444443', 'cd444443-4444-4444-4444-444444444443', 'r4444444-4444-4444-4444-444444444444', 'j4444444-4444-4444-4444-444444444444',
     0.78,
     ARRAY['組み込み経験豊富', '車載システムの知識'],
     ARRAY['IoT/ネットワーク経験不足', '工場系システム未経験'],
     'medium', 'gpt-4', NOW() - INTERVAL '3 hours'),
     
    ('ae444444-4444-4444-4444-444444444444', 'cd444444-4444-4444-4444-444444444444', 'r4444444-4444-4444-4444-444444444444', 'j4444444-4444-4444-4444-444444444444',
     0.25,
     ARRAY['プログラミング能力あり'],
     ARRAY['組み込み開発経験なし', 'C/C++経験なし', 'ハードウェア知識不足'],
     'low', 'gpt-4', NOW() - INTERVAL '3 hours'),
     
    ('ae444445-4444-4444-4444-444444444445', 'cd444445-4444-4444-4444-444444444445', 'r4444444-4444-4444-4444-444444444444', 'j4444444-4444-4444-4444-444444444444',
     0.87,
     ARRAY['組み込みLinux専門', 'ロボット制御経験'],
     ARRAY['IoTプロトコルの経験不明'],
     'high', 'gpt-4', NOW() - INTERVAL '3 hours')
ON CONFLICT (id) DO NOTHING;

-- ジョブ5用候補者（プロダクトマネージャー - 6名）
INSERT INTO candidates (id, candidate_id, candidate_link, candidate_company, candidate_resume, platform, client_id, requirement_id, created_at)
VALUES
    ('cd555551-5555-5555-5555-555555555551', 'PM001', 'https://bizreach.jp/PM001',
     '大手EC企業', 'PM 7年、MAU 1000万のアプリ改善、A/Bテスト実施', 'bizreach',
     'c5555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', NOW() - INTERVAL '12 hours'),
     
    ('cd555552-5555-5555-5555-555555555552', 'PM002', 'https://bizreach.jp/PM002',
     'スタートアップ', 'プロダクトマネージャー5年、グロースハック、SQL使える', 'bizreach',
     'c5555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', NOW() - INTERVAL '12 hours'),
     
    ('cd555553-5555-5555-5555-555555555553', 'PM003', 'https://bizreach.jp/PM003',
     'コンサル', 'ビジネスアナリスト4年、データ分析得意', 'bizreach',
     'c5555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', NOW() - INTERVAL '12 hours'),
     
    ('cd555554-5555-5555-5555-555555555554', 'PM004', 'https://bizreach.jp/PM004',
     'デザイン会社', 'UXデザイナー6年、プロダクト企画も担当', 'bizreach',
     'c5555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', NOW() - INTERVAL '12 hours'),
     
    ('cd555555-5555-5555-5555-555555555555', 'PM005', 'https://bizreach.jp/PM005',
     'SaaS企業', 'PM 5年、B2B SaaS、アジャイル開発、OKR運用', 'bizreach',
     'c5555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', NOW() - INTERVAL '12 hours'),
     
    ('cd555556-5555-5555-5555-555555555556', 'PM006', 'https://bizreach.jp/PM006',
     '営業出身', '営業5年、最近PMに転向', 'bizreach',
     'c5555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', NOW() - INTERVAL '12 hours')
ON CONFLICT (id) DO NOTHING;

-- ジョブ5のAI評価
INSERT INTO ai_evaluations (id, candidate_id, requirement_id, search_id, ai_score, match_reasons, concerns, recommendation, model_version, evaluated_at)
VALUES
    ('ae555551-5555-5555-5555-555555555551', 'cd555551-5555-5555-5555-555555555551', 'r5555555-5555-5555-5555-555555555555', 'j5555555-5555-5555-5555-555555555555',
     0.97,
     ARRAY['EC業界でのPM経験', '大規模サービスの改善実績', 'A/Bテスト実施経験'],
     ARRAY[]::text[],
     'high', 'gpt-4', NOW() - INTERVAL '10 hours'),
     
    ('ae555552-5555-5555-5555-555555555552', 'cd555552-5555-5555-5555-555555555552', 'r5555555-5555-5555-5555-555555555555', 'j5555555-5555-5555-5555-555555555555',
     0.89,
     ARRAY['グロースハック経験', 'SQL使用可能', 'スタートアップでのスピード感'],
     ARRAY['大規模チームの経験不明'],
     'high', 'gpt-4', NOW() - INTERVAL '10 hours'),
     
    ('ae555553-5555-5555-5555-555555555553', 'cd555553-5555-5555-5555-555555555553', 'r5555555-5555-5555-5555-555555555555', 'j5555555-5555-5555-5555-555555555555',
     0.70,
     ARRAY['データ分析力', 'ビジネス理解'],
     ARRAY['PM実務経験不足', 'プロダクト開発経験なし'],
     'medium', 'gpt-4', NOW() - INTERVAL '10 hours'),
     
    ('ae555554-5555-5555-5555-555555555554', 'cd555554-5555-5555-5555-555555555554', 'r5555555-5555-5555-5555-555555555555', 'j5555555-5555-5555-5555-555555555555',
     0.75,
     ARRAY['UX理解が深い', 'プロダクト企画経験'],
     ARRAY['PMとしての実績不明', 'データ分析経験不明'],
     'medium', 'gpt-4', NOW() - INTERVAL '10 hours'),
     
    ('ae555555-5555-5555-5555-555555555555', 'cd555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', 'j5555555-5555-5555-5555-555555555555',
     0.85,
     ARRAY['PM経験5年で要件満たす', 'アジャイル/OKR経験'],
     ARRAY['B2C経験なし', 'EC業界未経験'],
     'high', 'gpt-4', NOW() - INTERVAL '10 hours'),
     
    ('ae555556-5555-5555-5555-555555555556', 'cd555556-5555-5555-5555-555555555556', 'r5555555-5555-5555-5555-555555555555', 'j5555555-5555-5555-5555-555555555555',
     0.35,
     ARRAY['顧客理解力'],
     ARRAY['PM経験が浅い', '技術理解不足', 'データ分析経験なし'],
     'low', 'gpt-4', NOW() - INTERVAL '10 hours')
ON CONFLICT (id) DO NOTHING;

-- =====================================
-- 5. 検索セッションデータ（オプション）
-- =====================================
INSERT INTO searches (id, requirement_id, client_id, started_at, completed_at, status, execution_mode, total_candidates, evaluated_candidates, matched_candidates, created_by)
VALUES
    ('j1111111-1111-1111-1111-111111111111', 'r1111111-1111-1111-1111-111111111111', 'c1111111-1111-1111-1111-111111111111',
     NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days' + INTERVAL '2 hours', 'completed', 'manual', 8, 8, 4, (SELECT id FROM profiles LIMIT 1)),
     
    ('j2222222-2222-2222-2222-222222222222', 'r2222222-2222-2222-2222-222222222222', 'c2222222-2222-2222-2222-222222222222',
     NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '1 hour', 'completed', 'manual', 4, 4, 3, (SELECT id FROM profiles LIMIT 1)),
     
    ('j3333333-3333-3333-3333-333333333333', 'r3333333-3333-3333-3333-333333333333', 'c3333333-3333-3333-3333-333333333333',
     NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day' + INTERVAL '3 hours', 'completed', 'manual', 3, 3, 1, (SELECT id FROM profiles LIMIT 1)),
     
    ('j4444444-4444-4444-4444-444444444444', 'r4444444-4444-4444-4444-444444444444', 'c4444444-4444-4444-4444-444444444444',
     NOW() - INTERVAL '5 hours', NOW() - INTERVAL '3 hours', 'completed', 'manual', 5, 5, 3, (SELECT id FROM profiles LIMIT 1)),
     
    ('j5555555-5555-5555-5555-555555555555', 'r5555555-5555-5555-5555-555555555555', 'c5555555-5555-5555-5555-555555555555',
     NOW() - INTERVAL '12 hours', NOW() - INTERVAL '10 hours', 'completed', 'manual', 6, 6, 3, (SELECT id FROM profiles LIMIT 1))
ON CONFLICT (id) DO NOTHING;

-- =====================================
-- 確認用サマリー
-- =====================================
SELECT 
    j.id as job_id,
    c.name as client_name,
    jr.title as position,
    j.status,
    j.completed_at,
    COUNT(DISTINCT cd.id) as total_candidates,
    COUNT(DISTINCT CASE WHEN ae.recommendation = 'high' THEN ae.id END) as high_recommendations,
    COUNT(DISTINCT CASE WHEN ae.recommendation = 'medium' THEN ae.id END) as medium_recommendations,
    COUNT(DISTINCT CASE WHEN ae.recommendation = 'low' THEN ae.id END) as low_recommendations
FROM jobs j
JOIN clients c ON j.client_id = c.id
JOIN job_requirements jr ON j.parameters->>'requirement_id' = jr.id::text
LEFT JOIN candidates cd ON cd.requirement_id = jr.id
LEFT JOIN ai_evaluations ae ON ae.candidate_id = cd.id
WHERE j.status = 'completed'
  AND j.job_type = 'ai_matching'
GROUP BY j.id, c.name, jr.title, j.status, j.completed_at
ORDER BY j.completed_at DESC;