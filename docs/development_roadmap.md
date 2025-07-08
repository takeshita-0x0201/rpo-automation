# RPO Automation 開発ロードマップ

## 📊 現在の実装状況

### ✅ 完了済み
- **認証システム**
  - ログイン/ログアウト
  - JWT認証
  - ロールベースアクセス制御

- **UI/テンプレート**
  - 全画面のHTML作成
  - ロール別フォルダ構成
  - レスポンシブデザイン

- **基本的なCRUD**
  - ユーザー管理（作成・編集・削除・有効化/無効化）
  - クライアント管理（作成・編集・削除）

### ⚠️ 未実装（重要度順）
1. **データベース連携**
2. **コア機能（採用要件・検索）**
3. **外部API連携**
4. **バックグラウンドジョブ**
5. **通知機能**
6. **レポート機能**

---

## 🎯 開発優先順位（MVP approach）

### Phase 1: データベース基盤（1-2週間）
**目的**: データの永続化と基本的なCRUD操作を可能にする

```
優先度: 🔴 最高
理由: すべての機能の基盤となるため
```

#### タスク分解:
- [ ] Supabaseのテーブル設計・作成
  - [ ] requirementsテーブル
  - [ ] candidatesテーブル
  - [ ] search_jobsテーブル
  - [ ] search_resultsテーブル
- [ ] Pydanticモデルの作成
- [ ] データベース操作用のサービスクラス作成
- [ ] 既存のダミーデータをDBから取得するよう修正

### Phase 2: コア業務機能（2-3週間）
**目的**: RPO業務の基本フローを実装

```
優先度: 🔴 高
理由: ビジネス価値を提供する中核機能
```

#### A. 採用要件管理
- [ ] 要件の作成API
- [ ] 要件の一覧・詳細表示
- [ ] 要件の編集・削除
- [ ] ステータス管理（Draft/Active/Completed）

#### B. 候補者検索（シミュレーション）
- [ ] 検索条件の保存
- [ ] ダミーデータでの検索シミュレーション
- [ ] 検索結果の表示
- [ ] 検索履歴の記録

### Phase 3: 外部API連携（2-3週間）
**目的**: 実際のデータソースとの連携

```
優先度: 🟡 中
理由: 実運用には必要だが、開発初期はモックで代替可能
```

#### タスク分解:
- [ ] API連携の抽象化層作成
- [ ] Bizreach API連携（または代替）
- [ ] OpenAI API連携（候補者分析）
- [ ] エラーハンドリング
- [ ] レート制限対応

### Phase 4: バックグラウンド処理（1-2週間）
**目的**: 非同期処理による UX向上

```
優先度: 🟡 中
理由: パフォーマンス向上に必要
```

#### タスク分解:
- [ ] Celeryセットアップ
- [ ] ジョブキューの実装
- [ ] 進捗状況の追跡
- [ ] ジョブのキャンセル機能

### Phase 5: 通知・レポート（1-2週間）
**目的**: 運用効率の向上

```
優先度: 🟢 低
理由: Nice to have機能
```

---

## 🚀 今すぐ始められるタスク

### 1. データベーススキーマ設計（2-3日）
```sql
-- requirements テーブル
CREATE TABLE requirements (
    id UUID PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    position_name VARCHAR(255) NOT NULL,
    description TEXT,
    required_skills TEXT[],
    preferred_skills TEXT[],
    experience_years_min INT,
    experience_years_max INT,
    salary_min INT,
    salary_max INT,
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'draft',
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- candidates テーブル
CREATE TABLE candidates (
    id UUID PRIMARY KEY,
    external_id VARCHAR(255),
    source VARCHAR(50),
    profile_data JSONB,
    skills TEXT[],
    experience_years INT,
    current_position VARCHAR(255),
    desired_salary_min INT,
    desired_salary_max INT,
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- search_jobs テーブル
CREATE TABLE search_jobs (
    id UUID PRIMARY KEY,
    requirement_id UUID REFERENCES requirements(id),
    search_criteria JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    results_count INT DEFAULT 0,
    error_message TEXT,
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- search_results テーブル
CREATE TABLE search_results (
    id UUID PRIMARY KEY,
    search_job_id UUID REFERENCES search_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    match_score DECIMAL(3,2),
    match_reasons JSONB,
    status VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. 最初の実装タスク（1日）

**requirements_service.py** を作成:
```python
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from supabase import Client
from ..utils.supabase_client import get_supabase_client

class RequirementsService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def create_requirement(self, data: dict) -> dict:
        """採用要件を作成"""
        result = self.supabase.table('requirements').insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_requirements(self, client_id: Optional[UUID] = None) -> List[dict]:
        """採用要件一覧を取得"""
        query = self.supabase.table('requirements').select('*')
        if client_id:
            query = query.eq('client_id', str(client_id))
        result = query.execute()
        return result.data
    
    async def get_requirement_by_id(self, requirement_id: UUID) -> Optional[dict]:
        """採用要件の詳細を取得"""
        result = self.supabase.table('requirements').select('*').eq('id', str(requirement_id)).execute()
        return result.data[0] if result.data else None
    
    async def update_requirement(self, requirement_id: UUID, data: dict) -> dict:
        """採用要件を更新"""
        result = self.supabase.table('requirements').update(data).eq('id', str(requirement_id)).execute()
        return result.data[0] if result.data else None
    
    async def delete_requirement(self, requirement_id: UUID) -> bool:
        """採用要件を削除"""
        result = self.supabase.table('requirements').delete().eq('id', str(requirement_id)).execute()
        return len(result.data) > 0
```

### 3. 既存のルーターを更新（1日）

main.pyのadmin_requirementsを更新:
```python
@app.get("/admin/requirements", response_class=HTMLResponse)
async def admin_requirements(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - 採用要件管理"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    # サービスクラスを使用してデータ取得
    service = RequirementsService()
    requirements = await service.get_requirements()
    
    return templates.TemplateResponse("admin/requirements.html", {
        "request": request, 
        "current_user": user, 
        "requirements": requirements
    })
```

---

## 💡 開発のコツ

### 1. 小さく始める
- まず1つのテーブル（requirements）から始める
- CRUD操作を完全に実装してから次へ
- 動作確認を頻繁に行う

### 2. モックデータの活用
- 外部APIは後回しにして、まずモックデータで動作確認
- フロントエンドの動作確認を優先

### 3. 段階的な統合
- 新機能は独立して開発
- 既存機能への影響を最小限に
- テストを書きながら進める

### 4. 定期的なレビュー
- 週次で進捗確認
- 優先順位の見直し
- ユーザーフィードバックの収集

---

## 📅 推奨スケジュール

**Week 1-2**: データベース基盤
- テーブル設計と作成
- 基本的なCRUD実装

**Week 3-4**: 採用要件管理
- 完全な要件管理機能
- UI/UXの改善

**Week 5-6**: 検索機能（モック）
- 検索フローの実装
- 結果表示の実装

**Week 7-8**: API連携
- 実データとの接続
- エラーハンドリング

**Week 9-10**: 仕上げ
- バグ修正
- パフォーマンス改善
- ドキュメント整備