# Requirements Document

## Introduction

この機能は、AIマッチングシステムで評価された候補者を選択し、スプレッドシートに出力する機能を提供します。ユーザーは候補者一覧画面から複数の候補者を選択し、「送客リストに追加」ボタンをクリックすることで、選択した候補者の情報を指定されたスプレッドシートに出力できます。また、出力履歴を管理するために、`ai_evaluations`テーブルに送客状態を記録します。

## Requirements

### Requirement 1

**User Story:** As a リクルーター, I want 選択した候補者の情報をスプレッドシートに出力できる, so that クライアントと共有しやすくなる

#### Acceptance Criteria

1. WHEN ユーザーが候補者一覧画面で複数の候補者を選択して「送客リストに追加」ボタンをクリックする THEN システムは選択された候補者の情報をスプレッドシートに出力する
2. WHEN スプレッドシート出力が成功する THEN システムは成功メッセージとスプレッドシートのURLを表示する
3. WHEN スプレッドシート出力が失敗する THEN システムはエラーメッセージを表示する
4. WHEN 候補者情報がスプレッドシートに出力される THEN 出力される情報には少なくとも候補者ID、会社名、プラットフォーム、年齢、性別、AIスコア、推奨度、マッチ理由、懸念事項、候補者リンクが含まれる

### Requirement 2

**User Story:** As a リクルーター, I want 送客済みの候補者を視覚的に識別できる, so that 重複して送客することを防げる

#### Acceptance Criteria

1. WHEN 候補者がスプレッドシートに出力される THEN システムは`ai_evaluations`テーブルの該当レコードに送客済みフラグと送客日時を記録する
2. WHEN ユーザーが候補者一覧画面を表示する THEN 送客済みの候補者には「送客済み」バッジが表示される
3. WHEN ユーザーが候補者一覧画面を表示する THEN 統計情報に送客済み候補者数が表示される

### Requirement 3

**User Story:** As a システム管理者, I want Google Apps Script (GAS) を使用して既存のスプレッドシートにデータを出力できる, so that 既存のワークフローを維持できる

#### Acceptance Criteria

1. WHEN システムがスプレッドシートに出力する THEN Google Apps Script (GAS) エンドポイントを使用して指定されたスプレッドシートに新しいシートを作成する
2. WHEN 新しいシートが作成される THEN シート名は日付、クライアント名、候補者数を含む形式になる
3. WHEN データがスプレッドシートに出力される THEN 基本情報（送客日時、クライアント名、求人タイトル、送客者、候補者数）も含まれる
4. WHEN スプレッドシートへの出力が完了する THEN GASはスプレッドシートのURLを返す

### Requirement 4

**User Story:** As a システム開発者, I want 環境変数で設定を管理できる, so that 環境ごとに設定を変更しやすくなる

#### Acceptance Criteria

1. WHEN システムがGASエンドポイントを呼び出す THEN 環境変数`GAS_WEBHOOK_URL`から取得したURLを使用する
2. WHEN GASスクリプトがスプレッドシートを開く THEN スクリプトプロパティから取得したスプレッドシートIDを使用する