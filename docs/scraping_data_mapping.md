# スクレイピングデータのマッピング仕様

## candidatesテーブルのカラムマッピング

### 1. candidate_id
- **説明**: プラットフォーム上の一意の候補者識別子
- **Bizreachの場合**: 
  - URLから抽出: `https://cr-support.jp/resume/pdf?candidate=1079961` → `1079961`
  - またはプロフィールページのIDを使用
- **形式**: TEXT（プラットフォームによって形式が異なるため）

### 2. candidate_link
- **説明**: 候補者のプロフィールページへの完全なURL
- **Bizreachの場合**: 
  - 例: `https://cr-support.jp/resume/pdf?candidate=1079961`
  - または: `https://www.bizreach.jp/members/profiles/12345`
- **形式**: TEXT（完全なURL）

### 3. candidate_company
- **説明**: 候補者の現在の所属企業名
- **スクレイピング元**: 
  - Bizreach: `.company-name`セレクタ
  - プロフィールページの「現在の勤務先」セクション
- **形式**: TEXT（企業名のみ、部署情報は含まない）

### 4. candidate_resume
- **説明**: レジュメ情報の保存方法は2つのオプション
- **オプション1**: レジュメPDFのURL
  - 例: `https://cr-support.jp/resume/pdf?candidate=1079961`
- **オプション2**: スクレイピングしたテキスト情報
  - プロフィールページから取得した要約テキスト
- **形式**: TEXT

## Chrome拡張機能での実装例

```javascript
// content/scrapers/bizreach.js での実装例

function extractCandidateData(element) {
  // candidate_id の抽出
  const profileLink = element.querySelector('a[href*="candidate="]');
  const candidateId = profileLink ? 
    profileLink.href.match(/candidate=(\d+)/)?.[1] : 
    null;
  
  // candidate_link の取得
  const candidateLink = profileLink ? profileLink.href : null;
  
  // candidate_company の取得
  const companyElement = element.querySelector('.company-name');
  const candidateCompany = companyElement ? 
    companyElement.textContent.trim() : 
    null;
  
  // candidate_resume の取得（URLの場合）
  const resumeLink = element.querySelector('a[href*="/resume/pdf"]');
  const candidateResume = resumeLink ? resumeLink.href : null;
  
  return {
    candidate_id: candidateId,
    candidate_link: candidateLink,
    candidate_company: candidateCompany,
    candidate_resume: candidateResume
  };
}
```

## APIへの送信形式

```javascript
// 拡張機能からAPIへ送信するデータ形式
{
  "candidates": [
    {
      "candidate_id": "1079961",
      "candidate_link": "https://cr-support.jp/resume/pdf?candidate=1079961",
      "candidate_company": "株式会社サンプル",
      "candidate_resume": "https://cr-support.jp/resume/pdf?candidate=1079961"
    }
  ],
  "session_id": "uuid-here",
  "client_id": "uuid-here",
  "requirement_id": "uuid-here"
}
```

## エンドポイントでの処理

```python
# /api/extension/candidates/batch での処理
@router.post("/candidates/batch")
async def save_candidates_batch(request: BatchCandidateRequest):
    candidates_data = []
    
    for candidate in request.candidates:
        candidate_data = {
            'candidate_id': candidate.candidate_id,
            'candidate_link': candidate.candidate_link,
            'candidate_company': candidate.candidate_company,
            'candidate_resume': candidate.candidate_resume,
            'scraping_session_id': request.session_id,
            'client_id': request.client_id,
            'requirement_id': request.requirement_id,
            'scraped_by': current_user["id"],
            'platform': 'bizreach'
        }
        candidates_data.append(candidate_data)
    
    # Supabaseに保存
    supabase.table('candidates').insert(candidates_data).execute()
```

## 注意事項

1. **candidate_id**は必須フィールドで、プラットフォーム内での重複チェックに使用
2. **candidate_link**も必須で、後で詳細情報を取得する際に使用
3. **candidate_company**は可能な限り取得（nullも許可）
4. **candidate_resume**はURLまたはテキスト情報を格納

## 将来の拡張

必要に応じて`candidate_details`テーブルに以下の情報を追加：
- 候補者名
- 連絡先情報
- 職歴詳細
- スキルセット
- 学歴
- その他の詳細情報