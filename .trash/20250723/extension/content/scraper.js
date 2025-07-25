// Bizreach スクレイピングメインモジュール

class BizreachScraper {
  constructor() {
    this.isRunning = false;
    this.isPaused = false;
    this.sessionData = null;
    this.candidates = [];
    this.processedUrls = new Set();
    this.currentBatch = [];
    this.errors = [];
  }

  // 初期化
  async init() {
    DebugUtil.log('Initializing scraper...');
    
    // メッセージリスナーの設定
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request).then(sendResponse);
      return true;
    });

    // ページ変更の監視
    this.observePageChanges();
  }

  // メッセージハンドラー
  async handleMessage(request) {
    DebugUtil.log('Content script received message:', request.type);
    
    switch (request.type) {
      case MESSAGE_TYPES.START_SCRAPING:
        return await this.startScraping(request.data);
        
      case MESSAGE_TYPES.PAUSE_SCRAPING:
        return this.pauseScraping();
        
      case MESSAGE_TYPES.RESUME_SCRAPING:
        return this.resumeScraping();
        
      case MESSAGE_TYPES.STOP_SCRAPING:
        return this.stopScraping();
        
      default:
        return { success: false, error: 'Unknown message type' };
    }
  }

  // スクレイピング開始
  async startScraping(data) {
    try {
      DebugUtil.log('Starting scraping with data:', data);
      
      if (this.isRunning) {
        return { success: false, error: 'スクレイピングは既に実行中です' };
      }

      // セッションデータを保存
      this.sessionData = {
        sessionId: data.sessionId,
        clientId: data.clientId,
        requirementId: data.requirementId
      };

      // 採用要件を取得
      const requirementResponse = await this.fetchRequirement(data.requirementId);
      if (!requirementResponse.success) {
        return { success: false, error: '採用要件の取得に失敗しました' };
      }

      this.requirement = requirementResponse.requirement;
      DebugUtil.log('Loaded requirement:', this.requirement);

      // 状態を初期化
      this.isRunning = true;
      this.isPaused = false;
      this.candidates = [];
      this.processedUrls.clear();
      this.currentBatch = [];
      this.errors = [];
      this.currentPage = 1;  // 現在のページ番号を追跡

      // UIを表示
      window.uiOverlay.show();
      window.uiOverlay.updateStatus('running');

      // スクレイピングループを開始
      await this.runScrapingLoop();

      return { success: true };
    } catch (error) {
      DebugUtil.error('Failed to start scraping:', error);
      window.uiOverlay.showError('スクレイピングの開始に失敗しました');
      return { success: false, error: error.message };
    }
  }

  // 採用要件を取得
  async fetchRequirement(requirementId) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.GET_REQUIREMENT,
        data: { requirementId }
      });

      if (response.success) {
        return { success: true, requirement: response.requirement };
      } else {
        return { success: false, error: response.error };
      }
    } catch (error) {
      DebugUtil.error('Failed to fetch requirement:', error);
      return { success: false, error: error.message };
    }
  }

  // メインのスクレイピングループ
  async runScrapingLoop() {
    try {
      while (this.isRunning && !this.isPaused) {
        // 候補者一覧ページか確認
        if (!this.isCandidateListPage()) {
          window.uiOverlay.showError('候補者一覧ページではありません');
          break;
        }

        // 現在のページをスクレイピング
        const scraped = await this.scrapeCurrentPage();
        
        if (!scraped) {
          DebugUtil.log('No candidates found on current page');
          break;
        }

        // 次のページの確認と遷移
        if (this.hasNextPage()) {
          DebugUtil.log(`Page ${this.currentPage} completed. Moving to next page...`);
          
          // XPathで次ページボタンを取得
          const xpath = '//*[@id="jsi_resume_page_inner"]/div/div[1]/ul/li[2]/a';
          let nextButton = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
          
          // XPathで見つからない場合は従来のセレクタを試す
          if (!nextButton) {
            nextButton = document.querySelector(BIZREACH_SELECTORS.NEXT_PAGE_BUTTON);
          }
          
          if (nextButton) {
            DebugUtil.log('Clicking next page button...');
            nextButton.click();
            this.currentPage++;
            
            // ページ遷移を待つ
            await DomUtil.sleep(SCRAPING_CONFIG.PAGE_DELAY);
            await this.waitForPageLoad();
          } else {
            DebugUtil.log('Next page button not found');
            break;
          }
        } else {
          DebugUtil.log('No more pages. Scraping completed.');
          break;
        }
      }

      // 残りのバッチを送信
      if (this.currentBatch.length > 0) {
        await this.sendBatch();
      }

      // スクレイピング完了
      if (this.isRunning) {
        this.completeScraping();
      }
    } catch (error) {
      DebugUtil.error('Scraping loop error:', error);
      window.uiOverlay.showError('スクレイピング中にエラーが発生しました');
      this.handleError(error);
    }
  }

  // 現在のページをスクレイピング（ページ遷移は行わない）
  async scrapeCurrentPage() {
    try {
      // ページの読み込みを待つ
      await this.waitForPageLoad();

      // 候補者要素を取得
      const candidateElements = await this.getCandidateElements();
      
      // デバッグ情報を出力
      DebugUtil.log(`Scraping page ${this.currentPage}:`, {
        url: window.location.href,
        candidateCount: candidateElements.length,
        totalProcessed: this.candidates.length
      });
      
      if (candidateElements.length === 0) {
        return false;
      }

      // 総数を更新
      const totalCount = this.getTotalCandidateCount();
      window.uiOverlay.updateProgress({
        current: this.candidates.length,
        total: totalCount,
        success: this.candidates.length - this.errors.length,
        error: this.errors.length
      });

      // 各候補者を処理
      let processedCount = 0;
      for (const element of candidateElements) {
        if (!this.isRunning || this.isPaused) break;

        const processed = await this.processCandidateElement(element);
        if (processed) {
          processedCount++;
        }
        
        // 進捗を更新
        window.uiOverlay.updateProgress({
          current: this.candidates.length,
          total: totalCount,
          success: this.candidates.length - this.errors.length,
          error: this.errors.length
        });

        // バッチサイズに達したら送信
        if (this.currentBatch.length >= SCRAPING_CONFIG.BATCH_SIZE) {
          await this.sendBatch();
        }
      }

      return processedCount > 0;
    } catch (error) {
      DebugUtil.error('Page scraping error:', error);
      throw error;
    }
  }

  // 候補者要素を処理
  async processCandidateElement(element) {
    try {
      // 候補者のURLを取得
      const url = this.getCandidateUrl(element);
      if (!url || this.processedUrls.has(url)) {
        return;
      }

      // 候補者データを抽出
      const candidateData = this.extractCandidateData(element);
      if (!candidateData) {
        return;
      }

      // URLとメタデータを追加
      candidateData.url = url;
      candidateData.bizreach_url = url;
      candidateData.requirement_id = this.sessionData.requirementId;
      candidateData.session_id = this.sessionData.sessionId;
      candidateData.client_id = this.sessionData.clientId;

      // データを整形
      const formattedCandidate = window.dataFormatter.formatCandidate(candidateData);
      if (!formattedCandidate) {
        this.errors.push({ url, error: 'データの整形に失敗しました' });
        return;
      }

      // 採用要件との関連付け情報を追加
      const candidateWithContext = window.dataFormatter.addRequirementContext(
        formattedCandidate,
        this.sessionData.requirementId,
        this.sessionData.sessionId,
        this.sessionData.clientId
      );

      // 処理済みとしてマーク
      this.processedUrls.add(url);
      this.candidates.push(candidateWithContext);
      this.currentBatch.push(candidateWithContext);

      DebugUtil.log('Processed candidate:', candidateWithContext.name);
      return true;
    } catch (error) {
      DebugUtil.error('Failed to process candidate:', error);
      this.errors.push({ element, error: error.message });
      return false;
    }
  }

  // 候補者データを抽出（実際のDOM構造に合わせて調整が必要）
  extractCandidateData(element) {
    try {
      const data = {
        // 基本情報
        name: DomUtil.getTextContent(element, BIZREACH_SELECTORS.CANDIDATE_NAME),
        current_company: DomUtil.getTextContent(element, BIZREACH_SELECTORS.CANDIDATE_COMPANY),
        current_position: DomUtil.getTextContent(element, BIZREACH_SELECTORS.CANDIDATE_POSITION),
        
        // 経験・スキル
        experience: DomUtil.getTextContent(element, BIZREACH_SELECTORS.CANDIDATE_EXPERIENCE),
        skills: this.extractSkills(element),
        
        // 学歴
        education: DomUtil.getTextContent(element, BIZREACH_SELECTORS.CANDIDATE_EDUCATION),
        
        // HTML（デバッグ用）
        html: element.outerHTML
      };

      return data;
    } catch (error) {
      DebugUtil.error('Failed to extract candidate data:', error);
      return null;
    }
  }

  // スキルを抽出
  extractSkills(element) {
    const skillElements = element.querySelectorAll(BIZREACH_SELECTORS.CANDIDATE_SKILLS);
    return Array.from(skillElements).map(el => el.textContent.trim());
  }

  // 候補者のURLを取得
  getCandidateUrl(element) {
    const linkElement = element.querySelector('a');
    if (linkElement) {
      const href = linkElement.getAttribute('href');
      if (href) {
        return new URL(href, window.location.origin).href;
      }
    }
    return null;
  }

  // バッチを送信
  async sendBatch() {
    try {
      if (this.currentBatch.length === 0) return;

      DebugUtil.log(`Sending batch of ${this.currentBatch.length} candidates`);

      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.SEND_CANDIDATES,
        data: {
          candidates: this.currentBatch,
          sessionId: this.sessionData.sessionId
        }
      });

      if (response.success) {
        DebugUtil.log(`Batch sent successfully: ${response.processed} processed`);
        this.currentBatch = [];
      } else {
        DebugUtil.error('Failed to send batch:', response.error);
        this.errors.push({ batch: this.currentBatch, error: response.error });
      }
    } catch (error) {
      DebugUtil.error('Batch send error:', error);
      this.errors.push({ batch: this.currentBatch, error: error.message });
    }
  }

  // ページ関連のヘルパーメソッド
  isCandidateListPage() {
    // Bizreachの候補者一覧ページのURLパターンをチェック
    const url = window.location.href;
    const isValid = url.includes('/search/') || 
                    url.includes('/candidates/') ||
                    url.includes('/hrbc/search/') ||  // 追加のパターン
                    url.includes('/talent/');          // 追加のパターン
    
    DebugUtil.log('Page validation:', {
      url: url,
      isValid: isValid,
      patterns: {
        search: url.includes('/search/'),
        candidates: url.includes('/candidates/'),
        hrbc: url.includes('/hrbc/search/'),
        talent: url.includes('/talent/')
      }
    });
    
    return isValid;
  }

  async waitForPageLoad() {
    DebugUtil.log('Waiting for page load...');
    
    // URL変更を検知するための待機
    await DomUtil.sleep(1000);
    
    // ローディング要素が消えるまで待つ
    const loadingSelector = BIZREACH_SELECTORS.LOADING_INDICATOR;
    let attempts = 0;
    const maxAttempts = 30;

    while (attempts < maxAttempts) {
      const loading = document.querySelector(loadingSelector);
      if (!loading || loading.style.display === 'none') {
        break;
      }
      await DomUtil.sleep(1000);
      attempts++;
    }

    // 候補者要素が表示されるまで待つ（エラーハンドリング付き）
    try {
      await DomUtil.waitForElements(BIZREACH_SELECTORS.CANDIDATE_ITEM, 1);
      DebugUtil.log('Page loaded successfully');
    } catch (error) {
      DebugUtil.log('Warning: Candidate elements not found with default selector');
      // 代替セレクタを試す
      const alternativeSelectors = [
        '[class*="candidate"]',
        '[data-test*="candidate"]',
        '.search-result-item',
        '.list-item'
      ];
      
      for (const selector of alternativeSelectors) {
        const elements = document.querySelectorAll(selector);
        if (elements.length > 0) {
          DebugUtil.log(`Found candidates with alternative selector: ${selector}`);
          break;
        }
      }
    }
  }

  async getCandidateElements() {
    // まずデフォルトセレクタを試す
    let elements = document.querySelectorAll(BIZREACH_SELECTORS.CANDIDATE_ITEM);
    
    // 見つからない場合は代替セレクタを試す
    if (elements.length === 0) {
      const alternativeSelectors = [
        '[class*="candidate-item"]',
        '[class*="candidate-card"]',
        '[data-test*="candidate"]',
        '.search-result-item',
        'article[class*="result"]',
        'div[class*="result-item"]'
      ];
      
      for (const selector of alternativeSelectors) {
        elements = document.querySelectorAll(selector);
        if (elements.length > 0) {
          DebugUtil.log(`Using alternative candidate selector: ${selector} (found ${elements.length} items)`);
          // 今後このセレクタを使用するように更新
          BIZREACH_SELECTORS.CANDIDATE_ITEM = selector;
          break;
        }
      }
    }
    
    return elements;
  }

  getTotalCandidateCount() {
    // ページに表示されている総数を取得（実装は実際のDOM構造に依存）
    const pageInfo = document.querySelector(BIZREACH_SELECTORS.PAGE_INFO);
    if (pageInfo) {
      const match = pageInfo.textContent.match(/\d+/g);
      if (match && match.length > 0) {
        return parseInt(match[match.length - 1], 10);
      }
    }
    return this.candidates.length;
  }

  hasNextPage() {
    // XPathで次ページボタンを検索
    const xpath = '//*[@id="jsi_resume_page_inner"]/div/div[1]/ul/li[2]/a';
    const nextButton = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    
    // XPathで見つからない場合は従来のセレクタも試す
    if (!nextButton) {
      const cssButton = document.querySelector(BIZREACH_SELECTORS.NEXT_PAGE_BUTTON);
      return cssButton && !cssButton.disabled;
    }
    
    // ボタンが存在し、無効化されていないか確認
    return nextButton && !nextButton.classList.contains('disabled') && !nextButton.hasAttribute('disabled');
  }

  // このメソッドは新しいループ構造では不要だが、互換性のために残す
  async goToNextPage() {
    // runScrapingLoop内で処理されるため、ここでは何もしない
    DebugUtil.log('goToNextPage called - handled by runScrapingLoop');
  }

  // スクレイピング制御メソッド
  pauseScraping() {
    this.isPaused = true;
    window.uiOverlay.updateStatus('paused');
    return { success: true };
  }

  resumeScraping() {
    this.isPaused = false;
    window.uiOverlay.updateStatus('running');
    this.runScrapingLoop(); // ループを再開
    return { success: true };
  }

  stopScraping() {
    this.isRunning = false;
    this.isPaused = false;
    window.uiOverlay.updateStatus('idle');
    return { success: true };
  }

  completeScraping() {
    this.isRunning = false;
    window.uiOverlay.complete();
    
    // 完了を通知
    chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.UPDATE_PROGRESS,
      data: {
        current: this.candidates.length,
        total: this.candidates.length,
        success: this.candidates.length - this.errors.length,
        error: this.errors.length
      }
    });

    DebugUtil.log('Scraping completed:', {
      total: this.candidates.length,
      errors: this.errors.length
    });
  }

  handleError(error) {
    chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.SCRAPING_ERROR,
      error: error.message
    });
  }

  // ページ変更の監視
  observePageChanges() {
    // URLの変更を監視
    let lastUrl = window.location.href;
    const observer = new MutationObserver(() => {
      if (window.location.href !== lastUrl) {
        lastUrl = window.location.href;
        DebugUtil.log('Page URL changed:', lastUrl);
        
        // 候補者一覧ページに戻った場合、UIの状態を確認
        if (this.isRunning && this.isCandidateListPage()) {
          window.uiOverlay.show();
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }
}

// このファイルは現在使用されていません
// BizreachScraperクラスのみが必要で、インスタンス化はcontent.jsで行います