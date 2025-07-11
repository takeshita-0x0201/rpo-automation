# Bizreachスクレイピング処理更新

## 実施日: 2025-07-10

## 更新内容

### 1. スクレイピング要素の変更

#### bizreach.js での実装

```javascript
// candidate_idの抽出
// class="lapPageHeader cf" 内の class="resumePageID fl" から取得
const pageHeader = element.querySelector('.lapPageHeader.cf');
const resumePageIdElement = pageHeader.querySelector('.resumePageID.fl');
candidateId = resumePageIdElement.textContent.trim();

// candidate_linkの抽出
// data-clipboard-text属性から取得
const clipboardElement = element.querySelector('[data-clipboard-text]');
candidateLink = clipboardElement.getAttribute('data-clipboard-text');

// candidate_companyの抽出
// class="mt15 ns-drawer-resume-contents" 内の jsi_company_header_name_0_0
const resumeContents = element.querySelector('.mt15.ns-drawer-resume-contents');
const companyElement = resumeContents.querySelector('[id*="jsi_company_header_name"]');
candidateCompany = companyElement.textContent.trim();

// candidate_resumeの抽出
// jsi_resume_ja_block class="resumeView" から取得
const resumeBlock = element.querySelector('[id*="jsi_resume_ja_block"].resumeView');
candidateResume = resumeBlock.textContent.trim();
```

### 2. プラットフォーム選択機能

#### popup.js での実装
- 選択したプラットフォームをローカルストレージに保存
- `chrome.storage.local.set({ selected_platform: platform })`

#### bizreach.js での実装
- `getSelectedPlatform()`メソッドを追加
- ストレージから選択されたプラットフォームを取得
- デフォルトは'bizreach'

### 3. requirement_id の処理
- 拡張機能で選択されたjob_requirementsのIDを使用
- `this.sessionInfo.requirementId`から取得

## 変更された関数

### extractCandidateData()
主な変更点：
1. 新しいセレクタを使用してデータを抽出
2. フォールバック処理を追加（要素が見つからない場合）
3. candidate_resumeは最大1000文字に制限
4. プラットフォーム情報を動的に取得

### 新規追加メソッド
1. `extractCandidateIdFromUrl()` - URLからIDを抽出（フォールバック用）
2. `getSelectedPlatform()` - 選択されたプラットフォームを取得

## データ構造

### 抽出されるデータ
```javascript
{
  candidate_id: "123456",           // resumePageID fl から取得
  candidate_link: "https://...",    // data-clipboard-text から取得
  candidate_company: "株式会社XX",   // jsi_company_header_name から取得
  candidate_resume: "レジュメ内容",  // jsi_resume_ja_block から取得
  platform: "bizreach",             // 拡張機能で選択
  client_id: "uuid",                // セッション情報から
  requirement_id: "uuid",           // 拡張機能で選択
  scraping_session_id: "uuid",      // セッション情報から
  scraped_at: "2025-07-10T..."     // スクレイピング時刻
}
```

## テスト手順

1. Chrome拡張機能を再読み込み
2. Bizreachにログイン
3. 候補者一覧ページを開く
4. 拡張機能のポップアップで：
   - プラットフォーム「BizReach」を選択
   - 採用要件を選択
   - 「開始」ボタンをクリック
5. 開発者ツールのコンソールで抽出データを確認

## デバッグ情報

コンソールに以下の情報が出力されます：
- `BizReachScraper: candidate_id found: XXX`
- `BizReachScraper: candidate_link found: XXX`
- `BizReachScraper: candidate_company found: XXX`
- `BizReachScraper: candidate_resume length: XXX`
- `BizReachScraper: 抽出データ:` （完全なデータオブジェクト）

## 注意事項

1. **必須フィールドのフォールバック**
   - candidate_idが見つからない場合は、URLから抽出またはタイムスタンプベースのIDを生成
   - candidate_linkが見つからない場合は、現在のページURLを使用
   - candidate_companyが見つからない場合は、'不明'を設定

2. **candidate_resumeの処理**
   - テキスト内容が1000文字を超える場合は切り詰め
   - レジュメが見つからない場合は、candidate_linkを代わりに使用

3. **プラットフォーム対応**
   - 現在は'bizreach'のみ対応
   - 将来的に'green'、'wantedly'等を追加予定