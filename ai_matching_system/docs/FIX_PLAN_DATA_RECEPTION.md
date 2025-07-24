# データ受信問題の修正計画

## 現状の問題

1. **求人情報が38文字しか受信されていない**
   - 現状: `job_description_text`に求人タイトルのみが渡されている
   - 期待: 求人の全文（4,000文字以上）が渡されるべき

2. **候補者基本情報が提供されていない**
   - 現状: `match_candidate_direct`メソッドが候補者情報を受け取っていない
   - 期待: age, gender, company, enrolled_company_countが渡されるべき

3. **structured_job_dataが渡されていない**
   - 現状: 構造化された求人データが欠落
   - 期待: 給与、スキル要件などの構造化データが渡されるべき

## 修正手順

### Step 1: match_candidate_directメソッドの修正

```python
def match_candidate_direct(
    self,
    resume_text: str,
    job_description_text: str,
    job_memo_text: str,
    max_cycles: int = 3,
    candidate_id: Optional[str] = None,
    # 以下を追加
    candidate_age: Optional[int] = None,
    candidate_gender: Optional[str] = None,
    candidate_company: Optional[str] = None,
    enrolled_company_count: Optional[int] = None,
    structured_job_data: Optional[Dict] = None
) -> Dict:
```

### Step 2: runメソッドへのパラメータ受け渡し

```python
return asyncio.run(
    self.orchestrator.run(
        resume=resume_text,
        job_description=job_description_text,
        job_memo=job_memo_text,
        max_cycles=max_cycles,
        candidate_id=candidate_id,
        # 以下を追加
        candidate_age=candidate_age,
        candidate_gender=candidate_gender,
        candidate_company=candidate_company,
        enrolled_company_count=enrolled_company_count,
        structured_job_data=structured_job_data
    )
)
```

### Step 3: 呼び出し側の修正確認

AI matching systemを呼び出している箇所（おそらくSupabase Edge FunctionまたはバックエンドAPI）で以下を確認：

1. **job_descriptionの取得**
   - `job_requirements`テーブルから`job_description`カラムを正しく取得
   - タイトルではなく全文を渡す

2. **候補者情報の取得**
   - `candidates`テーブルから候補者基本情報を取得
   - 各パラメータを正しく渡す

3. **structured_dataの取得**
   - `job_requirements`テーブルから`structured_data`カラムを取得
   - JSONとしてパースして渡す

## 期待される呼び出し方

```python
result = await ai_matching_service.match_candidate_direct(
    resume_text=candidate_resume,
    job_description_text=requirement.job_description,  # 全文
    job_memo_text=requirement.memo,
    max_cycles=3,
    candidate_id=candidate.id,
    candidate_age=candidate.age,
    candidate_gender=candidate.gender,
    candidate_company=candidate.current_company,
    enrolled_company_count=candidate.enrolled_company_count,
    structured_job_data=requirement.structured_data
)
```

## デバッグ用ログの追加

修正後、以下のログを追加して正しくデータが渡されているか確認：

```python
print(f"[DEBUG] job_description_text length: {len(job_description_text)}")
print(f"[DEBUG] job_description_text preview: {job_description_text[:200]}...")
print(f"[DEBUG] candidate_age: {candidate_age}")
print(f"[DEBUG] structured_job_data keys: {list(structured_job_data.keys()) if structured_job_data else 'None'}")
```

## 検証方法

1. 修正後、同じ候補者で再度マッチングを実行
2. ログで以下を確認：
   - 求人情報が4,000文字以上あること
   - 候補者基本情報が表示されること
   - structured_job_dataが含まれること