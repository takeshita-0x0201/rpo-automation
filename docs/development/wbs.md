# WBS（作業計画書） - Chrome拡張機能版

このドキュメントでは、Chrome拡張機能版の開発タスクを詳細に分解したWBS（Work Breakdown Structure）を提示します。**文系出身の新卒エンジニアがAIアシスタントと対話しながら、一人でタスクを理解し、実装まで進められる**ことを目標としています。

各タスクには、具体的な作業内容、AIへの質問例、完了の定義を記載しています。この通りに進めることで、プロジェクトの全体像を把握しながら、着実に開発を進めることができます。

## 進捗管理について

各タスクの状態は以下で管理します：
- **未着手**: まだ開始していない
- **着手中**: 作業を開始している
- **レビュー中**: 実装は完了し、確認待ち
- **完了**: 動作確認まで完了

---

## フェーズ1: 開発準備と全体像の理解 (目標: 1週間)

**目的:** プロジェクトを自分のPCで動かすための準備を整え、AIアシスタントに質問しながら、基本的な仕組みと技術要素を理解する。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 1.1 | **開発環境のセットアップ** | 完了 | **目的:** Pythonコードを実行できる環境を整える。<br> **作業内容:**<br> 1. [環境設定ガイド](../setup/environment.md)の「前提条件」を確認し、Python 3.9以上をインストールする。<br> 2. 「開発環境のセットアップ」セクションに従い、リポジトリをクローンし、仮想環境(`venv`)を作成・有効化する。<br> 3. `pip install -r requirements.txt` を実行し、ライブラリをインストールする。<br> **AIへの質問例:**<br> - 「`git clone`って何をするコマンド？基本的な使い方を教えて」<br> - 「Pythonの`venv`って何？なぜ必要なの？」<br> - 「`pip install -r requirements.txt`は、何をしているの？」<br> **完了の定義:** `pip install`がエラーなく完了し、`pip list`でライブラリが一覧表示されること。 |
| 1.2 | **GCP/Google Workspaceのセットアップ** | 完了 | **目的:** プロジェクトが連携するGoogleのサービスを使えるようにする。<br> **作業内容:**<br> 1. [環境設定ガイド](../setup/environment.md)の「GCPプロジェクトの設定」に従い、`gcloud init`を実行し、GCPプロジェクトと連携させる。<br> 2. 「必要なGCP APIの有効化」セクションで、BigQuery API、Google Sheets APIなどを有効化する。<br> 3. 「サービスアカウントの作成」でサービスアカウントを作成し、キー（JSONファイル）をダウンロードする。<br> **AIへの質問例:**<br> - 「GCPのサービスアカウントって何？人とどう違うの？」<br> - 「GCPのIAMロールって何？『BigQueryデータ編集者』にはどんな権限があるの？」<br> **完了の定義:** `gcloud config list`で自分のプロジェクトが表示されること。サービスアカウントのJSONキーがダウンロードされていること。 |
| 1.3 | **環境変数の設定** | 完了 | **目的:** APIキーなどの秘密情報をコードから分離し、安全に管理する方法を学ぶ。<br> **作業内容:**<br> 1. `.env.example`をコピーして`.env`ファイルを作成する。<br> 2. [環境設定ガイド](../setup/environment.md)の「環境変数の設定」を参考に、ダウンロードしたGCPのキー情報や、別途用意したOpenAI/GeminiのAPIキーなどを`.env`ファイルに書き込む。<br> **AIへの質問例:**<br> - 「`.env`ファイルって何？なぜこれを使うとセキュリティが向上するの？」<br> - 「`python-dotenv`ライブラリの使い方を教えて。サンプルコードが欲しい」<br> **完了の定義:** `src/utils/env_loader.py`がエラーなく実行でき、環境変数が読み込めること。 |
| 1.4 | **プロジェクト構成の理解** | 完了 | **目的:** どこに何のコードがあるか把握し、変更するべきファイルを見つけられるようになる。<br> **作業内容:**<br> 1. メインREADMEの「プロジェクト構成」を読み、各ディレクトリの役割を理解する。<br> 2. `src`内の各ディレクトリ（`extension`, `ai`, `web`等）を開き、ファイル名を眺めて、何をするためのコードか推測する。<br> 3. Chrome拡張機能の構造（manifest.json、content script、background script）を理解する。<br> **AIへの質問例:**<br> - 「Chrome拡張機能のmanifest.jsonって何？どんな役割があるの？」<br> - 「content scriptとbackground scriptの違いを教えて」<br> - 「Chrome拡張機能でAPIを叩くにはどうすればいい？」<br> **完了の定義:** 「Bizreachのスクレイピングロジックはどこ？」と聞かれて`src/extension/content/scraper.js`と答えられるなど、主要な機能とファイルの対応関係を説明できること。 |
| 1.5 | **Supabase/BigQueryのセットアップ** | 完了 | **目的:** WebAppのメインDBと、大規模データ用のDBを準備する。<br> **作業内容:**<br> 1. [Supabaseセットアップガイド](../setup/supabase.md)に従い、プロジェクト作成、テーブル作成、接続テストを行う。<br> 2. [BigQueryセットアップガイド](../setup/bigquery.md)に従い、データセット作成、テーブル作成、接続テストを行う。<br> **AIへの質問例:**<br> - 「SupabaseとBigQueryはどう使い分けるの？それぞれの得意なことは？」<br> - 「SQLの`INSERT INTO`文の基本的な書き方を教えて」<br> - 「SupabaseのRLS（行レベルセキュリティ）って、どういう仕組み？」<br> **完了の定義:** 各セットアップガイドのPython接続テストコードがエラーなく実行でき、データが取得できること。 |
| 1.6 | **RPOビジネスモデルの理解** | 未着手 | **目的:** このシステムが「誰の」「どんな課題を」解決するのかを理解する。<br> **作業内容:**<br> 1. RPO（採用代行）の基本的な業務フロー（クライアントから求人をもらう→候補者を探す→推薦する→結果を報告する）をネットで調べる。<br> 2. このシステムのユーザー（RPO事業者）が、どんな手作業に困っているか想像する。<br> 3. [システムアーキテクチャ](../architecture.md)のアーキテクチャ図を見て、どの部分が手作業を自動化しているか考える。<br> **AIへの質問例:**<br> - 「RPO事業のビジネスモデルについて、分かりやすく解説して」<br> - 「このシステムのアーキテクチャ図で、一番重要なコンポーネントはどれだと思う？その理由は？」<br> **完了の定義:** このシステムが解決する課題と、その解決方法の概要を自分の言葉で説明できること。 |
| 1.7 | **Chrome拡張機能の基礎理解** | 未着手 | **目的:** Chrome拡張機能の仕組みと開発方法を理解する。<br> **作業内容:**<br> 1. Chrome拡張機能の公式ドキュメントを読む。<br> 2. 簡単な「Hello World」拡張機能を作ってみる。<br> 3. `src/extension/`ディレクトリの構造を理解する。<br> **AIへの質問例:**<br> - 「Chrome拡張機能のmanifest v3って何？v2との違いは？」<br> - 「Chrome拡張機能でWebページの内容を取得する方法を教えて」<br> - 「Chrome拡張機能からAPIを叩く時のCORS対策は？」<br> **完了の定義:** 自作の簡単な拡張機能をChromeにインストールして動かせること。 |

---

## フェーズ2: WebApp開発 (目標: 2週間)

**目的:** ユーザーが実際に操作する画面（フロントエンド）と、それに応答するAPI（バックエンド）の基礎を、FastAPIとSupabaseを使って構築する。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 2.1 | **FastAPIで"Hello World"** | 完了 | **目的:** Webアプリケーションの最も基本的な仕組みを動かしてみる。<br> **作業内容:**<br> 1. `src/web/main.py`を作成する。<br> 2. FastAPIをインポートし、`app = FastAPI()`でインスタンスを作成する。<br> 3. `@app.get("/")`でルートエンドポイントを作成し、`{"message": "Hello World"}`を返す簡単な関数を定義する。<br> 4. `uvicorn src.web.main:app --reload`コマンドでサーバーを起動する。<br> **AIへの質問例:**<br> - 「FastAPIで最もシンプルなAPIを作る方法を教えて」<br> - 「`uvicorn`って何？`--reload`オプションにはどんな意味があるの？」<br> **完了の定義:** ブラウザで `http://localhost:8000` にアクセスし、`{"message": "Hello World"}` が表示されること。 |
| 2.2 | **クライアント企業の一覧表示** | 着手中 | **目的:** Supabaseデータベースからデータを取得し、Webページに表示する。<br> **作業内容:**<br> 1. **API実装:** `src/web/routers/clients.py`に、Supabaseから`clients`テーブルの全件を検索するAPIエンドポイント(`/api/clients`)を作成する。<br> 2. **HTMLテンプレート作成:** `src/web/templates/clients.html`を作成し、APIから受け取ったクライアント情報をテーブル形式で表示するHTMLを記述する。<br> 3. **ルーティング設定:** `src/web/main.py`で、`/clients`というパスへのアクセス時に`clients.html`を返すように設定する。<br> **AIへの質問例:**<br> - 「FastAPIでSupabaseに接続して、テーブルから全件取得するPythonコードを教えて」<br> - 「FastAPIでHTMLテンプレート(Jinja2)を返す基本的な方法を教えて」<br> - 「HTMLでテーブル（表）を作るにはどうすればいい？」<br> **完了の定義:** `http://localhost:8000/clients`にアクセスすると、Supabaseに登録したテスト用のクライアント企業一覧が表示されること。 |
| 2.3 | **クライアント企業の新規登録** | 未着手 | **目的:** Webフォームからの入力を受け取り、データベースに新しいデータを保存する。<br> **作業内容:**<br> 1. **入力フォーム作成:** `clients.html`に、企業名や担当者名を入力するHTMLフォーム(`<form>`)を追加する。<br> 2. **Pydanticモデル作成:** `src/web/models/client.py`に、フォームの入力に対応するPydanticモデルを作成し、データ型を定義する。<br> 3. **登録API実装:** `clients.py`に、フォームからのPOSTリクエストを受け取り、Pydanticモデルで検証し、Supabaseの`clients`テーブルにデータを`INSERT`するAPIエンドポイントを作成する。<br> **AIへの質問例:**<br> - 「HTMLの`<form>`タグの基本的な使い方を教えて。`action`と`method`って何？」<br> - 「FastAPIで、フォームからのデータを受け取るにはどうすればいい？Pydanticモデルの使い方も教えて」<br> - 「SupabaseのPythonクライアントで、新しい行をINSERTするコードを教えて」<br> **完了の定義:** Webページのフォームから新しいクライアント情報を入力・送信すると、ページがリロードされ、一覧に新しい企業が追加されていること。 |
| 2.4 | **採用要件管理機能の実装** | 未着手 | **目的:** プロジェクトのコア機能である採用要件のCRUD（作成・読み取り・更新・削除）を実装する。<br> **作業内容:**<br> 1. `2.2`, `2.3`を参考に、`採用要件`の「一覧表示機能」と「新規登録機能」を実装する。（`requirements.py`, `requirements.html`など）<br> 2. **編集機能:** 一覧の各行に「編集」ボタンを追加し、クリックすると既存データが入力されたフォームが表示されるページを作成。更新APIを実装する。<br> 3. **削除機能:** 一覧の各行に「削除」ボタンを追加し、クリックすると確認ダイアログを表示後、削除APIを呼び出すように実装する。<br> **AIへの質問例:**<br> - 「REST APIのCRUDってどういう意味？HTTPメソッド（GET, POST, PUT, DELETE）とどう対応するの？」<br> - 「JavaScriptで、ボタンクリック時に確認ダイアログ（`confirm`）を表示する方法は？」<br> **完了の定義:** WebApp上で採用要件の登録、一覧確認、編集、削除が一通り行えること。 |
| 2.5 | **拡張機能用認証APIの実装** | 未着手 | **目的:** Chrome拡張機能がFastAPIと安全に通信するための認証機能を実装する。<br> **作業内容:**<br> 1. `src/web/routers/auth_extension.py`を作成する。<br> 2. 拡張機能用のログインエンドポイント（`/api/auth/extension/login`）を実装する。<br> 3. JWTトークンの発行と検証機能を実装する。<br> 4. CORS設定でChrome拡張機能のOriginを許可する。<br> **AIへの質問例:**<br> - 「FastAPIでJWT認証を実装する方法を教えて」<br> - 「Chrome拡張機能のOriginって何？どう設定すればいい？」<br> - 「FastAPIでCORSを設定する方法は？」<br> **完了の定義:** Chrome拡張機能からログインAPIを呼び出し、JWTトークンが取得できること。 |
| 2.6 | **候補者データ受信APIの実装** | 未着手 | **目的:** Chrome拡張機能から送信される候補者データを受信・保存するAPIを実装する。<br> **作業内容:**<br> 1. `src/web/routers/candidates.py`を作成する。<br> 2. バッチデータ受信エンドポイント（`/api/candidates/batch`）を実装する。<br> 3. 受信したデータの検証とBigQueryへの保存処理を実装する。<br> 4. ジョブの進捗更新機能を実装する。<br> **AIへの質問例:**<br> - 「FastAPIで大量のデータを効率的に受信する方法は？」<br> - 「PythonでBigQueryにデータを一括挿入する方法を教えて」<br> - 「バッチ処理のベストプラクティスは？」<br> **完了の定義:** POSTMANなどで候補者データを送信し、BigQueryに保存されることを確認できること。 |

---

## フェーズ3: Chrome拡張機能の実装 (目標: 2週間)

**目的:** Bizreachから候補者情報を自動収集するChrome拡張機能を実装する。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 3.1 | **拡張機能の基本構造作成** | 未着手 | **目的:** Chrome拡張機能の骨組みを作成する。<br> **作業内容:**<br> 1. `src/extension/manifest.json`を作成し、必要な権限を設定する。<br> 2. `popup.html`と`popup.js`で基本的なUIを作成する。<br> 3. `background/service-worker.js`を作成し、バックグラウンド処理の準備をする。<br> **AIへの質問例:**<br> - 「Chrome拡張機能のmanifest.jsonの基本的な書き方を教えて」<br> - 「拡張機能で必要な権限（permissions）の種類と用途は？」<br> - 「service workerって何？background scriptとの違いは？」<br> **完了の定義:** 拡張機能をChromeにインストールし、ポップアップが表示されること。 |
| 3.2 | **FastAPI認証の実装** | 未着手 | **目的:** 拡張機能からFastAPIにログインし、認証トークンを取得する機能を実装する。<br> **作業内容:**<br> 1. `background/api-client.js`を作成する。<br> 2. ログイン関数を実装し、JWTトークンを取得する。<br> 3. Chrome Storage APIを使ってトークンを安全に保存する。<br> 4. トークンの自動リフレッシュ機能を実装する。<br> **AIへの質問例:**<br> - 「Chrome拡張機能からfetchでAPIを叩く方法を教えて」<br> - 「Chrome Storage APIの使い方は？localStorageとの違いは？」<br> - 「JWTトークンの有効期限をチェックする方法は？」<br> **完了の定義:** 拡張機能からログインボタンを押すと、トークンが取得・保存されること。 |
| 3.3 | **Bizreachスクレイピング実装** | 未着手 | **目的:** Bizreachの候補者一覧から情報を抽出する機能を実装する。<br> **作業内容:**<br> 1. `content/scraper.js`を作成する。<br> 2. 候補者一覧の要素を特定し、情報を抽出する関数を実装する。<br> 3. ページネーションに対応した自動遷移機能を実装する。<br> 4. 抽出したデータを構造化する処理を実装する。<br> **AIへの質問例:**<br> - 「JavaScriptでDOM要素から情報を抽出する方法を教えて」<br> - 「動的に読み込まれるコンテンツを待つ方法は？」<br> - 「Chrome拡張機能でページ遷移を検知する方法は？」<br> **完了の定義:** Bizreachの候補者一覧ページで、候補者情報がコンソールに出力されること。 |
| 3.4 | **進捗表示UIの実装** | 未着手 | **目的:** スクレイピング中の進捗をユーザーに表示する機能を実装する。<br> **作業内容:**<br> 1. `content/ui-overlay.js`を作成する。<br> 2. ページ上に進捗バーを表示するオーバーレイを実装する。<br> 3. 収集済み候補者数やエラー情報を表示する。<br> 4. 一時停止・再開ボタンを実装する。<br> **AIへの質問例:**<br> - 「JavaScriptで他のサイトのページ上にUIを重ねて表示する方法は？」<br> - 「CSSでposition: fixedを使った進捗バーの作り方を教えて」<br> - 「Shadow DOMを使ってスタイルの競合を防ぐ方法は？」<br> **完了の定義:** Bizreachページ上に進捗バーが表示され、カウントが更新されること。 |
| 3.5 | **データ送信機能の実装** | 未着手 | **目的:** 収集した候補者データをFastAPIに送信する機能を実装する。<br> **作業内容:**<br> 1. `background/api-client.js`にデータ送信関数を追加する。<br> 2. バッチサイズ（例：10件）ごとにデータを送信する処理を実装する。<br> 3. 送信失敗時のリトライ機能を実装する。<br> 4. 送信完了の通知機能を実装する。<br> **AIへの質問例:**<br> - 「JavaScriptで配列を指定サイズごとに分割する方法は？」<br> - 「fetchでのエラーハンドリングとリトライの実装方法を教えて」<br> - 「Chrome拡張機能で通知（notification）を表示する方法は？」<br> **完了の定義:** 収集したデータがバッチでFastAPIに送信され、BigQueryに保存されること。 |
| 3.6 | **エラーハンドリングの実装** | 未着手 | **目的:** スクレイピング中の各種エラーに対応する処理を実装する。<br> **作業内容:**<br> 1. ネットワークエラー、認証エラー、DOM変更などの対処を実装する。<br> 2. エラーログをローカルに保存する機能を実装する。<br> 3. ユーザーへのエラー通知機能を実装する。<br> 4. エラー発生時の自動リカバリー機能を実装する。<br> **AIへの質問例:**<br> - 「JavaScriptでtry-catchを使ったエラーハンドリングの方法は？」<br> - 'Chrome拡張機能でログを永続化する方法は？」<br> - 「ユーザーフレンドリーなエラーメッセージの書き方は？」<br> **完了の定義:** 各種エラーが発生してもアプリケーションがクラッシュせず、適切に処理されること。 |

---

## フェーズ4: AI判定とシステム統合 (目標: 1週間)

**目的:** 収集した候補者データのAI判定機能を実装し、システム全体を統合する。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 4.1 | **AI判定処理の実装** | 未着手 | **目的:** 採用要件と候補者情報を基に、AI（ChatGPT-4o）がマッチング度を判定する機能を実装する。<br> **作業内容:**<br> 1. `src/ai/matching_engine.py`に、OpenAIのAPIクライアントを初期化するコードを書く。<br> 2. **プロンプト作成:** 採用要件と候補者情報をテキストとして結合し、「この候補者は、この採用要件にどのくらいマッチしますか？スコアと理由をJSON形式で回答してください」という指示文（プロンプト）を作成する。<br> 3. 作成したプロンプトをOpenAI APIに送信し、結果を受け取る。<br> 4. AIからの返答（JSON文字列）をパースし、スコアや理由をBigQueryに保存する。<br> **AIへの質問例:**<br> - 「PythonでOpenAIのAPIを呼び出す基本的なコードを教えて」<br> - 「AIの性能を引き出すためのプロンプトのコツ（プロンプトエンジニアリング）を教えて」<br> - 「PythonでJSON文字列を辞書オブジェクトに変換するにはどうすればいい？」<br> **完了の定義:** 採用要件IDと候補者IDを渡すと、AIによる評価スコアと理由がBigQueryに保存されること。 |
| 4.2 | **バッチAI判定の実装** | 未着手 | **目的:** 大量の候補者を効率的にAI判定する仕組みを実装する。<br> **作業内容:**<br> 1. Cloud Functionsでバッチ処理用の関数を作成する。<br> 2. ジョブ完了時に自動でAI判定を開始する仕組みを実装する。<br> 3. 判定結果をGoogle Sheetsに出力する処理を実装する。<br> 4. 完了通知をWebAppに送信する。<br> **AIへの質問例:**<br> - 「Cloud Functionsで長時間実行されるタスクの実装方法は？」<br> - 「PythonでGoogle Sheets APIを使ってデータを書き込む方法を教えて」<br> - 「非同期処理のベストプラクティスは？」<br> **完了の定義:** ジョブ完了後、自動的にAI判定が実行され、結果がGoogle Sheetsに出力されること。 |
| 4.3 | **システム統合テスト** | 未着手 | **目的:** 全体のワークフローが正しく動作することを確認する。<br> **作業内容:**<br> 1. WebAppで採用要件を登録する。<br> 2. ジョブを作成し、Chrome拡張機能で候補者を収集する。<br> 3. AI判定が自動実行されることを確認する。<br> 4. Google Sheetsに結果が出力されることを確認する。<br> **AIへの質問例:**<br> - 「統合テストのチェックリストの作り方を教えて」<br> - 「エンドツーエンドテストの重要性は？」<br> - 「バグを見つけたときの対処法は？」<br> **完了の定義:** 採用要件登録から結果出力まで、一連の流れがエラーなく完了すること。 |

---

## フェーズ5: 仕上げとデプロイ (目標: 1週間)

**目的:** システムを安定稼働させ、本番環境で使えるようにする。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 5.1 | **エラーハンドリングの強化** | 未着手 | **目的:** 予期せぬエラーが発生しても、システム全体が停止しないように、堅牢性を高める。<br> **作業内容:**<br> 1. Pythonの`try...except`構文を学ぶ。<br> 2. 特に外部と通信する部分（スクレイピング、API呼び出し）に`try...except`を追加し、エラーが発生しても処理が継続するようにする。<br> 3. エラーが発生した場合は、その内容を`logging`ライブラリを使ってBigQueryのログテーブルに記録する。<br> **AIへの質問例:**<br> - 「Pythonの`try...except`の基本的な使い方を教えて。`Exception as e`って何？」<br> - 「Pythonの`logging`ライブラリの基本的な設定方法と、ファイルにログを出力する方法を教えて」<br> **完了の定義:** 意図的にエラー（例: 間違ったAPIキー）を発生させてもプログラムが異常終了せず、エラーログが記録されること。 |
| 5.2 | **単体テストの作成** | 未着手 | **目的:** 機能の変更によって、既存の機能が意図せず壊れていないかを確認する仕組みを作る。<br> **作業内容:**<br> 1. `pytest`の基本的な使い方を学ぶ。<br> 2. `tests/unit/`ディレクトリに、引数を渡すと決まった値を返すような単純な関数（例: `utils`内の関数）のテストコードを書く。<br> 3. ダミーの入力データを用意し、関数の返り値が期待通りの値になるかを`assert`で検証する。<br> **AIへの質問例:**<br> - 「`pytest`の基本的な使い方を教えて。テストファイルの命名規則や、簡単なテスト関数の書き方は？」<br> - 「`assert`文って何？テストでどう使うの？」<br> **完了の定義:** `pytest tests/unit/` を実行すると、作成したテストがすべて成功（PASS）すること。 |
| 5.3 | **WebAppのデプロイ** | 未着手 | **目的:** 開発したWebAppを、インターネット上の誰からでもアクセスできる本番環境（Cloud Run）で動かす。<br> **作業内容:**<br> 1. **Dockerfile作成:** WebAppをコンテナ化するための`Dockerfile`を作成する。<br> 2. **コンテナイメージのビルド:** `gcloud builds submit`コマンドを使い、ソースコードをCloud Buildに送信してコンテナイメージを作成する。<br> 3. **Cloud Runへのデプロイ:** `gcloud run deploy`コマンドを使い、ビルドしたイメージをCloud Runにデプロイする。<br> 4. **CORS設定の更新:** Chrome拡張機能のIDを取得し、本番環境のCORS設定に追加する。<br> **AIへの質問例:**<br> - 「FastAPIアプリケーションをデプロイするための、基本的な`Dockerfile`を書いて」<br> - 「`gcloud builds submit`と`gcloud run deploy`コマンドの基本的な使い方を教えて」<br> - 「Chrome拡張機能のIDの取得方法は？」<br> **完了の定義:** デプロイ後に発行されるCloud RunのURLにアクセスすると、ローカル環境と同じようにWebAppが表示されること。 |
| 5.4 | **Chrome拡張機能の公開準備** | 未着手 | **目的:** 拡張機能を組織内で配布できるように準備する。<br> **作業内容:**<br> 1. 拡張機能のアイコンを作成する。<br> 2. manifest.jsonの情報を本番用に更新する。<br> 3. 拡張機能をパッケージ化（.crxファイル）する。<br> 4. 配布用のドキュメントを作成する。<br> **AIへの質問例:**<br> - 「Chrome拡張機能のアイコンのサイズと形式は？」<br> - 「拡張機能をパッケージ化する方法を教えて」<br> - 「組織内でChrome拡張機能を配布する方法は？」<br> **完了の定義:** .crxファイルが作成され、他のPCでインストールできること。 |

## 完了チェックリスト

各フェーズ完了時に以下を確認してください：

### フェーズ1完了チェック
- [ ] Python仮想環境が正常に動作する
- [ ] GCPプロジェクトに接続できる
- [ ] Supabase・BigQueryのテストが成功する
- [ ] プロジェクト構成を理解している
- [ ] Chrome拡張機能の基本を理解している

### フェーズ2完了チェック
- [ ] FastAPIでHello Worldが表示される
- [ ] クライアント一覧が表示される
- [ ] 新規クライアント登録ができる
- [ ] 採用要件のCRUDが動作する
- [ ] 認証APIが動作する
- [ ] 候補者データ受信APIが動作する

### フェーズ3完了チェック
- [ ] 拡張機能がChromeにインストールできる
- [ ] FastAPI認証が成功する
- [ ] Bizreachスクレイピングが動作する
- [ ] 進捗UIが表示される
- [ ] データ送信が成功する
- [ ] エラーハンドリングが動作する

### フェーズ4完了チェック
- [ ] AI判定が実行される
- [ ] バッチ処理が動作する
- [ ] エンドツーエンドテストが成功する

### フェーズ5完了チェック
- [ ] エラーログが記録される
- [ ] 単体テストが成功する
- [ ] WebAppがCloud Runで動作する
- [ ] 拡張機能がパッケージ化される

## サポートとヘルプ

開発中に困ったときは：

1. **AIアシスタントに質問**: 各タスクの「AIへの質問例」を参考に
2. **ドキュメント参照**: [トラブルシューティング](../operations/troubleshooting.md)
3. **ログ確認**: BigQueryのシステムログテーブル
4. **GitHubイシュー**: 技術的な問題や改善提案