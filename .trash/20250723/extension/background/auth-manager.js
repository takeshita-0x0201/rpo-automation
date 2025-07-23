// 認証管理モジュール

class AuthManager {
  constructor() {
    this.tokenKey = 'rpo_auth_token';
    this.expiryKey = 'rpo_token_expiry';
    this.userKey = 'rpo_user_info';
    this.refreshBuffer = 5 * 60 * 1000; // 5分前にリフレッシュ
  }

  // 認証状態を取得
  async getAuthState() {
    const token = await this.getValidToken();
    const user = await this.getUser();
    
    return {
      isAuthenticated: !!token,
      token,
      user
    };
  }

  // ログイン
  async login(email, password) {
    try {
      // API経由でログイン
      const response = await apiClient.login(email, password);
      
      if (response.access_token) {
        // トークンとユーザー情報を保存
        await this.saveAuthData(
          response.access_token,
          response.user,
          response.expires_in
        );
        
        return {
          success: true,
          user: response.user
        };
      }
      
      return {
        success: false,
        error: 'ログインに失敗しました'
      };
    } catch (error) {
      console.error('Login error:', error);
      
      if (error instanceof ApiError) {
        if (error.status === 401) {
          return {
            success: false,
            error: 'メールアドレスまたはパスワードが正しくありません'
          };
        }
        if (error.isNetworkError()) {
          return {
            success: false,
            error: 'ネットワークエラーが発生しました'
          };
        }
      }
      
      return {
        success: false,
        error: error.message || 'ログインに失敗しました'
      };
    }
  }

  // ログアウト
  async logout() {
    try {
      // ストレージから認証情報を削除
      await chrome.storage.local.remove([
        this.tokenKey,
        this.expiryKey,
        this.userKey,
        'rpo_selected_client',
        'rpo_current_session',
        'rpo_scraping_state'
      ]);
      
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return {
        success: false,
        error: 'ログアウトに失敗しました'
      };
    }
  }

  // 有効なトークンを取得
  async getValidToken() {
    const result = await chrome.storage.local.get([this.tokenKey, this.expiryKey]);
    
    if (!result[this.tokenKey] || !result[this.expiryKey]) {
      return null;
    }
    
    // 有効期限チェック
    const now = Date.now();
    const expiry = result[this.expiryKey];
    
    if (now > expiry) {
      // トークンが期限切れ
      await this.clearAuthData();
      return null;
    }
    
    // リフレッシュが必要かチェック
    if (now > expiry - this.refreshBuffer) {
      // リフレッシュを試みる
      const refreshed = await this.refreshToken();
      if (refreshed) {
        return refreshed;
      }
    }
    
    return result[this.tokenKey];
  }

  // トークンリフレッシュ
  async refreshToken() {
    try {
      // 現在のトークンを取得
      const currentToken = await this.getRawToken();
      if (!currentToken) {
        return null;
      }
      
      // リフレッシュAPIを呼び出し
      const response = await apiClient.post('/api/auth/refresh', {
        token: currentToken
      });
      
      if (response.access_token) {
        // 新しいトークンを保存
        await this.updateToken(response.access_token, response.expires_in);
        return response.access_token;
      }
      
      return null;
    } catch (error) {
      console.error('Token refresh failed:', error);
      
      // リフレッシュに失敗した場合は認証情報をクリア
      await this.clearAuthData();
      return null;
    }
  }

  // ユーザー情報を取得
  async getUser() {
    const result = await chrome.storage.local.get(this.userKey);
    return result[this.userKey] || null;
  }

  // 認証データを保存
  async saveAuthData(token, user, expiresIn = 86400) {  // デフォルト24時間
    const expiry = Date.now() + (expiresIn * 1000);
    
    await chrome.storage.local.set({
      [this.tokenKey]: token,
      [this.expiryKey]: expiry,
      [this.userKey]: user
    });
  }

  // トークンを更新
  async updateToken(token, expiresIn = 86400) {  // デフォルト24時間
    const expiry = Date.now() + (expiresIn * 1000);
    
    await chrome.storage.local.set({
      [this.tokenKey]: token,
      [this.expiryKey]: expiry
    });
  }

  // 認証データをクリア
  async clearAuthData() {
    await chrome.storage.local.remove([
      this.tokenKey,
      this.expiryKey,
      this.userKey
    ]);
  }

  // 生のトークンを取得（有効期限チェックなし）
  async getRawToken() {
    const result = await chrome.storage.local.get(this.tokenKey);
    return result[this.tokenKey] || null;
  }

  // 認証が必要かチェック
  async requiresAuth() {
    const token = await this.getValidToken();
    return !token;
  }

  // 認証エラーハンドリング
  async handleAuthError() {
    // 認証情報をクリア
    await this.clearAuthData();
    
    // ポップアップに通知
    try {
      await chrome.runtime.sendMessage({
        type: 'AUTH_ERROR',
        message: '認証の有効期限が切れました。再度ログインしてください。'
      });
    } catch (error) {
      // ポップアップが開いていない場合は無視
    }
    
    // 通知を表示
    chrome.notifications.create({
      type: 'basic',
      iconUrl: '/icons/icon-48.png',
      title: 'RPO Automation',
      message: '認証の有効期限が切れました。再度ログインしてください。'
    });
  }
}

// シングルトンインスタンス
const authManager = new AuthManager();

// エクスポート（Service Workerで使用）
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { authManager };
}