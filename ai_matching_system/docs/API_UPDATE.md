# AIマッチングシステム API更新ガイド（v2）

## 概要
AIマッチングシステムの呼び出し方法を更新し、求人情報と候補者情報を正しく渡すようにする必要があります。

## 問題点
現在、システムに渡されているデータ：
- `job_description`: タイトルのみ（38文字）❌
- `job_memo`: memoフィールド（144文字）✓
- 候補者基本情報: 未提供 ❌
- 構造化求人データ: 未提供 ❌

## 正しい呼び出し方法

### 1. job_requirementsテーブルから取得すべきデータ

```sql
SELECT 
    title,
    job_description,     -- 求人票全文（4,000文字以上）
    memo,               -- 求人メモ
    structured_data     -- 構造化データ（JSON）
FROM job_requirements 
WHERE id = ?;
```

### 2. candidatesテーブルから取得すべきデータ

```sql
SELECT 
    id,
    age,
    gender,
    current_company,
    enrolled_company_count
FROM candidates 
WHERE id = ?;
```

### 3. AIマッチングシステムへの呼び出し（match_candidate_direct使用）

```python
from ai_matching.nodes.orchestrator import SeparatedDeepResearchMatcher

# マッチャーを初期化
matcher = SeparatedDeepResearchMatcher(
    gemini_api_key=GEMINI_API_KEY,
    tavily_api_key=TAVILY_API_KEY,
    pinecone_api_key=PINECONE_API_KEY
)

# 直接テキストを渡してマッチング実行
result = matcher.match_candidate_direct(
    resume_text=candidate_resume_text,
    job_description_text=requirement.job_description,  # 全文を渡す（4,000文字以上）
    job_memo_text=requirement.memo,
    max_cycles=3,
    # 候補者情報を追加
    candidate_id=candidate.id,
    candidate_age=candidate.age,
    candidate_gender=candidate.gender,
    candidate_company=candidate.current_company,
    enrolled_company_count=candidate.enrolled_company_count,
    # 構造化データを追加
    structured_job_data=requirement.structured_data  # JSONオブジェクト
)
```

### 4. 通常のオーケストレーター使用の場合

```python
from ai_matching.nodes.orchestrator import DeepResearchOrchestrator

# オーケストレーターを初期化
orchestrator = DeepResearchOrchestrator(
    gemini_api_key=GEMINI_API_KEY,
    tavily_api_key=TAVILY_API_KEY  # オプション
)

# 正しい呼び出し方法
result = await orchestrator.run(
    # レジュメ
    resume=candidate.candidate_resume,
    
    # 求人票全文（job_descriptionフィールドから）
    job_description=requirement.job_description,  # ⚠️ titleではない！
    
    # 求人メモ
    job_memo=requirement.memo,
    
    # 候補者基本情報（candidatesテーブルから）
    candidate_id=candidate.candidate_id,
    candidate_age=int(candidate.age) if candidate.age else None,
    candidate_gender=candidate.gender,
    candidate_company=candidate.candidate_company,
    enrolled_company_count=int(candidate.enrolled_company_count) if candidate.enrolled_company_count else None,
    
    # 構造化データ（NEW!）
    structured_job_data=requirement.structured_data,  # JSONBフィールド
    
    # その他のパラメータ
    max_cycles=3
)
```

## デバッグ方法

### 1. 求人情報が正しく渡されているか確認

```python
# API呼び出し前にデータを確認
print(f"job_description length: {len(requirement.job_description)}")
print(f"job_description preview: {requirement.job_description[:200]}...")
print(f"structured_data keys: {list(requirement.structured_data.keys())}")
```

### 2. ログ出力の確認

正常な場合：
```
データ受信...
  レジュメ: 10607文字
  求人情報: 4394文字  ✓ 正常
  求人補足情報: 144文字
  構造化データ: ['position', 'salary_min', 'salary_max', ...]

【候補者情報】
年齢: 32歳
性別: 男性
現在の所属: 株式会社テクノロジー
在籍企業数: 2社
```

異常な場合：
```
データ受信...
  レジュメ: 10607文字
  求人情報: 38文字  ❌ 問題あり
  [警告] 求人情報が短すぎます: 'シニアバックエンドエンジニア'  ❌ タイトルのみ
  求人補足情報: 144文字
  構造化データなし  ❌

【候補者情報】
候補者基本情報が提供されていません  ❌
```

## 注意事項

1. **job_descriptionは全文を渡す**: タイトルだけでは不十分
2. **候補者情報は必須**: 評価精度に大きく影響
3. **structured_dataは重要**: 給与やスキル要件などの構造化情報を含む

### 3. structured_dataの形式

```json
{
    "title": "新規リード開発/マネージャー候補",
    "position": "新規リード開発マネージャー候補",
    "salary_max": 12000000,
    "salary_min": 7000000,
    "work_location": "東京都港区東新橋1-5-2",
    "employment_type": "正社員",
    "required_skills": [
        "2階層以上（10名以上）の組織マネジメント経験",
        "営業組織における全体責任者またはそれに準ずるマネジメント経験"
    ],
    "preferred_skills": [
        "インターネットサービス、人材業界での新規顧客獲得経験",
        "飲食、物流、小売への法人営業経験"
    ],
    "experience_years_min": 5
}
```

## Edge FunctionやWebアプリの更新例

### Supabase Edge Function

```typescript
// job_requirementsから正しいデータを取得
const { data: requirement } = await supabaseClient
  .from('job_requirements')
  .select('*')
  .eq('id', requirementId)
  .single();

// candidatesから候補者情報を取得
const { data: candidate } = await supabaseClient
  .from('candidates')
  .select('*')
  .eq('id', candidateId)
  .single();

// AIマッチングシステムを呼び出し
const matchingResult = await callAIMatching({
  resume: candidate.candidate_resume,
  job_description: requirement.job_description,  // 全文を渡す
  job_memo: requirement.memo,
  candidate_id: candidate.candidate_id,
  candidate_age: candidate.age ? parseInt(candidate.age) : null,
  candidate_gender: candidate.gender,
  candidate_company: candidate.candidate_company,
  enrolled_company_count: candidate.enrolled_company_count ? parseInt(candidate.enrolled_company_count) : null,
  structured_job_data: requirement.structured_data  // 構造化データを追加
});
```

## 重要な変更点まとめ

1. ✅ `job_description`には`job_requirements.job_description`（全文）を渡す
2. ✅ `job_memo`には`job_requirements.memo`を渡す
3. ✅ `structured_job_data`に`job_requirements.structured_data`を渡す（新規追加）
4. ✅ 候補者情報は最初から渡す（Supabaseで再取得しない）
5. ❌ タイトルだけを渡さない
6. ❌ 候補者IDをレジュメに埋め込まない