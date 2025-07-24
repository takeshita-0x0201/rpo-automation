// OpenWork スクレイパー
class OpenWorkScraper {
  constructor() {
    this.name = 'OpenWork';
    this.domain = 'recruiting.vorkers.com';
    this.platform = 'openwork';
    this.isActive = false;
    this.isPaused = false;
    this.stats = {
      processed: 0,
      success: 0,
      error: 0,
      skipped: 0
    };
  }

  // 初期化
  async initialize() {
    console.log('OpenWork Scraper initialized');
    return true;
  }

  // 現在のページがスクレイピング対象かチェック
  canScrape() {
    return window.location.hostname.includes('recruiting.vorkers.com') &&
           window.location.pathname.includes('/scout/candidates');
  }

  // スクレイピング開始
  async startScraping(sessionData) {
    console.log('Starting OpenWork scraping with session:', sessionData);
    
    this.isActive = true;
    this.isPaused = false;
    this.sessionData = sessionData;
    this.stats = { processed: 0, success: 0, error: 0, skipped: 0 };
    
    // scrape_resumeフラグの確認
    if (!('scrape_resume' in this.sessionData)) {
      console.log('scrape_resume flag not found in sessionData, defaulting to false');
      this.sessionData.scrape_resume = false;
    }
    
    try {
      // 現在のページから開始
      await this.scrapeCurrentBatch();
      
      // 自動的に次のページへ進む場合
      console.log('Auto pagination enabled:', this.sessionData.auto_pagination);
      if (this.sessionData.auto_pagination !== false) {
        // デフォルトでtrueとして扱う
        await this.continueScraping();
      }
      
      return { success: true, stats: this.stats };
    } catch (error) {
      console.error('Scraping error:', error);
      return { success: false, error: error.message };
    }
  }

  // 現在表示されている候補者をスクレイピング
  async scrapeCurrentBatch() {
    console.log('Scraping current batch...');
    
    // 最初の処理前にもランダムな待機（1-3秒）
    if (this.stats.processed === 0) {
      const initialDelay = Math.floor(Math.random() * 2001) + 1000; // 1000-3000ms
      console.log(`Initial wait: ${initialDelay/1000} seconds before first scraping...`);
      await this.wait(initialDelay);
    }
    
    // ドロワー要素を確認
    const drawer = document.querySelector('#testDrawer');
    if (!drawer) {
      throw new Error('候補者情報のドロワーが見つかりません');
    }

    try {
      // 候補者情報を取得
      const candidateData = await this.extractCandidateData();
      
      if (candidateData) {
        // APIに送信
        const result = await this.sendToAPI(candidateData);
        
        if (result.success) {
          this.stats.success++;
          this.updateUI('候補者を保存しました', 'success');
        } else {
          this.stats.error++;
          this.updateUI(`エラー: ${result.error}`, 'error');
        }
      }
      
      this.stats.processed++;
      
      // 進捗状況を更新
      await chrome.runtime.sendMessage({
        type: 'UPDATE_PROGRESS',
        data: {
          current: this.stats.processed,
          total: this.sessionData.pageLimit || 100,
          processed: this.stats.processed,
          success: this.stats.success,
          error: this.stats.error
        }
      });
      
    } catch (error) {
      console.error('Batch scraping error:', error);
      this.stats.error++;
      this.updateUI(`エラー: ${error.message}`, 'error');
    }
  }

  // 候補者データを抽出
  async extractCandidateData() {
    const data = {};
    
    try {
      // 候補者ID - CSSセレクタで取得
      const idElement = document.querySelector('#testDrawer dl dd');
      if (idElement) {
        data.candidate_id = this.cleanText(idElement);
      }
      
      // XPathでの取得も試す
      if (!data.candidate_id) {
        const candidateIdElement = this.getElementByXPath('//*[@id="testDrawer"]/div[1]/div/div/div[1]/div/dl/dd');
        if (candidateIdElement) {
          data.candidate_id = this.cleanText(candidateIdElement);
        }
      }
      
      if (!data.candidate_id) {
        console.warn('候補者IDが見つかりません');
        return null;
      }
      
      // プラットフォーム
      data.platform = this.platform;
      
      // 候補者リンク
      data.candidate_link = `https://recruiting.vorkers.com/scout/candidates/${data.candidate_id}/resume`;
      
      // 現在の会社名
      let companyElement = document.querySelector('#testDrawer h2 span');
      if (!companyElement) {
        companyElement = this.getElementByXPath('//*[@id="testDrawer"]/div[1]/div/div/div[1]/div/div/h2/span');
      }
      if (companyElement) {
        data.candidate_company = this.cleanText(companyElement);
      }
      
      // 性別（OpenWorkでは提供されていない）
      data.gender = null;
      
      // 年齢と在籍企業数を含むp要素を探す
      const infoElements = document.querySelectorAll('#testDrawer p');
      for (const p of infoElements) {
        const text = this.cleanText(p);
        
        // 年齢を抽出
        if (!data.age) {
          const ageMatch = text.match(/(\d+)歳/);
          if (ageMatch) {
            data.age = parseInt(ageMatch[1]);
          }
        }
        
        // 在籍企業数を抽出
        if (!data.enrolled_company_count) {
          const countMatch = text.match(/(\d+)社/);
          if (countMatch) {
            data.enrolled_company_count = parseInt(countMatch[1]);
          }
        }
      }
      
      // レジュメ内容を取得
      console.log('Extracting resume from current document, scrape_resume flag:', this.sessionData.scrape_resume);
      if (this.sessionData.scrape_resume) {
        const resumeParts = [];
        // 1. 固定要素（テーブルやH3タイトル）を先に取得
        const fixedXpaths = [
          '//*[@id="jsContainerContents"]/section/div/div[1]/table[1]',
          '//*[@id="jsContainerContents"]/section/div/div[1]/table[2]',
          '//*[@id="jsContainerContents"]/section/div/div[1]/h3'
        ];

        for (const xpath of fixedXpaths) {
          try {
            const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            const element = result.singleNodeValue;
            if (element) {
              const text = this.cleanText(element);
              if (text) {
                resumeParts.push(text);
              }
            }
          } catch (e) {
            console.error(`[Fixed XPath Error] for ${xpath}:`, e);
          }
        }

        // 2. 職務経歴など、可変するdiv要素を全て取得
        const dynamicDivXpath = '//*[@id="jsContainerContents"]/section/div/div[1]/div';
        try {
          const divResults = document.evaluate(dynamicDivXpath, document, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
          let currentDiv = divResults.iterateNext();
          while (currentDiv) {
            const text = this.cleanText(currentDiv);
            if (text) {
              resumeParts.push(text);
            }
            currentDiv = divResults.iterateNext();
          }
        } catch (e) {
          console.error(`[Dynamic Divs XPath Error] for ${dynamicDivXpath}:`, e);
        }

        if (resumeParts.length > 0) {
          data.candidate_resume = resumeParts.join('\n\n');
          console.log(`Resume assembled from ${resumeParts.length} parts, total length: ${data.candidate_resume.length}`);
        } else {
          console.warn('No resume elements found in the document. The page structure might have changed.');
        }
      }
      
      // その他の必須フィールド
      data.client_id = this.sessionData.clientId || this.sessionData.client_id;
      data.requirement_id = this.sessionData.requirementId || this.sessionData.requirement_id;
      data.scraping_session_id = this.sessionData.sessionId || this.sessionData.session_id;
      data.scraped_by = this.sessionData.scraped_by || 'extension';
      data.scraped_at = new Date().toISOString();
      
      console.log('Extracted candidate data:', data);
      
      // 必須フィールドの確認
      const requiredFields = ['candidate_id', 'platform', 'client_id', 'requirement_id', 'scraping_session_id'];
      const missingFields = requiredFields.filter(field => !data[field]);
      if (missingFields.length > 0) {
        console.error('Missing required fields:', missingFields);
      }
      
      // データ型の確認
      console.log('Data types check:', {
        candidate_id: typeof data.candidate_id,
        client_id: typeof data.client_id,
        requirement_id: typeof data.requirement_id,
        scraping_session_id: typeof data.scraping_session_id,
        age: typeof data.age,
        enrolled_company_count: typeof data.enrolled_company_count
      });
      
      // 実際の値も確認
      console.log('Field values:', {
        client_id: data.client_id,
        requirement_id: data.requirement_id,
        scraping_session_id: data.scraping_session_id
      });
      
      return data;
      
    } catch (error) {
      console.error('Data extraction error:', error);
      throw error;
    }
  }

  // XPathで要素を取得
  getElementByXPath(xpath) {
    try {
      const result = document.evaluate(
        xpath,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      );
      return result.singleNodeValue;
    } catch (error) {
      console.error('XPath error:', xpath, error);
      return null;
    }
  }

  // 現在の候補者IDを取得
  getCurrentCandidateId() {
    try {
      // 候補者ID要素を探す
      const idElement = document.querySelector('#testDrawer dl dd') || 
                       this.getElementByXPath('//*[@id="testDrawer"]/div[1]/div/div/div[1]/div/dl/dd');
      return idElement ? this.cleanText(idElement) : null;
    } catch (error) {
      console.error('Error getting current candidate ID:', error);
      return null;
    }
  }

  // 候補者の変更を待つ
  async waitForCandidateChange(previousCandidateId) {
    console.log('Waiting for candidate change from:', previousCandidateId);
    let attempts = 0;
    const maxAttempts = 30; // 最大3秒待機
    
    while (attempts < maxAttempts) {
      await this.wait(100);
      const currentId = this.getCurrentCandidateId();
      
      if (currentId && currentId !== previousCandidateId) {
        console.log('Candidate changed to:', currentId);
        await this.wait(500); // 追加の安定待機
        return;
      }
      
      attempts++;
    }
    
    console.warn('Timeout waiting for candidate change');
  }

  // 次のページへ移動して継続
  async continueScraping() {
    if (!this.isActive || this.isPaused) {
      return;
    }
    
    // ページ数制限に達した場合
    if (this.sessionData.pageLimit && this.stats.processed >= this.sessionData.pageLimit) {
      console.log('Page limit reached');
      this.updateUI('ページ数制限に達しました', 'success');
      
      // 完了を通知
      await chrome.runtime.sendMessage({
        type: 'SCRAPING_COMPLETE',
        data: {
          sessionId: this.sessionData.sessionId,
          stats: this.stats
        }
      });
      return;
    }
    
    // 次へボタンを探す（複数のセレクタを試す）
    console.log('Looking for next button...');
    
    let nextButton = this.getElementByXPath('//*[@id="testDrawer"]/div[1]/div/div/div[1]/ul/li[2]/a');
    
    // XPathで見つからない場合はCSSセレクタも試す
    if (!nextButton) {
      const cssSelectors = [
        'a.button.button-white:contains("次の候補者")',
        '#testDrawer a.button-white',
        '#testDrawer ul li:nth-child(2) a',
        '#testDrawer a[class*="button-white"]',
        'a.button.button-white.fs-11.w-100'
      ];
      
      for (const selector of cssSelectors) {
        try {
          if (selector.includes(':contains')) {
            // :contains擬似セレクタの場合は別処理
            const buttons = document.querySelectorAll('a.button.button-white');
            for (const btn of buttons) {
              if (btn.textContent.includes('次の候補者')) {
                nextButton = btn;
                console.log('Next button found by text content');
                break;
              }
            }
          } else {
            nextButton = document.querySelector(selector);
          }
          
          if (nextButton) {
            console.log(`Next button found with selector: ${selector}`);
            break;
          }
        } catch (e) {
          // セレクタエラーを無視
        }
      }
    }
    
    if (nextButton) {
      // ボタンの状態を確認
      const isDisabled = nextButton.disabled || 
                        nextButton.classList.contains('disabled') ||
                        nextButton.getAttribute('aria-disabled') === 'true';
      
      console.log('Next button found, disabled:', isDisabled);
      
      if (!isDisabled) {
        console.log('Moving to next candidate...');
        
        // 現在の候補者IDを記録
        const currentCandidateId = this.getCurrentCandidateId();
        console.log('Current candidate ID:', currentCandidateId);
        
        // クリック前に待機（5-10秒のランダム）
        const minDelay = 5000; // 5秒
        const maxDelay = 10000; // 10秒
        const randomDelay = Math.floor(Math.random() * (maxDelay - minDelay + 1)) + minDelay;
        console.log(`Waiting ${randomDelay/1000} seconds before clicking next button...`);
        await this.wait(randomDelay);
        
        // 次の候補者へ
        nextButton.click();
        
        // ページが更新されるのを待つ（候補者IDの変更を待つ）
        await this.waitForCandidateChange(currentCandidateId);
        
        // 次の候補者をスクレイピング
        await this.scrapeCurrentBatch();
        
        // 再帰的に続行
        await this.continueScraping();
      } else {
        console.log('Next button is disabled, no more candidates');
        this.updateUI('すべての候補者を処理しました', 'success');
        
        // 完了を通知
        await chrome.runtime.sendMessage({
          type: 'SCRAPING_COMPLETE',
          data: {
            sessionId: this.sessionData.sessionId,
            stats: this.stats
          }
        });
      }
    } else {
      console.log('No more candidates or scraping stopped');
      this.updateUI('スクレイピングが完了しました', 'success');
      
      // 完了を通知
      await chrome.runtime.sendMessage({
        type: 'SCRAPING_COMPLETE',
        data: {
          sessionId: this.sessionData.sessionId,
          stats: this.stats
        }
      });
    }
  }

  // APIに候補者データを送信（background script経由）
  async sendToAPI(candidateData) {
    try {
      console.log('Sending candidate data to API:', candidateData);
      console.log('Session data:', this.sessionData);
      
      // 送信するデータの構造を確認
      const messageData = {
        candidates: [candidateData],
        sessionId: this.sessionData.sessionId,
        clientId: this.sessionData.clientId,
        requirementId: this.sessionData.requirementId
      };
      
      console.log('Message data to send:', JSON.stringify(messageData, null, 2));
      
      // background scriptに送信
      const response = await chrome.runtime.sendMessage({
        type: 'SEND_CANDIDATES',
        data: messageData
      });
      
      if (response && response.success) {
        return { success: true, data: response.data };
      } else {
        // エラーメッセージの詳細を取得
        let errorMessage = 'API送信に失敗しました';
        if (response?.error) {
          // エラーメッセージが既に整形されている場合はそのまま使用
          errorMessage = response.error;
        }
        if (response?.details) {
          console.error('API Error details:', response.details);
          // 詳細エラー情報がある場合は、その内容も確認
          if (response.details.detail && Array.isArray(response.details.detail)) {
            console.error('Validation errors from API:');
            response.details.detail.forEach((err, index) => {
              console.error(`  Error ${index + 1}:`, err);
              if (err.loc) {
                console.error(`    Location: ${err.loc.join(' -> ')}`);
              }
              if (err.msg) {
                console.error(`    Message: ${err.msg}`);
              }
              if (err.type) {
                console.error(`    Type: ${err.type}`);
              }
            });
          } else if (Array.isArray(response.details)) {
            console.error('Validation errors:');
            response.details.forEach((err, index) => {
              console.error(`  ${index + 1}:`, err);
            });
          }
        }
        throw new Error(errorMessage);
      }
    } catch (error) {
      console.error('API error:', error);
      return { success: false, error: error.message };
    }
  }

  // テキストのクリーンアップ
  cleanText(element) {
    if (!element) return '';
    
    const text = element.textContent || element.innerText || '';
    return text.trim()
      .replace(/\s+/g, ' '); // 複数の空白や改行をスペース1つに統一
  }

  // 待機処理
  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // UI更新
  updateUI(message, type = 'info') {
    // content.jsのupdateOverlayStatus関数を呼び出す
    if (typeof updateOverlayStatus === 'function') {
      updateOverlayStatus(message, type);
    }
    
    // 統計情報も更新
    if (typeof updateOverlayStats === 'function') {
      const progress = Math.round((this.stats.processed / (this.sessionData.pageLimit || 100)) * 100);
      updateOverlayStats({
        ...this.stats,
        progress: progress
      });
    }
  }

  // 一時停止
  pause() {
    this.isPaused = true;
    this.updateUI('一時停止中', 'paused');
  }

  // 再開
  resume() {
    this.isPaused = false;
    this.updateUI('再開しました', 'info');
    
    // 自動ページ送りが有効な場合は継続
    if (this.sessionData && this.sessionData.auto_pagination) {
      this.continueScraping();
    }
  }

  // 停止
  stop() {
    this.isActive = false;
    this.isPaused = false;
    this.updateUI('スクレイピングを停止しました', 'info');
  }

  // 現在のページのみスクレイピング（単発実行用）
  async scrapeCurrentPage() {
    try {
      const candidateData = await this.extractCandidateData();
      
      if (!candidateData) {
        return { success: false, error: '候補者データが見つかりません' };
      }
      
      // セッションデータがない場合のデフォルト値
      if (!this.sessionData) {
        this.sessionData = {
          client_id: 'manual',
          requirement_id: 'manual',
          scraped_by: 'manual'
        };
      }
      
      candidateData.client_id = this.sessionData.client_id;
      candidateData.requirement_id = this.sessionData.requirement_id;
      candidateData.scraped_by = this.sessionData.scraped_by;
      
      return { success: true, data: candidateData };
    } catch (error) {
      console.error('Scrape current page error:', error);
      return { success: false, error: error.message };
    }
  }
}

// デバッグログ
console.log('openwork.js loading...');

// グローバルに公開（Chrome拡張機能のcontent script内）
window.OpenWorkScraper = OpenWorkScraper;

// テスト用のヘルパー関数をグローバルに公開
window.testOpenWork = {
  // スクレイパーインスタンスを作成
  createScraper: function() {
    const scraper = new OpenWorkScraper();
    console.log('OpenWorkScraper instance created:', scraper);
    return scraper;
  },
  
  // 現在のページの候補者データを取得（レジュメなし）
  extractCurrentCandidate: async function() {
    const scraper = new OpenWorkScraper();
    scraper.sessionData = {
      clientId: 'test-client-id',
      requirementId: 'test-requirement-id',
      sessionId: 'test-session-id',
      scrape_resume: false
    };
    
    try {
      const data = await scraper.extractCandidateData();
      console.log('Extracted candidate data:', data);
      return data;
    } catch (error) {
      console.error('Error extracting candidate:', error);
      return null;
    }
  },
  
  // レジュメを含む完全な候補者データを取得
  extractWithResume: async function() {
    const scraper = new OpenWorkScraper();
    scraper.sessionData = {
      clientId: 'test-client-id',
      requirementId: 'test-requirement-id',
      sessionId: 'test-session-id',
      scrape_resume: true
    };
    
    try {
      const data = await scraper.extractCandidateData();
      console.log('Extracted candidate data with resume:', data);
      return data;
    } catch (error) {
      console.error('Error extracting candidate with resume:', error);
      return null;
    }
  },
  
  // 次へボタンを探す
  findNextButton: function() {
    const scraper = new OpenWorkScraper();
    
    // XPathで探す
    console.log('Searching for next button...');
    let button = scraper.getElementByXPath('//*[@id="testDrawer"]/div[1]/div/div/div[1]/ul/li[2]/a');
    if (button) {
      console.log('Found with XPath:', button);
      return button;
    }
    
    // CSSセレクタで探す
    const selectors = [
      'a.button.button-white',
      '#testDrawer a.button-white',
      '#testDrawer ul li:nth-child(2) a'
    ];
    
    for (const selector of selectors) {
      button = document.querySelector(selector);
      if (button) {
        console.log(`Found with CSS selector: ${selector}`, button);
        return button;
      }
    }
    
    // テキストで探す
    const buttons = document.querySelectorAll('a.button');
    for (const btn of buttons) {
      if (btn.textContent.includes('次の候補者')) {
        console.log('Found by text content:', btn);
        return btn;
      }
    }
    
    console.log('Next button not found');
    return null;
  },
  
  // スクレイピング処理を開始（ランダムインターバル付き）
  startScrapingWithInterval: async function(pageLimit = 3) {
    console.log(`Starting scraping with random 5-10s interval, limit: ${pageLimit} pages`);
    
    const scraper = new OpenWorkScraper();
    scraper.sessionData = {
      clientId: 'test-client-id',
      requirementId: 'test-requirement-id',
      sessionId: 'test-session-id',
      scrape_resume: true,
      pageLimit: pageLimit,
      scraping_delay: 7000, // この値は使用されません（ランダムを使用）
      auto_pagination: true
    };
    
    scraper.isActive = true;
    scraper.stats = { processed: 0, success: 0, error: 0, skipped: 0 };
    
    // 処理をシミュレート
    for (let i = 0; i < pageLimit; i++) {
      console.log(`\n--- Processing page ${i + 1}/${pageLimit} ---`);
      
      try {
        // 候補者データを取得
        const data = await scraper.extractCandidateData();
        if (data) {
          console.log('Candidate extracted:', data.candidate_id);
          scraper.stats.processed++;
          scraper.stats.success++;
        }
        
        // 次のページへ移動する前に待機
        if (i < pageLimit - 1) {
          const randomInterval = Math.floor(Math.random() * 5001) + 5000; // 5000-10000ms
          console.log(`Waiting ${randomInterval/1000} seconds before next page...`);
          await new Promise(resolve => setTimeout(resolve, randomInterval));
          
          // 次へボタンをクリック
          const nextButton = this.findNextButton();
          if (nextButton && !nextButton.disabled) {
            console.log('Clicking next button...');
            nextButton.click();
            
            // ページの更新を待つ
            await new Promise(resolve => setTimeout(resolve, 2000));
          } else {
            console.log('Next button not found or disabled');
            break;
          }
        }
      } catch (error) {
        console.error('Error in scraping loop:', error);
        scraper.stats.error++;
      }
    }
    
    console.log('\n--- Scraping completed ---');
    console.log('Stats:', scraper.stats);
    return scraper.stats;
  }
};

// 読み込み確認
console.log('OpenWorkScraper loaded successfully');
console.log('Test functions available:');
console.log('- window.testOpenWork.createScraper()');
console.log('- window.testOpenWork.extractCurrentCandidate()');
console.log('- window.testOpenWork.extractWithResume()');
console.log('- window.testOpenWork.findNextButton()');
console.log('- window.testOpenWork.startScrapingWithInterval(pageLimit) // 5-10秒のランダムインターバル');