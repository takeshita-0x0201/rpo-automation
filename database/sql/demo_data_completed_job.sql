-- 完了したAIマッチングジョブのデモデータ作成
-- 前提: clients, job_requirements, candidatesテーブルにデータが存在すること

-- 1. デモ用のクライアントを作成（既存の場合はスキップ）
INSERT INTO clients (id, name, industry, company_size, is_active)
VALUES 
    ('11111111-1111-1111-1111-111111111111', '株式会社テックコーポレーション', 'IT', 'large', true)
ON CONFLICT (id) DO NOTHING;

-- 2. デモ用の採用要件を作成
INSERT INTO job_requirements (id, client_id, title, description, created_by, structured_data, is_active)
VALUES 
    ('22222222-2222-2222-2222-222222222222', 
     '11111111-1111-1111-1111-111111111111',
     'バックエンドエンジニア（テックリード）',
     'ECサイトのバックエンド開発をリードしていただけるエンジニアを募集',
     (SELECT id FROM profiles LIMIT 1),
     '{
       "required_skills": ["Java", "Spring Boot", "AWS", "チームリード経験"],
       "preferred_skills": ["Kubernetes", "マイクロサービス", "DDD"],
       "experience_years": "5年以上",
       "team_size": "8名",
       "salary_range": "700-1000万円"
     }'::jsonb,
     true)
ON CONFLICT (id) DO NOTHING;

-- 3. 完了したAIマッチングジョブを作成
INSERT INTO jobs (
    id, 
    job_type, 
    client_id, 
    status, 
    priority,
    parameters,
    progress,
    started_at,
    completed_at,
    created_by,
    created_at
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    'ai_matching',
    '11111111-1111-1111-1111-111111111111',
    'completed',
    'normal',
    '{
        "requirement_id": "22222222-2222-2222-2222-222222222222",
        "data_source": "latest",
        "matching_threshold": "medium",
        "output_sheets": true
    }'::jsonb,
    100,
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '30 minutes',
    (SELECT id FROM profiles LIMIT 1),
    NOW() - INTERVAL '3 hours'
)
ON CONFLICT (id) DO NOTHING;

-- 4. デモ用の候補者データを作成
INSERT INTO candidates (
    id,
    candidate_id,
    candidate_link,
    candidate_company,
    candidate_resume,
    platform,
    client_id,
    requirement_id,
    scraping_session_id,
    created_at
)
VALUES 
    -- 高評価候補者1
    ('44444444-4444-4444-4444-444444444444',
     'BZ2024001',
     'https://www.bizreach.jp/candidates/BZ2024001',
     '株式会社イノベーションテック',
     'バックエンドエンジニア（7年）
     
【職務経歴】
2020-現在: 株式会社イノベーションテック / シニアエンジニア
- ECプラットフォームのバックエンド開発
- マイクロサービスアーキテクチャの設計・実装
- 5名のチームリード経験
- AWS環境での大規模システム運用

2017-2020: 株式会社デジタルソリューション / エンジニア  
- Javaを使用したWebアプリケーション開発
- Spring BootでのREST API実装
- PostgreSQLのパフォーマンスチューニング

【技術スキル】
- Java (7年)
- Spring Boot (5年)
- AWS (EC2, RDS, Lambda, ECS) (4年)
- Docker/Kubernetes (2年)
- マイクロサービス設計
- チームマネジメント',
     'bizreach',
     '11111111-1111-1111-1111-111111111111',
     '22222222-2222-2222-2222-222222222222',
     'session_001',
     NOW() - INTERVAL '1 day'
    ),
    
    -- 高評価候補者2
    ('55555555-5555-5555-5555-555555555555',
     'BZ2024002',
     'https://www.bizreach.jp/candidates/BZ2024002',
     '株式会社クラウドシステムズ',
     'テックリード（6年）
     
【職務経歴】
2019-現在: 株式会社クラウドシステムズ / テックリード
- 10名のエンジニアチームをリード
- サービス指向アーキテクチャの導入
- CI/CDパイプラインの構築
- 技術選定と設計レビュー

2018-2019: 同社 / シニアエンジニア
- Spring Bootを使用したマイクロサービス開発
- Kubernetesでのコンテナオーケストレーション
- 技術ブログ執筆、社内勉強会の主催

【技術スキル】
- Java (6年)
- Spring Boot (5年)  
- AWS (3年)
- Kubernetes (3年)
- DDD実践経験
- アジャイル/スクラム',
     'bizreach',
     '11111111-1111-1111-1111-111111111111',
     '22222222-2222-2222-2222-222222222222',
     'session_001',
     NOW() - INTERVAL '1 day'
    ),
    
    -- 中評価候補者
    ('66666666-6666-6666-6666-666666666666',
     'BZ2024003', 
     'https://www.bizreach.jp/candidates/BZ2024003',
     '大手SIer A社',
     'システムエンジニア（10年）
     
【職務経歴】
2014-現在: 大手SIer A社 / プロジェクトマネージャー
- 金融系システムの開発PM
- 20名規模のプロジェクト管理
- Java/Springでの開発経験あり
- オンプレミス環境での運用

【技術スキル】
- Java (10年)
- Spring Framework (5年)
- Oracle Database
- プロジェクトマネジメント
- 要件定義・設計',
     'bizreach',
     '11111111-1111-1111-1111-111111111111',
     '22222222-2222-2222-2222-222222222222',
     'session_001',
     NOW() - INTERVAL '1 day'
    ),
    
    -- 低評価候補者
    ('77777777-7777-7777-7777-777777777777',
     'BZ2024004',
     'https://www.bizreach.jp/candidates/BZ2024004',
     'フリーランス',
     'Webデザイナー/フロントエンドエンジニア（3年）
     
【職務経歴】
2021-現在: フリーランス
- Webサイトのデザイン・コーディング
- HTML/CSS/JavaScript
- React.jsでのSPA開発

【技術スキル】
- HTML/CSS (3年)
- JavaScript (2年)
- React.js (1年)
- デザインツール (Figma, Photoshop)',
     'bizreach',
     '11111111-1111-1111-1111-111111111111',
     '22222222-2222-2222-2222-222222222222',
     'session_001',
     NOW() - INTERVAL '1 day'
    );

-- 5. AI評価結果を作成
INSERT INTO ai_evaluations (
    id,
    candidate_id,
    requirement_id,
    search_id,
    ai_score,
    match_reasons,
    concerns,
    recommendation,
    detailed_evaluation,
    model_version,
    prompt_version,
    evaluated_at
)
VALUES
    -- 高評価候補者1の評価
    ('88888888-8888-8888-8888-888888888888',
     '44444444-4444-4444-4444-444444444444',
     '22222222-2222-2222-2222-222222222222',
     '33333333-3333-3333-3333-333333333333',
     0.92,
     ARRAY[
         '必須スキルを全て満たしている（Java 7年、Spring Boot 5年、AWS 4年、チームリード経験あり）',
         'マイクロサービスの実装経験があり、要件に合致',
         'ECプラットフォームの開発経験は貴社事業と親和性が高い'
     ],
     ARRAY[
         'Kubernetesの経験が2年とやや短い',
         'DDDの実践経験が明記されていない'
     ],
     'high',
     '{
         "skill_match": {
             "score": 0.95,
             "matched_skills": ["Java", "Spring Boot", "AWS", "チームリード", "マイクロサービス"],
             "missing_skills": ["DDD実践経験の明記なし"],
             "years_comparison": {
                 "java": {"required": 5, "actual": 7},
                 "team_lead": {"required": true, "actual": true}
             }
         },
         "experience_match": {
             "score": 0.90,
             "relevant_experience": "ECプラットフォーム開発",
             "team_size_match": "5名のリード経験（要件: 8名チーム）"
         },
         "salary_expectation": {
             "estimated_range": "800-900万円",
             "match_with_budget": true
         }
     }'::jsonb,
     'gpt-4',
     'v2.1',
     NOW() - INTERVAL '1 hour'
    ),
    
    -- 高評価候補者2の評価
    ('99999999-9999-9999-9999-999999999999',
     '55555555-5555-5555-5555-555555555555',
     '22222222-2222-2222-2222-222222222222',
     '33333333-3333-3333-3333-333333333333',
     0.88,
     ARRAY[
         '10名のチームリード経験があり、要件の8名を上回る',
         'Kubernetes 3年の経験で歓迎要件を満たす',
         'DDD実践経験あり、技術選定の経験も豊富'
     ],
     ARRAY[
         'AWS経験が3年とやや短い（要件: 5年相当を期待）',
         '現職の詳細な技術スタックが不明'
     ],
     'high',
     '{
         "skill_match": {
             "score": 0.90,
             "matched_skills": ["Java", "Spring Boot", "AWS", "Kubernetes", "DDD", "チームリード"],
             "strong_points": ["大規模チームのリード経験", "アーキテクチャ設計"]
         },
         "experience_match": {
             "score": 0.85,
             "team_management": "10名のチームリード（要件以上）",
             "technical_leadership": "技術選定、設計レビューの経験"
         }
     }'::jsonb,
     'gpt-4',
     'v2.1', 
     NOW() - INTERVAL '1 hour'
    ),
    
    -- 中評価候補者の評価
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
     '66666666-6666-6666-6666-666666666666',
     '22222222-2222-2222-2222-222222222222',
     '33333333-3333-3333-3333-333333333333',
     0.65,
     ARRAY[
         'Java経験が10年と豊富',
         '大規模プロジェクトのマネジメント経験',
         '金融系の堅牢なシステム開発経験'
     ],
     ARRAY[
         'AWS/クラウド経験が不足',
         'マイクロサービスの経験なし',
         'モダンな開発手法の経験が不明',
         'SIerの文化とスタートアップ文化のギャップ'
     ],
     'medium',
     '{
         "skill_match": {
             "score": 0.60,
             "matched_skills": ["Java", "Spring", "マネジメント"],
             "missing_skills": ["AWS", "Kubernetes", "マイクロサービス"],
             "concern": "クラウドネイティブな開発経験の不足"
         },
         "culture_fit": {
             "score": 0.70,
             "concern": "大手SIerからスタートアップへの転職はカルチャーギャップが懸念"
         }
     }'::jsonb,
     'gpt-4',
     'v2.1',
     NOW() - INTERVAL '1 hour'
    ),
    
    -- 低評価候補者の評価  
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
     '77777777-7777-7777-7777-777777777777',
     '22222222-2222-2222-2222-222222222222',
     '33333333-3333-3333-3333-333333333333',
     0.25,
     ARRAY[
         'Web開発の基礎知識はある',
         'フリーランスとして自己管理能力がある'
     ],
     ARRAY[
         'バックエンド開発経験が全くない',
         '必須スキル（Java, Spring Boot, AWS）を満たしていない',
         'チームリード経験なし',
         'フロントエンドエンジニアとバックエンドエンジニアは別職種'
     ],
     'low',
     '{
         "skill_match": {
             "score": 0.20,
             "matched_skills": [],
             "missing_skills": ["Java", "Spring Boot", "AWS", "バックエンド開発"],
             "mismatch": "フロントエンド専門でバックエンド経験なし"
         },
         "recommendation": "この候補者はフロントエンドポジションであれば検討の余地あり"
     }'::jsonb,
     'gpt-4',
     'v2.1',
     NOW() - INTERVAL '1 hour'
    );

-- 6. 検索セッションの作成（省略可）
INSERT INTO searches (
    id,
    requirement_id,
    client_id,
    started_at,
    completed_at,
    status,
    execution_mode,
    total_candidates,
    evaluated_candidates,
    matched_candidates,
    search_params,
    created_by
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '30 minutes',
    'completed',
    'manual',
    4,
    4,
    2,
    '{"platform": "bizreach", "keywords": ["Java", "エンジニア"]}'::jsonb,
    (SELECT id FROM profiles LIMIT 1)
)
ON CONFLICT (id) DO NOTHING;

-- 確認用クエリ
SELECT 
    'デモデータ作成完了' as status,
    'ジョブID: 33333333-3333-3333-3333-333333333333' as job_id,
    'クライアント: 株式会社テックコーポレーション' as client,
    '採用要件: バックエンドエンジニア（テックリード）' as requirement,
    '候補者数: 4名（高評価2名、中評価1名、低評価1名）' as candidates;