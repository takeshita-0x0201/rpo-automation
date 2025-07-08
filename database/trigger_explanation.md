# トリガー関数の説明

## 🤔 トリガー関数とは？

簡単に言うと「データが更新されたら自動的に実行される関数」です。

## 📝 具体例で理解する

### 例：採用要件を編集した場合

```sql
-- ユーザーが実行するSQL
UPDATE requirements 
SET position_name = 'シニアエンジニア' 
WHERE id = '123';
```

**トリガーなしの場合：**
- `updated_at`は古いまま（作成時の日時のまま）
- いつ更新されたか分からない

**トリガーありの場合：**
- 自動的に`updated_at`が現在時刻に更新される
- 更新履歴が正確に記録される

## 🎯 なぜ必要？

### 1. 更新日時の自動管理
```sql
-- これを毎回書かなくて済む
UPDATE requirements 
SET 
    position_name = 'シニアエンジニア',
    updated_at = NOW()  -- 手動で書く必要がない！
WHERE id = '123';
```

### 2. 開発者のミスを防ぐ
- 更新時にupdated_atを忘れても大丈夫
- アプリケーション側で管理する必要がない

### 3. データの整合性
- すべての更新で確実に記録される
- 監査やデバッグに役立つ

## 🔧 どう動く？

```sql
-- 1. トリガー関数の定義
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();  -- 新しいデータのupdated_atを現在時刻に
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 2. トリガーの設定
CREATE TRIGGER update_requirements_updated_at 
    BEFORE UPDATE ON requirements  -- requirementsテーブルの更新前に
    FOR EACH ROW                    -- 各行に対して
    EXECUTE FUNCTION update_updated_at_column();  -- この関数を実行
```

## 🚦 トリガーを使うべき？使わないべき？

### 使うべき場合 ✅
- updated_atのような共通処理
- データの整合性が重要
- アプリケーション側の負担を減らしたい

### 使わない方がいい場合 ❌
- 複雑なビジネスロジック
- 外部APIの呼び出し
- パフォーマンスが超重要な場合

## 💡 代替案

もしトリガーを使いたくない場合：

### Option 1: アプリケーション側で管理
```python
# Pythonの例
from datetime import datetime

async def update_requirement(requirement_id, data):
    data['updated_at'] = datetime.now()  # 手動で設定
    return await supabase.table('requirements').update(data).eq('id', requirement_id).execute()
```

### Option 2: Supabaseの機能を使う
Supabaseでは、テーブル作成時に以下のオプションで自動管理できます：
```sql
-- Supabaseの推奨方法
CREATE TABLE requirements (
    -- ... 他のカラム ...
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()  -- ただし、これだけでは自動更新されない
);

-- Supabaseのダッシュボードで「Enable Realtime」を有効にすると
-- 自動的にupdated_atを管理してくれる場合もある
```

## 🎨 結論

トリガーは便利ですが、必須ではありません。

**トリガーを使わない簡易版：**
```sql
-- トリガーなしバージョン
CREATE TABLE requirements (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    -- ... 他のカラム ...
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 更新時は手動でupdated_atを設定
UPDATE requirements 
SET 
    position_name = '新しいポジション',
    updated_at = NOW()
WHERE id = '123';
```

どちらのアプローチを選びますか？