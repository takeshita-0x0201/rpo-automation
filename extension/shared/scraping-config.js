// スクレイピング設定管理

// デフォルト設定（高度な設定は固定）
const DEFAULT_SCRAPING_CONFIG = {
  // ユーザー設定可能項目
  basic: {
    batchSize: 10,
    pageDelay: 5000,
    retryAttempts: 3
  },
  
  // システム固定設定（セキュリティ関連）
  advanced: {
    // リクエスト遅延設定
    delay: {
      min: 3000,       // 最小3秒
      max: 8000,       // 最大8秒
      jitter: true,    // ランダムジッター有効
      pageChange: 5000 // ページ遷移時の追加遅延
    },
    
    // 時間帯別設定
    timeBasedDelay: {
      business: { // 9:00-17:00
        min: 5000,
        max: 10000,
        requestsPerMinute: 6
      },
      evening: {  // 17:00-22:00
        min: 3000,
        max: 6000,
        requestsPerMinute: 10
      },
      night: {    // 22:00-9:00
        min: 2000,
        max: 4000,
        requestsPerMinute: 12
      }
    },
    
    // 休憩設定
    breakInterval: {
      afterRequests: 50,
      duration: 30000,     // 30秒休憩
      longBreakAfter: 200, // 200件後は長い休憩
      longBreakDuration: 120000 // 2分休憩
    },
    
    // HTTPヘッダー設定
    headers: {
      rotateUserAgent: true,
      userAgents: [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
      ],
      includeReferer: true,
      acceptLanguages: ['ja-JP', 'en-US', 'en']
    },
    
    // プロキシ設定（将来の拡張用）
    proxy: {
      enabled: false,
      rotationInterval: 60000, // 1分ごとにローテーション
      maxRequestsPerIP: 10,
      geoConsistent: true
    }
  }
};

// 媒体別設定
const PLATFORM_CONFIGS = {
  bizreach: {
    name: 'BizReach',
    domain: 'bizreach.jp',
    selectors: {
      CANDIDATE_ITEM: '.candidate-item',
      CANDIDATE_NAME: '.candidate-name',
      CANDIDATE_COMPANY: '.current-company',
      CANDIDATE_POSITION: '.current-position',
      CANDIDATE_EXPERIENCE: '.experience',
      CANDIDATE_SKILLS: '.skill-tag',
      CANDIDATE_EDUCATION: '.education',
      NEXT_PAGE_BUTTON: '.pagination-next',
      LOADING_INDICATOR: '.loading-spinner',
      PAGE_INFO: '.page-info'
    },
    urls: {
      searchPage: '/search/candidates',
      candidateDetail: '/candidates/'
    },
    scraper: 'BizreachScraper'
  },
  
  // 将来の媒体追加用
  direct: {
    name: 'Direct Recruiting',
    domain: 'directrecruiting.jp',
    selectors: {
      // TODO: セレクタを定義
    },
    scraper: 'DirectScraper'
  },
  
  // 新しいサイトの例
  exampleSite: {
    name: 'Example Site',
    domain: 'example.com',
    selectors: {
      CANDIDATE_ITEM: '.candidate-item',
      CANDIDATE_NAME: '.candidate-name',
      CANDIDATE_COMPANY: '.company',
      CANDIDATE_POSITION: '.position',
      CANDIDATE_RESUME: '.resume-summary',
      NEXT_PAGE_BUTTON: '.pagination-next',
      LOADING_INDICATOR: '.loading',
      PAGE_INFO: '.page-info'
    },
    urls: {
      searchPage: '/search',
      candidateDetail: '/candidate/'
    },
    scraper: 'ExampleSiteScraper'
  }
};

// 設定管理クラス
class ScrapingConfigManager {
  constructor() {
    this.config = null;
    this.platform = null;
  }
  
  async initialize() {
    // 保存された設定を読み込み
    const savedSettings = await StorageUtil.get(STORAGE_KEYS.SETTINGS) || {};
    
    // デフォルト設定とマージ（基本設定のみ）
    this.config = {
      basic: {
        ...DEFAULT_SCRAPING_CONFIG.basic,
        ...savedSettings
      },
      advanced: DEFAULT_SCRAPING_CONFIG.advanced
    };
  }
  
  // 現在の時間帯に基づく遅延を取得
  getDelay() {
    const hour = new Date().getHours();
    let delayConfig;
    
    if (hour >= 9 && hour < 17) {
      delayConfig = this.config.advanced.timeBasedDelay.business;
    } else if (hour >= 17 && hour < 22) {
      delayConfig = this.config.advanced.timeBasedDelay.evening;
    } else {
      delayConfig = this.config.advanced.timeBasedDelay.night;
    }
    
    // ランダムジッターを適用
    if (this.config.advanced.delay.jitter) {
      return Math.floor(
        Math.random() * (delayConfig.max - delayConfig.min) + delayConfig.min
      );
    }
    
    return delayConfig.min;
  }
  
  // リクエスト数に基づく休憩が必要か確認
  shouldTakeBreak(requestCount) {
    const { breakInterval } = this.config.advanced;
    
    if (requestCount > 0 && requestCount % breakInterval.longBreakAfter === 0) {
      return { needed: true, duration: breakInterval.longBreakDuration };
    }
    
    if (requestCount > 0 && requestCount % breakInterval.afterRequests === 0) {
      return { needed: true, duration: breakInterval.duration };
    }
    
    return { needed: false };
  }
  
  // ランダムなUser-Agentを取得
  getRandomUserAgent() {
    const { headers } = this.config.advanced;
    if (!headers.rotateUserAgent) {
      return navigator.userAgent;
    }
    
    const agents = headers.userAgents;
    return agents[Math.floor(Math.random() * agents.length)];
  }
  
  // 媒体設定を設定
  setPlatform(platformId) {
    this.platform = PLATFORM_CONFIGS[platformId];
    if (!this.platform) {
      throw new Error(`Unknown platform: ${platformId}`);
    }
  }
  
  // 媒体固有のセレクタを取得
  getSelector(name) {
    if (!this.platform) {
      throw new Error('Platform not set');
    }
    return this.platform.selectors[name];
  }
  
  // 現在の設定を取得
  getConfig() {
    return {
      ...this.config.basic,
      platform: this.platform
    };
  }
}

// シングルトンインスタンス
const scrapingConfig = new ScrapingConfigManager();

// エクスポート
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { scrapingConfig, PLATFORM_CONFIGS };
}