// ストレージ操作のユーティリティ
const StorageUtil = {
  // データを保存
  async set(key, value) {
    try {
      await chrome.storage.local.set({ [key]: value });
      return true;
    } catch (error) {
      console.error('Storage set error:', error);
      return false;
    }
  },

  // データを取得
  async get(key) {
    try {
      const result = await chrome.storage.local.get(key);
      return result[key];
    } catch (error) {
      console.error('Storage get error:', error);
      return null;
    }
  },

  // 複数のデータを取得
  async getMultiple(keys) {
    try {
      const result = await chrome.storage.local.get(keys);
      return result;
    } catch (error) {
      console.error('Storage get multiple error:', error);
      return {};
    }
  },

  // データを削除
  async remove(key) {
    try {
      await chrome.storage.local.remove(key);
      return true;
    } catch (error) {
      console.error('Storage remove error:', error);
      return false;
    }
  },

  // すべてのデータをクリア
  async clear() {
    try {
      await chrome.storage.local.clear();
      return true;
    } catch (error) {
      console.error('Storage clear error:', error);
      return false;
    }
  }
};

// 認証トークン管理
const TokenUtil = {
  // トークンを保存
  async saveToken(token, expiresIn = 86400) {  // デフォルト24時間
    const expiry = Date.now() + (expiresIn * 1000);
    await StorageUtil.set(STORAGE_KEYS.AUTH_TOKEN, token);
    await StorageUtil.set(STORAGE_KEYS.TOKEN_EXPIRY, expiry);
  },

  // トークンを取得
  async getToken() {
    const token = await StorageUtil.get(STORAGE_KEYS.AUTH_TOKEN);
    const expiry = await StorageUtil.get(STORAGE_KEYS.TOKEN_EXPIRY);
    
    if (!token || !expiry) {
      return null;
    }

    // 有効期限チェック
    if (Date.now() > expiry) {
      await this.clearToken();
      return null;
    }

    return token;
  },

  // トークンをクリア
  async clearToken() {
    await StorageUtil.remove(STORAGE_KEYS.AUTH_TOKEN);
    await StorageUtil.remove(STORAGE_KEYS.TOKEN_EXPIRY);
  },

  // トークンの有効性チェック
  async isValid() {
    const token = await this.getToken();
    return token !== null;
  }
};

// API通信のユーティリティ
const ApiUtil = {
  // APIリクエストの共通処理
  async request(endpoint, options = {}) {
    const token = await TokenUtil.getToken();
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      timeout: API_TIMEOUT
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
    const timeoutId = setTimeout(() => controller.abort(), mergedOptions.timeout);

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...mergedOptions,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.json();
        throw new ApiError(response.status, error.detail || 'API request failed');
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        throw new ApiError(0, 'Request timeout');
      }
      
      throw error;
    }
  },

  // GET リクエスト
  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  // POST リクエスト
  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  // PUT リクエスト
  async put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  // DELETE リクエスト
  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
};

// カスタムエラークラス
class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// DOM操作のユーティリティ
const DomUtil = {
  // 要素が存在するまで待機
  async waitForElement(selector, timeout = SCRAPING_CONFIG.ELEMENT_WAIT_TIME) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const element = document.querySelector(selector);
      if (element) {
        return element;
      }
      await this.sleep(100);
    }
    
    throw new Error(`Element not found: ${selector}`);
  },

  // 複数の要素が存在するまで待機
  async waitForElements(selector, minCount = 1, timeout = SCRAPING_CONFIG.ELEMENT_WAIT_TIME) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const elements = document.querySelectorAll(selector);
      if (elements.length >= minCount) {
        return elements;
      }
      await this.sleep(100);
    }
    
    throw new Error(`Elements not found: ${selector}`);
  },

  // スリープ
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  // テキストを安全に取得
  getTextContent(element, selector = null) {
    try {
      const target = selector ? element.querySelector(selector) : element;
      return target ? target.textContent.trim() : '';
    } catch (error) {
      return '';
    }
  },

  // 属性を安全に取得
  getAttribute(element, attribute, selector = null) {
    try {
      const target = selector ? element.querySelector(selector) : element;
      return target ? target.getAttribute(attribute) : '';
    } catch (error) {
      return '';
    }
  }
};

// データ整形のユーティリティ
const DataUtil = {
  // 配列をチャンクに分割
  chunk(array, size) {
    const chunks = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  },

  // オブジェクトの深いコピー
  deepCopy(obj) {
    return JSON.parse(JSON.stringify(obj));
  },

  // 空白文字の正規化
  normalizeWhitespace(str) {
    return str.replace(/\s+/g, ' ').trim();
  },

  // メールアドレスの検証
  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  // URLの検証
  isValidUrl(url) {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }
};

// デバッグユーティリティ
const DebugUtil = {
  // デバッグログ（開発環境のみ）
  log(...args) {
    if (CURRENT_ENV === 'DEV') {
      console.log('[RPO Extension]', ...args);
    }
  },

  // エラーログ
  error(...args) {
    console.error('[RPO Extension Error]', ...args);
  },

  // 警告ログ
  warn(...args) {
    console.warn('[RPO Extension Warning]', ...args);
  },

  // 情報ログ
  info(...args) {
    console.info('[RPO Extension Info]', ...args);
  }
};