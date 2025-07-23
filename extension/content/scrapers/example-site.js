// ExampleSite用スクレイピングロジック

class ExampleSiteScraper {
  constructor() {
    this.candidates = [];
    this.currentBatch = [];
    this.config = null;
    this.sessionInfo = null;
  }

  // 初期化
  async initialize() {
    const settings = await StorageUtil.get('settings');
    this.config = {
      batchSize: settings?.batchSize || 10,
      pageDelay: settings?.pageDelay || 5000,
      saveHtml: settings?.saveHtml || false
    };
    this.totalScrapedCount = 0;
  }

  // メイン処理
  async startScraping(sessionData) {
    try {
      console.log('ExampleSiteScraper.startScraping called with:', sessionData);
      
      this.sessionInfo = sessionData;
      
      // セッション情報の検証
      if (!sessionData.sessionId || !sessionData.clientId || !sessionData.requirementId) {
        throw new Error('セッション情報が不完全です');
      }
      
      this.candidates = [];
      this.currentBatch = [];
      this.isRunning = true;
      this.isPaused = false;
      
      const pageLimit = sessionData.pageLimit || 5;
      
      let pageNumber = 1;
      let hasNextPage = true;

      while (hasNextPage && pageNumber <= pageLimit && this.isRunning) {
        if (this.isPaused) {
          await this.waitForResume();
        }

        console.log(`ページ ${pageNumber} をスクレイピング中...`);
        
        // ページのスクレイピング
        const pageResults = await this.scrapePage();
        
        if (pageResults.candidates.length === 0) {
          console.log('候補者が見つかりませんでした');
          break;
        }

        // バッチに追加
        for (const candidate of pageResults.candidates) {
          this.currentBatch.push(candidate);
          
          if (this.currentBatch.length >= this.config.batchSize) {
            await this.saveBatch();
          }
        }

        // 次のページの確認
        hasNextPage = await this.hasNextPage();
        
        if (hasNextPage && pageNumber < pageLimit) {
          await this.goToNextPage();
          await this.delay(this.config.pageDelay);
        }
        
        pageNumber++;
      }

      // 残りのバッチを保存
      if (this.currentBatch.length > 0) {
        await this.saveBatch();
      }

      return {
        success: true,
        totalScraped: this.totalScrapedCount,
        message: 'スクレイピングが完了しました'
      };

    } catch (error) {
      console.error('Scraping error:', error);
      throw error;
    } finally {
      this.isRunning = false;
    }
  }

  // ページのスクレイピング
  async scrapePage() {
    const candidates = [];
    
    // TODO: サイト固有のセレクタに変更
    const candidateElements = document.querySelectorAll('.candidate-item');
    
    for (const element of candidateElements) {
      try {
        const candidate = {
          // 基本情報
          candidateId: this.extractText(element, '.candidate-id'),
          candidateLink: this.extractHref(element, '.candidate-link'),
          candidateName: this.extractText(element, '.candidate-name'),
          candidateCompany: this.extractText(element, '.company'),
          candidatePosition: this.extractText(element, '.position'),
          candidateResume: this.extractText(element, '.resume-summary'),
          
          // メタデータ
          platform: 'example-site',
          scrapedAt: new Date().toISOString(),
          sessionId: this.sessionInfo.sessionId,
          clientId: this.sessionInfo.clientId,
          requirementId: this.sessionInfo.requirementId
        };

        // 空の候補者はスキップ
        if (candidate.candidateId && candidate.candidateLink) {
          candidates.push(candidate);
        }
      } catch (error) {
        console.error('候補者の抽出エラー:', error);
      }
    }
    
    return { candidates };
  }

  // 次のページが存在するか確認
  async hasNextPage() {
    // TODO: サイト固有のセレクタに変更
    const nextButton = document.querySelector('.pagination-next');
    return nextButton && !nextButton.disabled && !nextButton.classList.contains('disabled');
  }

  // 次のページへ移動
  async goToNextPage() {
    // TODO: サイト固有のセレクタに変更
    const nextButton = document.querySelector('.pagination-next');
    if (nextButton) {
      nextButton.click();
      await this.waitForPageLoad();
    }
  }

  // ページ読み込み待機
  async waitForPageLoad() {
    return new Promise((resolve) => {
      let checkCount = 0;
      const maxChecks = 50;
      
      const checkInterval = setInterval(() => {
        // TODO: サイト固有の読み込み完了判定に変更
        const loadingIndicator = document.querySelector('.loading');
        const hasContent = document.querySelectorAll('.candidate-item').length > 0;
        
        if (!loadingIndicator && hasContent) {
          clearInterval(checkInterval);
          resolve();
        } else if (checkCount >= maxChecks) {
          clearInterval(checkInterval);
          resolve();
        }
        
        checkCount++;
      }, 200);
    });
  }

  // バッチ保存
  async saveBatch() {
    if (this.currentBatch.length === 0) return;
    
    try {
      const message = {
        type: 'SAVE_CANDIDATES',
        data: {
          candidates: this.currentBatch,
          sessionId: this.sessionInfo.sessionId,
          platform: 'example-site'
        }
      };
      
      const response = await chrome.runtime.sendMessage(message);
      
      if (response.success) {
        this.totalScrapedCount += this.currentBatch.length;
        console.log(`${this.currentBatch.length}件の候補者を保存しました`);
        this.currentBatch = [];
      } else {
        throw new Error(response.error || '保存に失敗しました');
      }
    } catch (error) {
      console.error('バッチ保存エラー:', error);
      throw error;
    }
  }

  // ユーティリティメソッド
  extractText(element, selector) {
    const el = element.querySelector(selector);
    return el ? el.textContent.trim() : '';
  }

  extractHref(element, selector) {
    const el = element.querySelector(selector);
    return el ? el.href : '';
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async waitForResume() {
    while (this.isPaused && this.isRunning) {
      await this.delay(100);
    }
  }

  pause() {
    this.isPaused = true;
  }

  resume() {
    this.isPaused = false;
  }

  stop() {
    this.isRunning = false;
    this.isPaused = false;
  }
}