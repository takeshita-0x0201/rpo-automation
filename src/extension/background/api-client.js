// API通信クライアント

class ApiClient {
  constructor() {
    this.baseUrl = this.getApiBaseUrl();
    this.timeout = 30000; // 30秒
  }

  // APIベースURL取得
  getApiBaseUrl() {
    // 環境に応じて切り替え
    const isDev = !chrome.runtime.id.includes('prod');
    return isDev ? 'http://localhost:8000' : 'https://rpo-automation.run.app';
  }

  // リクエスト共通処理
  async request(endpoint, options = {}) {
    console.log('API Request:', endpoint, options);
    // トークン取得
    const token = await this.getAuthToken();
    console.log('API Token available:', !!token);
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    };

    const mergedOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers
      }
    };

    // タイムアウト処理
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...mergedOptions,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      // レスポンスの処理
      const contentType = response.headers.get('content-type');
      let data;
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        console.error('API Error Response:', response.status, data);
        throw new ApiError(
          response.status,
          data.detail || data.message || 'API request failed',
          data.error_code
        );
      }

      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        throw new ApiError(0, 'Request timeout', 'TIMEOUT');
      }
      
      if (error instanceof ApiError) {
        throw error;
      }
      
      throw new ApiError(0, error.message || 'Network error', 'NETWORK_ERROR');
    }
  }

  // 認証トークン取得
  async getAuthToken() {
    const result = await chrome.storage.local.get(['rpo_auth_token', 'rpo_token_expiry']);
    
    if (!result.rpo_auth_token || !result.rpo_token_expiry) {
      return null;
    }
    
    // 有効期限チェック（5分前にリフレッシュ）
    const bufferTime = 5 * 60 * 1000; // 5分
    if (Date.now() > result.rpo_token_expiry - bufferTime) {
      // トークンリフレッシュが必要
      return await this.refreshToken();
    }
    
    return result.rpo_auth_token;
  }

  // トークンリフレッシュ
  async refreshToken() {
    try {
      // リフレッシュトークンの実装は後で追加
      // 現在は再ログインが必要
      return null;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return null;
    }
  }

  // GET リクエスト
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    
    return this.request(url, { method: 'GET' });
  }

  // POST リクエスト
  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // PUT リクエスト
  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  // DELETE リクエスト
  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  // 認証API
  async login(email, password) {
    const response = await this.post('/api/auth/extension/login', {
      email,
      password
    });
    
    // トークンを保存
    if (response.access_token) {
      const expiresIn = response.expires_in || 3600; // デフォルト1時間
      await chrome.storage.local.set({
        rpo_auth_token: response.access_token,
        rpo_token_expiry: Date.now() + (expiresIn * 1000),
        rpo_user_info: response.user
      });
    }
    
    return response;
  }

  // クライアント一覧取得
  async getClients() {
    return this.get('/api/extension/clients');
  }
  
  // 採用要件取得（クライアント指定）
  async getRequirements(clientId) {
    return this.get('/api/extension/requirements', { client_id: clientId });
  }
  
  // 全ての採用要件を取得
  async getAllRequirements() {
    console.log('ApiClient: Getting all requirements');
    try {
      const result = await this.get('/api/extension/requirements/all');
      console.log('ApiClient: Requirements received:', result);
      return result;
    } catch (error) {
      console.error('ApiClient: Failed to get requirements:', error);
      throw error;
    }
  }
  
  // 採用要件詳細取得
  async getRequirement(requirementId) {
    return this.get(`/api/extension/requirements/${requirementId}`);
  }

  // スクレイピングセッション開始
  async startScrapingSession(clientId, requirementId) {
    return this.post('/api/extension/scraping/start', {
      client_id: clientId,
      requirement_id: requirementId
    });
  }

  // スクレイピングセッション完了
  async completeScrapingSession(sessionId) {
    return this.post('/api/extension/scraping/end', {
      session_id: sessionId
    });
  }

  // 候補者データバッチ送信
  async sendCandidateBatch(candidates, sessionId) {
    return this.post('/api/extension/candidates/batch', {
      candidates,
      session_id: sessionId
    });
  }

  // 採用要件取得（クライアント指定）
  async getRequirements(clientId, activeOnly = true) {
    return this.get('/api/extension/requirements', {
      client_id: clientId,
      active_only: activeOnly
    });
  }

  // 全ての採用要件を取得
  async getAllRequirements(activeOnly = true) {
    console.log('API Client: Getting all requirements, activeOnly:', activeOnly);
    console.log('API Client: Base URL:', this.baseUrl);
    try {
      const result = await this.get('/api/extension/requirements/all', {
        active_only: activeOnly
      });
      console.log('API Client: Requirements fetched successfully');
      return result;
    } catch (error) {
      console.error('API Client: Error fetching requirements:', error);
      throw error;
    }
  }

  // 採用要件詳細取得
  async getRequirement(requirementId) {
    return this.get(`/api/extension/requirements/${requirementId}`);
  }

  // エラーレポート送信
  async reportError(error, context = {}) {
    try {
      await this.post('/api/errors/report', {
        error: {
          message: error.message,
          stack: error.stack,
          code: error.code
        },
        context: {
          ...context,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString()
        }
      });
    } catch (e) {
      console.error('Failed to report error:', e);
    }
  }
}

// カスタムエラークラス
class ApiError extends Error {
  constructor(status, message, code = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }

  isAuthError() {
    return this.status === 401 || this.code === 'AUTH_FAILED';
  }

  isNetworkError() {
    return this.status === 0 || this.code === 'NETWORK_ERROR';
  }

  isServerError() {
    return this.status >= 500;
  }
}

// シングルトンインスタンス
const apiClient = new ApiClient();

// Service Worker環境では、グローバルスコープに直接定義される
// Chrome拡張のService Workerで使用できるようにグローバルに公開
if (typeof self !== 'undefined') {
  self.apiClient = apiClient;
  self.ApiError = ApiError;
}

// エクスポート（Node.js環境で使用）
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { apiClient, ApiError };
}