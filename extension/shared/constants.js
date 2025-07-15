// API設定
const API_CONFIG = {
  // 開発環境
  DEV: {
    BASE_URL: 'http://localhost:8000',
    TIMEOUT: 30000
  },
  // 本番環境
  PROD: {
    BASE_URL: 'https://rpo-automation.run.app',
    TIMEOUT: 30000
  }
};

// 現在の環境（開発時はDEV、本番はPRODに変更）
const CURRENT_ENV = 'DEV';
const API_BASE_URL = API_CONFIG[CURRENT_ENV].BASE_URL;
const API_TIMEOUT = API_CONFIG[CURRENT_ENV].TIMEOUT;

// APIエンドポイント
const API_ENDPOINTS = {
  // 認証
  LOGIN: '/api/auth/extension/login',
  REFRESH: '/api/auth/refresh',
  
  // クライアント
  CLIENTS: '/api/clients',
  
  // 候補者
  CANDIDATES_BATCH: '/api/candidates/batch',
  
  // スクレイピングセッション
  SESSION_START: '/api/scraping/session/start',
  SESSION_COMPLETE: '/api/scraping/session/{session_id}/complete'
};

// スクレイピング設定
const SCRAPING_CONFIG = {
  // バッチサイズ（一度に送信する候補者数）
  BATCH_SIZE: 10,
  
  // ページ間の待機時間（ミリ秒）
  PAGE_DELAY: 2000,
  
  // 要素の読み込み待機時間（ミリ秒）
  ELEMENT_WAIT_TIME: 5000,
  
  // リトライ設定
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000,
  
  // 進捗更新間隔（ミリ秒）
  PROGRESS_UPDATE_INTERVAL: 1000
};

// ストレージキー
const STORAGE_KEYS = {
  // 認証トークン
  AUTH_TOKEN: 'rpo_auth_token',
  TOKEN_EXPIRY: 'rpo_token_expiry',
  
  // ユーザー情報
  USER_INFO: 'rpo_user_info',
  
  // 現在のセッション
  CURRENT_SESSION: 'rpo_current_session',
  
  // 選択中のクライアント
  SELECTED_CLIENT: 'rpo_selected_client',
  
  // スクレイピング状態
  SCRAPING_STATE: 'rpo_scraping_state'
};

// メッセージタイプ（background/content script間の通信）
const MESSAGE_TYPES = {
  // 認証関連
  LOGIN: 'LOGIN',
  LOGOUT: 'LOGOUT',
  GET_AUTH_STATUS: 'GET_AUTH_STATUS',
  
  // データ取得
  GET_CLIENTS: 'GET_CLIENTS',
  GET_REQUIREMENTS: 'GET_REQUIREMENTS',
  GET_ALL_REQUIREMENTS: 'GET_ALL_REQUIREMENTS',
  GET_REQUIREMENT: 'GET_REQUIREMENT',
  
  // スクレイピング制御
  START_SCRAPING: 'START_SCRAPING',
  PAUSE_SCRAPING: 'PAUSE_SCRAPING',
  RESUME_SCRAPING: 'RESUME_SCRAPING',
  STOP_SCRAPING: 'STOP_SCRAPING',
  
  // データ送信
  SEND_CANDIDATES: 'SEND_CANDIDATES',
  
  // 進捗更新
  UPDATE_PROGRESS: 'UPDATE_PROGRESS',
  
  // エラー通知
  SCRAPING_ERROR: 'SCRAPING_ERROR'
};

// スクレイピング状態
const SCRAPING_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  ERROR: 'error'
};

// エラーコード
const ERROR_CODES = {
  AUTH_FAILED: 'AUTH_FAILED',
  NETWORK_ERROR: 'NETWORK_ERROR',
  SCRAPING_ERROR: 'SCRAPING_ERROR',
  API_ERROR: 'API_ERROR',
  STORAGE_ERROR: 'STORAGE_ERROR',
  INVALID_SESSION: 'INVALID_SESSION'
};

// デバッグ設定
const DEBUG_CONFIG = {
  ENABLED: true,
  LOG_LEVEL: 'debug' // 'error', 'warn', 'info', 'debug'
};

// Bizreachのセレクタ（実際のDOM構造に合わせて調整が必要）
const BIZREACH_SELECTORS = {
  // 候補者一覧
  CANDIDATE_LIST: '.candidate-list',
  CANDIDATE_ITEM: '.candidate-item',
  
  // 候補者情報
  CANDIDATE_NAME: '.candidate-name',
  CANDIDATE_COMPANY: '.company-name',
  CANDIDATE_POSITION: '.position',
  CANDIDATE_EXPERIENCE: '.experience',
  CANDIDATE_SKILLS: '.skill-tag',
  CANDIDATE_EDUCATION: '.education',
  
  // ページネーション
  NEXT_PAGE_BUTTON: '.pagination-next',
  PAGE_INFO: '.page-info',
  
  // その他
  LOADING_INDICATOR: '.loading',
  NO_RESULTS: '.no-results'
};