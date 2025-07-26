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

// User-Agentのリスト（実際のブラウザから収集）
const USER_AGENTS = {
  chrome: [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  ],
  edge: [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
  ],
  firefox: [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
  ],
  safari: [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15'
  ]
};

// スクレイピングユーティリティ
const ScrapingUtil = {
  // 現在のUser-Agent
  currentUserAgent: null,
  
  // ランダムなUser-Agentを取得
  getRandomUserAgent() {
    // ブラウザタイプをランダムに選択（Chromeの確率を高くする）
    const browserWeights = {
      chrome: 0.6,  // 60%
      edge: 0.2,    // 20%
      firefox: 0.15, // 15%
      safari: 0.05   // 5%
    };
    
    let random = Math.random();
    let selectedBrowser = 'chrome';
    
    for (const [browser, weight] of Object.entries(browserWeights)) {
      random -= weight;
      if (random <= 0) {
        selectedBrowser = browser;
        break;
      }
    }
    
    // 選択したブラウザからランダムにUser-Agentを選択
    const agents = USER_AGENTS[selectedBrowser];
    return agents[Math.floor(Math.random() * agents.length)];
  },
  
  // セッション用のUser-Agentを設定
  setSessionUserAgent() {
    this.currentUserAgent = this.getRandomUserAgent();
    console.log('Session User-Agent set:', this.currentUserAgent);
    return this.currentUserAgent;
  },
  
  // 現在のUser-Agentを取得（セッション中は同じものを使用）
  getCurrentUserAgent() {
    if (!this.currentUserAgent) {
      this.setSessionUserAgent();
    }
    return this.currentUserAgent;
  },
  // ガウス分布（正規分布）に基づくランダム値生成
  gaussianRandom(mean, stdDev) {
    let u = 0, v = 0;
    while(u === 0) u = Math.random();
    while(v === 0) v = Math.random();
    
    const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
    return mean + stdDev * z;
  },

  // 人間らしい待機時間を生成（ミリ秒）
  getHumanLikeDelay(baseDelay, variation = 0.3) {
    // 基本遅延時間を中心に、変動幅（デフォルト30%）でガウス分布
    const stdDev = baseDelay * variation;
    const delay = this.gaussianRandom(baseDelay, stdDev);
    
    // 最小値は基本遅延の50%、最大値は200%に制限
    const minDelay = baseDelay * 0.5;
    const maxDelay = baseDelay * 2.0;
    
    return Math.max(minDelay, Math.min(maxDelay, delay));
  },

  // テキストの読み取り時間を計算（ミリ秒）
  getReadingTime(textLength, readingSpeed = 250) {
    // 読み取り速度: 200-300 単語/分（ランダム）
    const actualSpeed = this.gaussianRandom(readingSpeed, 50);
    const words = textLength / 5; // 日本語の場合は調整が必要
    const baseTime = (words / actualSpeed) * 60 * 1000;
    
    // 読み取り時間も20%の変動を持たせる
    return this.getHumanLikeDelay(baseTime, 0.2);
  },

  // 人間らしい待機
  async humanLikeWait(minDelay, maxDelay) {
    const baseDelay = (minDelay + maxDelay) / 2;
    const variation = (maxDelay - minDelay) / (2 * baseDelay);
    const actualDelay = this.getHumanLikeDelay(baseDelay, variation);
    
    await DomUtil.sleep(Math.round(actualDelay));
  },

  // クリック前の短い遅延（反応時間のシミュレーション）
  async preClickDelay() {
    // 人間の反応時間: 100-300ms
    const reactionTime = this.getHumanLikeDelay(200, 0.25);
    await DomUtil.sleep(Math.round(reactionTime));
  },

  // ベジェ曲線を使った自然なマウス軌跡を生成
  generateMousePath(startX, startY, endX, endY, steps = 20) {
    const path = [];
    
    // 制御点をランダムに生成（より自然な曲線のため）
    const midX = (startX + endX) / 2;
    const midY = (startY + endY) / 2;
    
    // 制御点に変動を加える
    const controlX1 = midX + (Math.random() - 0.5) * Math.abs(endX - startX) * 0.5;
    const controlY1 = midY + (Math.random() - 0.5) * Math.abs(endY - startY) * 0.5;
    const controlX2 = midX + (Math.random() - 0.5) * Math.abs(endX - startX) * 0.5;
    const controlY2 = midY + (Math.random() - 0.5) * Math.abs(endY - startY) * 0.5;
    
    // ベジェ曲線に沿って点を生成
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const t2 = t * t;
      const t3 = t2 * t;
      const mt = 1 - t;
      const mt2 = mt * mt;
      const mt3 = mt2 * mt;
      
      // 3次ベジェ曲線の式
      const x = mt3 * startX + 3 * mt2 * t * controlX1 + 3 * mt * t2 * controlX2 + t3 * endX;
      const y = mt3 * startY + 3 * mt2 * t * controlY1 + 3 * mt * t2 * controlY2 + t3 * endY;
      
      // 微小な揺れを追加（手の震えをシミュレート）
      const jitterX = (Math.random() - 0.5) * 2;
      const jitterY = (Math.random() - 0.5) * 2;
      
      path.push({
        x: Math.round(x + jitterX),
        y: Math.round(y + jitterY),
        // 速度も変動させる（加速・減速）
        speed: this.getMouseSpeed(i, steps)
      });
    }
    
    return path;
  },

  // マウス速度の計算（始点と終点で遅く、中間で速い）
  getMouseSpeed(currentStep, totalSteps) {
    const progress = currentStep / totalSteps;
    // イージング関数（ease-in-out）
    const easing = progress < 0.5 
      ? 2 * progress * progress 
      : 1 - Math.pow(-2 * progress + 2, 2) / 2;
    
    // 基本速度にイージングを適用（5-20ms/step）
    const minSpeed = 5;
    const maxSpeed = 20;
    return minSpeed + (maxSpeed - minSpeed) * (1 - Math.abs(easing - 0.5) * 2);
  },

  // マウス移動をシミュレート
  async simulateMouseMovement(targetElement) {
    try {
      // 現在のマウス位置を推定（画面中央から開始）
      const startX = window.innerWidth / 2 + (Math.random() - 0.5) * 100;
      const startY = window.innerHeight / 2 + (Math.random() - 0.5) * 100;
      
      // ターゲット要素の位置を取得
      const rect = targetElement.getBoundingClientRect();
      const endX = rect.left + rect.width / 2 + (Math.random() - 0.5) * rect.width * 0.3;
      const endY = rect.top + rect.height / 2 + (Math.random() - 0.5) * rect.height * 0.3;
      
      // マウスパスを生成
      const path = this.generateMousePath(startX, startY, endX, endY);
      
      // パスに沿ってマウスを移動（実際のイベントは発火しないが、タイミングをシミュレート）
      for (const point of path) {
        // mousemoveイベントをディスパッチ（検出回避のため）
        const mouseMoveEvent = new MouseEvent('mousemove', {
          clientX: point.x,
          clientY: point.y,
          bubbles: true,
          cancelable: true,
          view: window
        });
        document.dispatchEvent(mouseMoveEvent);
        
        // 次の点まで待機
        await DomUtil.sleep(point.speed);
      }
      
      // ターゲット要素にホバー
      const mouseOverEvent = new MouseEvent('mouseover', {
        clientX: endX,
        clientY: endY,
        bubbles: true,
        cancelable: true,
        view: window
      });
      targetElement.dispatchEvent(mouseOverEvent);
      
      // ホバー状態を少し維持
      await DomUtil.sleep(this.getHumanLikeDelay(100, 0.3));
      
    } catch (error) {
      console.warn('Mouse simulation error:', error);
      // エラーが発生しても処理を継続
    }
  },

  // 人間らしいクリック
  async humanLikeClick(element) {
    // マウスが要素に到達するまでの時間
    await this.simulateMouseMovement(element);
    
    // クリック前の反応時間
    await this.preClickDelay();
    
    // マウスダウンイベント
    const rect = element.getBoundingClientRect();
    const x = rect.left + rect.width / 2 + (Math.random() - 0.5) * rect.width * 0.3;
    const y = rect.top + rect.height / 2 + (Math.random() - 0.5) * rect.height * 0.3;
    
    const mouseDownEvent = new MouseEvent('mousedown', {
      clientX: x,
      clientY: y,
      bubbles: true,
      cancelable: true,
      view: window,
      button: 0
    });
    element.dispatchEvent(mouseDownEvent);
    
    // クリック保持時間（50-150ms）
    await DomUtil.sleep(this.getHumanLikeDelay(100, 0.5));
    
    // マウスアップイベント
    const mouseUpEvent = new MouseEvent('mouseup', {
      clientX: x + (Math.random() - 0.5) * 2, // 微小な移動
      clientY: y + (Math.random() - 0.5) * 2,
      bubbles: true,
      cancelable: true,
      view: window,
      button: 0
    });
    element.dispatchEvent(mouseUpEvent);
    
    // クリック実行
    element.click();
    
    // クリック後の短い待機（50-150ms）
    await DomUtil.sleep(this.getHumanLikeDelay(100, 0.5));
  },

  // CAPTCHA検知
  detectCaptcha() {
    // CAPTCHAに関連するキーワード
    const captchaKeywords = [
      'captcha',
      'recaptcha',
      'hcaptcha',
      '認証',
      'ロボット',
      'robot',
      'verification',
      '確認',
      'セキュリティチェック',
      'security check'
    ];
    
    // ページ内のテキストを小文字で取得
    const bodyText = document.body.innerText.toLowerCase();
    
    // キーワードの存在チェック
    const keywordFound = captchaKeywords.some(keyword => 
      bodyText.includes(keyword.toLowerCase())
    );
    
    // CAPTCHAに関連する要素の存在チェック
    const captchaElements = [
      'iframe[src*="recaptcha"]',
      'iframe[src*="hcaptcha"]',
      'div[class*="captcha"]',
      '#recaptcha',
      '.g-recaptcha',
      '.h-captcha'
    ];
    
    const elementFound = captchaElements.some(selector => 
      document.querySelector(selector) !== null
    );
    
    return keywordFound || elementFound;
  },

  // レート制限エラーの検知
  detectRateLimit() {
    const rateLimitKeywords = [
      'too many requests',
      'rate limit',
      'アクセス制限',
      'アクセスが集中',
      '一時的に制限',
      '429',
      'throttle',
      'temporarily blocked',
      '一時的にブロック'
    ];
    
    const bodyText = document.body.innerText.toLowerCase();
    
    // HTTPステータスコードのチェック（meta refresh等）
    const metaRefresh = document.querySelector('meta[http-equiv="refresh"]');
    if (metaRefresh && metaRefresh.content.includes('429')) {
      return true;
    }
    
    return rateLimitKeywords.some(keyword => 
      bodyText.includes(keyword.toLowerCase())
    );
  },

  // アクセス拒否の検知
  detectAccessDenied() {
    const deniedKeywords = [
      'access denied',
      'forbidden',
      'アクセス拒否',
      'アクセスできません',
      '403',
      'blocked',
      'ブロック',
      '許可されていません'
    ];
    
    const bodyText = document.body.innerText.toLowerCase();
    
    return deniedKeywords.some(keyword => 
      bodyText.includes(keyword.toLowerCase())
    );
  },

  // 自然なスクロール動作
  async naturalScroll(targetElement = null, options = {}) {
    const defaults = {
      duration: 300,      // スクロールにかける時間（ミリ秒）
      variability: 0.3,   // 変動幅（30%）
      smoothness: 'smooth', // スクロールの滑らかさ
      pauseChance: 0.2,   // 途中で一時停止する確率
      readingPause: true  // スクロール後に読み取り時間を設ける
    };
    
    const config = { ...defaults, ...options };
    
    // スクロール量を決定
    let scrollAmount;
    if (targetElement) {
      // 要素までスクロール
      const rect = targetElement.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      // 要素が画面の中央付近に来るように調整
      scrollAmount = rect.top - viewportHeight / 2 + rect.height / 2;
    } else {
      // ランダムなスクロール（ページの20-40%）
      const pageHeight = document.documentElement.scrollHeight - window.innerHeight;
      const baseScroll = pageHeight * (0.2 + Math.random() * 0.2);
      scrollAmount = this.getHumanLikeDelay(baseScroll, config.variability);
    }
    
    // 途中で一時停止するかどうか
    if (Math.random() < config.pauseChance && Math.abs(scrollAmount) > 200) {
      // 2段階でスクロール
      const firstScroll = scrollAmount * (0.5 + Math.random() * 0.3);
      const secondScroll = scrollAmount - firstScroll;
      
      // 最初のスクロール
      window.scrollBy({
        top: firstScroll,
        behavior: config.smoothness
      });
      
      // 一時停止（読んでいるふり）
      const pauseDuration = this.getHumanLikeDelay(800, 0.4);
      await DomUtil.sleep(Math.round(pauseDuration));
      
      // 残りをスクロール
      window.scrollBy({
        top: secondScroll,
        behavior: config.smoothness
      });
    } else {
      // 一気にスクロール
      window.scrollBy({
        top: scrollAmount,
        behavior: config.smoothness
      });
    }
    
    // スクロール完了を待つ
    const scrollDuration = this.getHumanLikeDelay(config.duration, config.variability);
    await DomUtil.sleep(Math.round(scrollDuration));
    
    // 読み取り時間
    if (config.readingPause) {
      // スクロール後に表示されているテキスト量を推定
      const visibleTextLength = this.estimateVisibleTextLength();
      const readingTime = this.getReadingTime(visibleTextLength);
      await DomUtil.sleep(Math.round(readingTime * 0.3)); // 部分的に読む
    }
  },

  // 画面内の推定テキスト量
  estimateVisibleTextLength() {
    const viewportHeight = window.innerHeight;
    const elements = document.elementsFromPoint(window.innerWidth / 2, viewportHeight / 2);
    
    let textLength = 0;
    elements.forEach(element => {
      if (element.innerText) {
        textLength += element.innerText.length;
      }
    });
    
    return Math.min(textLength, 500); // 最大500文字と仮定
  },

  // ページ全体を段階的にスクロール
  async scrollThroughPage(options = {}) {
    const defaults = {
      segments: 3,        // ページを何分割するか
      readEachSegment: true, // 各セグメントで読み取り時間を設ける
      randomOrder: false  // ランダムな順序でスクロールするか
    };
    
    const config = { ...defaults, ...options };
    const pageHeight = document.documentElement.scrollHeight;
    const segmentHeight = pageHeight / config.segments;
    
    // スクロール位置を決定
    let positions = [];
    for (let i = 1; i <= config.segments; i++) {
      positions.push(segmentHeight * i);
    }
    
    // ランダム順序の場合はシャッフル
    if (config.randomOrder) {
      positions.sort(() => Math.random() - 0.5);
    }
    
    // 各位置へスクロール
    for (const position of positions) {
      await this.naturalScroll(null, {
        readingPause: config.readEachSegment
      });
      
      // セグメント間の待機
      await DomUtil.sleep(this.getHumanLikeDelay(1000, 0.5));
    }
  },

  // 指数バックオフ（レート制限対策）
  async exponentialBackoff(attemptNumber, options = {}) {
    const defaults = {
      baseDelay: 30000,     // 基本待機時間（30秒）
      maxDelay: 600000,     // 最大待機時間（10分）
      factor: 2,            // 倍数
      jitter: true,         // ジッター（ランダム性）を加えるか
      onWait: null          // 待機中のコールバック
    };
    
    const config = { ...defaults, ...options };
    
    // 指数的に増加する待機時間を計算
    let delay = Math.min(
      config.baseDelay * Math.pow(config.factor, attemptNumber - 1),
      config.maxDelay
    );
    
    // ジッターを追加（競合を避ける）
    if (config.jitter) {
      delay = delay * (0.5 + Math.random() * 0.5);
    }
    
    // 人間らしい変動を追加
    delay = this.getHumanLikeDelay(delay, 0.2);
    
    console.log(`Backoff: Attempt ${attemptNumber}, waiting ${Math.round(delay / 1000)} seconds...`);
    
    // 待機中のコールバックを実行
    if (config.onWait) {
      config.onWait(delay, attemptNumber);
    }
    
    // 待機
    await DomUtil.sleep(Math.round(delay));
    
    return delay;
  },

  // レート制限に対応した再試行機能
  async retryWithBackoff(operation, options = {}) {
    const defaults = {
      maxAttempts: 5,
      shouldRetry: (error) => {
        // レート制限またはアクセス拒否の場合は再試行
        return this.detectRateLimit() || 
               (error && error.message && error.message.includes('rate'));
      },
      onRetry: null,
      backoffOptions: {}
    };
    
    const config = { ...defaults, ...options };
    let lastError;
    
    for (let attempt = 1; attempt <= config.maxAttempts; attempt++) {
      try {
        // 操作を実行
        const result = await operation();
        
        // 成功した場合は結果を返す
        return result;
        
      } catch (error) {
        lastError = error;
        console.error(`Attempt ${attempt} failed:`, error.message);
        
        // 再試行すべきかチェック
        if (!config.shouldRetry(error) || attempt === config.maxAttempts) {
          throw error;
        }
        
        // 再試行前のコールバック
        if (config.onRetry) {
          config.onRetry(attempt, error);
        }
        
        // バックオフ待機
        await this.exponentialBackoff(attempt, config.backoffOptions);
      }
    }
    
    throw lastError;
  },

  // セッション管理
  sessionManager: {
    startTime: null,
    actionCount: 0,
    
    // セッション開始
    startSession() {
      this.startTime = Date.now();
      this.actionCount = 0;
      console.log('Scraping session started');
    },
    
    // アクション記録
    recordAction() {
      this.actionCount++;
    },
    
    // セッション時間を取得（分）
    getSessionDuration() {
      if (!this.startTime) return 0;
      return (Date.now() - this.startTime) / (1000 * 60);
    },
    
    // 休憩が必要かチェック
    shouldTakeBreak(options = {}) {
      const defaults = {
        maxDuration: 30,      // 最大連続稼働時間（分）
        maxActions: 100,      // 最大アクション数
        breakProbability: 0.1 // ランダム休憩の確率
      };
      
      const config = { ...defaults, ...options };
      
      // 時間ベースのチェック
      if (this.getSessionDuration() >= config.maxDuration) {
        return { shouldBreak: true, reason: 'duration' };
      }
      
      // アクション数ベースのチェック
      if (this.actionCount >= config.maxActions) {
        return { shouldBreak: true, reason: 'actions' };
      }
      
      // ランダム休憩
      if (Math.random() < config.breakProbability) {
        return { shouldBreak: true, reason: 'random' };
      }
      
      return { shouldBreak: false };
    },
    
    // 休憩を取る
    async takeBreak(options = {}) {
      const defaults = {
        minDuration: 300000,  // 最小5分
        maxDuration: 900000,  // 最大15分
        message: 'Taking a break...'
      };
      
      const config = { ...defaults, ...options };
      
      // 休憩時間をランダムに決定
      const breakDuration = ScrapingUtil.getHumanLikeDelay(
        (config.minDuration + config.maxDuration) / 2,
        0.3
      );
      
      console.log(`${config.message} Duration: ${Math.round(breakDuration / 60000)} minutes`);
      
      await DomUtil.sleep(Math.round(breakDuration));
      
      // セッションをリセット
      this.startTime = Date.now();
      this.actionCount = 0;
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
  },
  
  // エラー時にスクリーンショットを撮影
  async captureErrorScreenshot(errorType, errorMessage, errorDetails = {}) {
    try {
      // バックグラウンドスクリプトにスクリーンショット要求を送信
      const response = await chrome.runtime.sendMessage({
        type: 'CAPTURE_SCREENSHOT',
        data: {
          errorType: errorType,
          errorMessage: errorMessage,
          errorDetails: errorDetails,
          download: true // 自動ダウンロードも実行
        }
      });
      
      if (response.success) {
        console.log('Error screenshot captured:', response.filename);
      } else {
        console.error('Failed to capture screenshot:', response.error);
      }
      
      return response;
    } catch (error) {
      console.error('Screenshot request error:', error);
      return { success: false, error: error.message };
    }
  }
};