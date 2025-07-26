/**
 * リクナビHR Tech用のスクレイパー
 */

class RikunaviHRTechScraper {
  constructor() {
    this.siteName = 'rikunavihrtech';
    this.baseUrl = 'https://hrtech.rikunabi.com';
    this.candidateCardBaseXPath = '//*[@id="root"]/div/div[2]/div[3]/div/div[1]/div[2]/div/div[2]/div[2]/div[1]/div[3]/div';
    this.closeButtonXPath = '//*[@id="root"]/div/div[2]/div/div[1]/div[2]/img';
    this.candidates = [];
    this.currentBatch = [];
    this.config = null;
    this.sessionInfo = null;
  }

  /**
   * 初期化
   */
  async initialize() {
    // 設定を取得
    const settings = await StorageUtil.get('settings');
    this.config = {
      batchSize: settings?.batchSize || 10,
      pageDelay: settings?.pageDelay || 2000,
      saveHtml: settings?.saveHtml || false
    };
    this.totalScrapedCount = 0;
  }

  /**
   * 現在のページが対象サイトかどうかを判定
   * @returns {boolean}
   */
  canHandle() {
    return window.location.hostname.includes('hrtech.rikunabi.com');
  }

  /**
   * ページタイプを判定
   * @returns {string|null}
   */
  getPageType() {
    const url = window.location.href;
    const path = window.location.pathname;

    // 候補者一覧ページ
    if (path.includes('/scoutroom/') || url.includes('scout_jobseeker_list')) {
      return 'candidate-list';
    }
    // 求人詳細ページ
    else if (path.includes('/detail/') || url.includes('JobId=')) {
      return 'job-detail';
    }
    // 求人一覧ページ
    else if (path === '/' || path.includes('/search') || url.includes('list')) {
      return 'job-list';
    }
    
    return null;
  }

  /**
   * 候補者一覧ページから全候補者情報を抽出
   * @returns {Promise<Array>}
   */
  /**
   * メイン処理 - スクレイピングを開始
   * @param {Object} sessionData - セッション情報
   * @returns {Promise<Object>}
   */
  async startScraping(sessionData) {
    try {
      console.log('RikunaviHRTechScraper.startScraping called with:', sessionData);
      
      // CAPTCHA・アクセス制限のチェック
      if (ScrapingUtil.detectCaptcha()) {
        await this.updateProgress({
          status: 'error',
          message: 'CAPTCHAが検出されました。手動で認証を完了してください。'
        });
        return { success: false, message: 'CAPTCHA検出' };
      }
      
      if (ScrapingUtil.detectRateLimit()) {
        await this.updateProgress({
          status: 'error',
          message: 'レート制限が検出されました。しばらく待ってから再試行してください。'
        });
        return { success: false, message: 'レート制限検出' };
      }
      
      // セッション管理を開始
      ScrapingUtil.sessionManager.startSession();
      
      // セッション情報を保存
      this.sessionInfo = sessionData;
      
      // セッション情報の検証
      if (!sessionData.sessionId || !sessionData.clientId || !sessionData.requirementId) {
        console.error('Missing required session data:', {
          sessionId: !!sessionData.sessionId,
          clientId: !!sessionData.clientId,
          requirementId: !!sessionData.requirementId
        });
        throw new Error('セッション情報が不完全です');
      }
      
      this.candidates = [];
      this.currentBatch = [];
      this.isRunning = true;
      this.isPaused = false;
      
      // カード数制限を取得（リクナビの場合）
      this.cardLimit = sessionData.cardLimit || null;
      
      // スクレイピング開始を通知
      await this.updateProgress({
        status: 'running',
        currentPage: 1,
        totalCandidates: 0,
        message: this.cardLimit ? 
          `スクレイピングを開始しました（最大${this.cardLimit}件）` : 
          'スクレイピングを開始しました'
      });
      
      // 候補者データを抽出
      const results = await this.extractCandidatesData();
      
      // セッション統計をログ
      const sessionDuration = ScrapingUtil.sessionManager.getSessionDuration();
      console.log(`Session statistics: Duration=${Math.round(sessionDuration)}分, Actions=${ScrapingUtil.sessionManager.actionCount}`);
      
      // 完了通知
      const completionMessage = this.isRunning ? 
        `完了: ${results.length}件の候補者を取得しました（セッション時間: ${Math.round(sessionDuration)}分）` :
        `停止: ${results.length}件取得（セッション時間: ${Math.round(sessionDuration)}分）`;
      
      await this.updateProgress({
        status: this.isRunning ? 'completed' : 'stopped',
        currentPage: 1,
        totalCandidates: results.length,
        message: completionMessage
      });
      
      return {
        success: true,
        message: `${results.length}件の候補者データを取得しました`,
        count: results.length,
        sessionDuration: Math.round(sessionDuration)
      };
      
    } catch (error) {
      console.error('RikunaviHRTechScraper: エラー', error);
      return { success: false, message: error.message };
    }
  }

  async extractCandidatesData() {
    console.log('🔍 候補者情報の抽出を開始します...');
    
    // カードの総数を取得
    let cardCount = this.getCardCount();
    if (cardCount === 0) {
      console.log('❌ 候補者カードが見つかりません');
      return [];
    }
    
    // カード数制限がある場合は適用
    if (this.cardLimit && this.cardLimit > 0) {
      cardCount = Math.min(cardCount, this.cardLimit);
      console.log(`✅ ${cardCount} 名の候補者を処理します（制限: ${this.cardLimit}件）`);
    } else {
      console.log(`✅ ${cardCount} 名の候補者が見つかりました`);
    }
    
    // 各カードを処理
    for (let i = 1; i <= cardCount; i++) {
      // 一時停止チェック
      while (this.isPaused && this.isRunning) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      
      if (!this.isRunning) break;
      
      // CAPTCHA・アクセス制限の定期チェック
      if (ScrapingUtil.detectCaptcha()) {
        await this.updateProgress({
          status: 'error',
          message: 'CAPTCHAが検出されました。手動で認証を完了してください。'
        });
        this.stop();
        break;
      }
      
      if (ScrapingUtil.detectRateLimit()) {
        await this.updateProgress({
          status: 'error',
          message: 'レート制限が検出されました。しばらく待ってから再試行してください。'
        });
        this.stop();
        break;
      }
      
      console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
      console.log(`📋 [${i}/${cardCount}] 処理中...`);
      
      try {
        // カードをクリック
        const clicked = await this.clickCard(i);
        
        if (clicked) {
          // 詳細情報を抽出
          const candidateInfo = this.extractCandidateDetail(i);
          
          if (candidateInfo) {
            // APIに送信するデータを整形
            const candidateData = {
              candidate_id: candidateInfo.candidate_id,
              candidate_link: window.location.href,
              candidate_company: candidateInfo.candidate_company || '',
              candidate_resume: candidateInfo.candidate_resume_text || '',  // 配列ではなく結合済みのテキストを使用
              age: candidateInfo.age,
              gender: candidateInfo.gender,
              enrolled_company_count: candidateInfo.enrolled_company_count,
              platform: 'rikunavihrtech',
              client_id: this.sessionInfo.clientId,
              requirement_id: this.sessionInfo.requirementId,
              scraping_session_id: this.sessionInfo.sessionId
            };
            
            this.currentBatch.push(candidateData);
            this.totalScrapedCount++;
            
            // 進捗を通知
            await chrome.runtime.sendMessage({
              type: MESSAGE_TYPES.UPDATE_PROGRESS,
              data: {
                current: this.totalScrapedCount,
                total: cardCount,
                success: this.totalScrapedCount,
                error: 0
              }
            });
            
            // アクションを記録
            ScrapingUtil.sessionManager.recordAction();
            
            // バッチサイズに達したら送信
            if (this.currentBatch.length >= this.config.batchSize) {
              await this.sendBatchData();
            }
          }
          
          // 詳細パネルを閉じる
          await this.closeDetailPanel();
          
          // セッション管理による休憩チェック（カード切り替え時）
          if (i % 20 === 0 && i > 0) {
            const breakCheck = ScrapingUtil.sessionManager.shouldTakeBreak({
              maxDuration: ScrapingUtil.getHumanLikeDelay(20, 0.25), // 15-25分のランダム
              maxActions: Math.floor(ScrapingUtil.getHumanLikeDelay(60, 0.3)), // 40-80アクションのランダム
              breakProbability: 0.1 // 10%の確率でランダム休憩
            });
            
            if (breakCheck.shouldBreak) {
              const breakReason = {
                duration: 'セッション時間が長くなったため',
                actions: 'アクション数が多くなったため',
                random: 'ランダムな休憩タイミング'
              }[breakCheck.reason];
              
              await this.updateProgress({
                status: 'break',
                totalCandidates: this.totalScrapedCount,
                message: `${breakReason}、休憩を取ります...`
              });
              
              await ScrapingUtil.sessionManager.takeBreak({
                minDuration: 300000,  // 最小5分
                maxDuration: 900000,  // 最大15分
                message: 'セッション休憩中'
              });
              
              await this.updateProgress({
                status: 'running',
                totalCandidates: this.totalScrapedCount,
                message: 'スクレイピングを再開しました'
              });
            }
          }
          
          // 次のカードの処理前に人間らしい待機
          await ScrapingUtil.humanLikeWait(800, 1500);
        }
        
      } catch (error) {
        console.error(`❌ カード${i}の処理中にエラー:`, error);
      }
    }
    
    // 残りのバッチデータを送信
    if (this.currentBatch.length > 0) {
      await this.sendBatchData();
    }
    
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(`✅ 完了: ${this.candidates.length}/${cardCount} 件を処理`);
    
    return this.candidates;
  }

  /**
   * カードの総数を取得
   * @returns {number}
   */
  getCardCount() {
    let count = 0;
    for (let i = 1; i <= 100; i++) {
      const xpath = `${this.candidateCardBaseXPath}[${i}]`;
      const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
      if (element) {
        count++;
      } else {
        break;
      }
    }
    return count;
  }

  /**
   * 指定されたインデックスのカードをクリック
   * @param {number} cardIndex
   * @returns {Promise<boolean>}
   */
  async clickCard(cardIndex) {
    const xpath = `${this.candidateCardBaseXPath}[${cardIndex}]`;
    const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    
    if (element) {
      console.log(`✓ カード${cardIndex}をクリック`);
      // 人間らしいクリック
      await ScrapingUtil.humanLikeClick(element);
      // 詳細パネルが完全に開くまで人間らしい待機
      await ScrapingUtil.humanLikeWait(1500, 2500);
      return true;
    } else {
      console.log(`❌ カード${cardIndex}が見つかりません`);
      return false;
    }
  }

  /**
   * 詳細パネルを閉じる
   * @returns {Promise<boolean>}
   */
  async closeDetailPanel() {
    const closeButton = document.evaluate(
      this.closeButtonXPath, 
      document, 
      null, 
      XPathResult.FIRST_ORDERED_NODE_TYPE, 
      null
    ).singleNodeValue;
    
    if (closeButton) {
      console.log('✓ 閉じるボタンをクリック');
      // 人間らしいクリック（少し待ってから閉じる）
      await ScrapingUtil.preClickDelay();
      closeButton.click();
      return true;
    } else {
      console.log('❌ 閉じるボタンが見つかりません');
      return false;
    }
  }

  /**
   * 詳細パネルから候補者情報を抽出
   * @param {number} cardIndex
   * @returns {Object}
   */
  extractCandidateDetail(cardIndex) {
    console.log('📝 詳細情報を抽出中...');
    
    const info = {
      cardIndex: cardIndex,
      timestamp: new Date().toISOString(),
      candidate_company: null,
      candidate_id: null,
      age: null,
      gender: null,  // 性別フィールドを追加
      enrolled_company_count: null,
      candidate_resume: []
    };
    
    try {
      // candidate_company（現在の会社）
      const companyElement = document.evaluate(
        '//*[@id="root"]/div/div[2]/div/div[2]/div[2]/div/div/div[2]',
        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
      ).singleNodeValue;
      if (companyElement) {
        info.candidate_company = companyElement.textContent.trim();
      }
      
      // candidate_id（候補者ID）
      const idElement = document.evaluate(
        '//*[@id="root"]/div/div[2]/div/div[2]/div[1]/div[2]',
        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
      ).singleNodeValue;
      if (idElement) {
        info.candidate_id = idElement.textContent.trim();
      }
      
      // age（年齢）
      const ageElement = document.evaluate(
        '//*[@id="root"]/div/div[2]/div/div[2]/div[2]/div/div/div[3]/div[1]',
        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
      ).singleNodeValue;
      if (ageElement) {
        const ageText = ageElement.textContent.trim();
        // 「XX歳」から数値を抽出
        const ageMatch = ageText.match(/(\d+)/);
        info.age = ageMatch ? parseInt(ageMatch[1]) : null;
      }
      
      // gender（性別）の取得を試みる
      // リクナビHR Techの性別情報の位置は不明なため、暫定的にnullとする
      info.gender = null;
      
      // enrolled_company_count（在籍企業数）
      const companyCountElement = document.evaluate(
        '//*[@id="root"]/div/div[2]/div/div[2]/div[2]/div/div/div[3]/div[3]',
        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
      ).singleNodeValue;
      if (companyCountElement) {
        const countText = companyCountElement.textContent.trim();
        // 「X社」から数値を抽出
        const countMatch = countText.match(/(\d+)/);
        info.enrolled_company_count = countMatch ? parseInt(countMatch[1]) : 0;
      }
      
      // candidate_resume（レジュメ - 複数のセクション）
      const resumeSections = [
        '//*[@id="root"]/div/div[2]/div/div[2]/div[2]',
        '//*[@id="root"]/div/div[2]/div/div[3]',
        '//*[@id="root"]/div/div[2]/div/div[4]',
        '//*[@id="root"]/div/div[2]/div/div[5]',
        '//*[@id="root"]/div/div[2]/div/div[6]',
        '//*[@id="root"]/div/div[2]/div/div[7]'
      ];
      
      resumeSections.forEach((xpath, index) => {
        const element = document.evaluate(
          xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
        ).singleNodeValue;
        
        if (element && element.textContent.trim()) {
          info.candidate_resume.push({
            section: index + 1,
            content: element.textContent.trim()
          });
        }
      });
      
      // レジュメを1つのテキストに結合
      info.candidate_resume_text = info.candidate_resume
        .map(section => section.content)
        .join('\n\n');
      
    } catch (error) {
      console.error('情報抽出中にエラー:', error);
    }
    
    // 取得結果を表示
    console.log(`\n  【取得結果】`);
    console.log(`  ✓ 会社: ${info.candidate_company || '取得失敗'}`);
    console.log(`  ✓ ID: ${info.candidate_id || '取得失敗'}`);
    console.log(`  ✓ 年齢: ${info.age || '取得失敗'}`);
    console.log(`  ✓ 在籍数: ${info.enrolled_company_count || '取得失敗'}`);
    console.log(`  ✓ レジュメ: ${info.candidate_resume.length}セクション取得`);
    
    return info;
  }

  /**
   * リストページから求人情報を抽出（未実装）
   * @returns {Array}
   */
  extractListData() {
    const jobs = [];
    // TODO: 求人リストページの実装
    return jobs;
  }

  /**
   * 詳細ページから求人情報を抽出（未実装）
   * @returns {Object}
   */
  extractDetailData() {
    const data = {
      id: this.extractJobIdFromUrl(),
      title: this.extractText(document, 'h1'),
      company: this.extractText(document, '.company-name'),
      description: this.extractJobDescription(),
      requirements: this.extractRequirements(),
      salary: this.extractSalaryInfo(),
      location: this.extractText(document, '.location'),
      employmentType: this.extractText(document, '.employment-type'),
      benefits: this.extractBenefits(),
      url: window.location.href,
      scrapedAt: new Date().toISOString()
    };
    
    return data;
  }

  /**
   * 求人IDを抽出
   */
  extractJobId(element) {
    // URLやdata属性から求人IDを抽出
    const link = element.querySelector('a');
    if (link) {
      const href = link.getAttribute('href');
      const match = href.match(/JobId=([^&]+)/);
      if (match) {
        return match[1];
      }
    }
    return null;
  }

  /**
   * URLから求人IDを抽出
   */
  extractJobIdFromUrl() {
    const match = window.location.href.match(/JobId=([^&]+)/);
    return match ? match[1] : null;
  }

  /**
   * URLを抽出
   */
  extractUrl(element) {
    const link = element.querySelector('a');
    if (link) {
      const href = link.getAttribute('href');
      // 相対URLの場合は絶対URLに変換
      return href.startsWith('http') ? href : this.baseUrl + href;
    }
    return null;
  }

  /**
   * 職務内容を抽出
   */
  extractJobDescription() {
    // TODO: 実際のセレクタに合わせて調整
    const descElement = document.querySelector('.job-description');
    return descElement ? this.cleanText(descElement.textContent) : '';
  }

  /**
   * 応募要件を抽出
   */
  extractRequirements() {
    // TODO: 実際のセレクタに合わせて調整
    const reqElement = document.querySelector('.requirements');
    return reqElement ? this.cleanText(reqElement.textContent) : '';
  }

  /**
   * 給与情報を抽出
   */
  extractSalaryInfo() {
    // TODO: 実際のセレクタに合わせて調整
    const salaryElement = document.querySelector('.salary-info');
    return salaryElement ? this.cleanText(salaryElement.textContent) : '';
  }

  /**
   * 福利厚生を抽出
   */
  extractBenefits() {
    // TODO: 実際のセレクタに合わせて調整
    const benefitsElement = document.querySelector('.benefits');
    return benefitsElement ? this.cleanText(benefitsElement.textContent) : '';
  }

  /**
   * テキストを抽出（ヘルパーメソッド）
   */
  extractText(context, selector) {
    const element = context.querySelector(selector);
    return element ? this.cleanText(element.textContent) : '';
  }

  /**
   * テキストをクリーンアップ
   */
  cleanText(text) {
    return text
      .replace(/\s+/g, ' ')
      .replace(/\n+/g, '\n')
      .trim();
  }

  /**
   * バッチデータの送信
   */
  async sendBatchData() {
    try {
      console.log('Sending batch data:', this.currentBatch.length, 'candidates');
      console.log('Session info:', this.sessionInfo);
      
      // セッション情報の検証
      if (!this.sessionInfo || !this.sessionInfo.sessionId || !this.sessionInfo.clientId || !this.sessionInfo.requirementId) {
        console.error('Invalid session info:', this.sessionInfo);
        throw new Error('セッション情報が不完全です');
      }
      
      // バックグラウンドスクリプトに送信
      const messageData = {
        candidates: this.currentBatch,
        platform: 'rikunavihrtech',
        sessionId: this.sessionInfo.sessionId,
        clientId: this.sessionInfo.clientId,
        requirementId: this.sessionInfo.requirementId
      };
      
      console.log('Sending message:', messageData);
      console.log('First candidate data:', JSON.stringify(this.currentBatch[0], null, 2));
      
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.SEND_CANDIDATES,
        data: messageData
      });

      console.log('Send candidates response:', response);
      
      if (response && response.success) {
        console.log('Successfully sent', this.currentBatch.length, 'candidates');
        this.candidates.push(...this.currentBatch);
        this.currentBatch = [];
      } else {
        console.error('Failed to send candidates. Full response:', response);
        let errorMessage = 'バッチデータの送信に失敗しました';
        if (response && response.error) {
          if (typeof response.error === 'string') {
            errorMessage = response.error;
          } else if (Array.isArray(response.error)) {
            console.error('Validation error details:', response.error);
            // エラー詳細を詳しく表示
            response.error.forEach((err, index) => {
              console.error(`Error ${index + 1}:`, err);
              if (err.loc) {
                console.error(`  Field path: ${err.loc.join(' -> ')}`);
              }
              if (err.msg) {
                console.error(`  Message: ${err.msg}`);
              }
              if (err.type) {
                console.error(`  Type: ${err.type}`);
              }
            });
            errorMessage = response.error.map(err => 
              `${err.loc ? err.loc.join('.') : 'unknown'}: ${err.msg || err}`
            ).join('\n');
          } else if (typeof response.error === 'object') {
            errorMessage = response.error.message || JSON.stringify(response.error);
          }
        }
        throw new Error(errorMessage);
      }

    } catch (error) {
      console.error('RikunaviHRTechScraper: エラー', error);
      throw error;
    }
  }

  /**
   * 進捗状況を更新
   */
  async updateProgress(progressData) {
    try {
      await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.UPDATE_PROGRESS,
        data: progressData
      });
    } catch (error) {
      // エラーを無視（ポップアップが閉じている場合など）
    }
  }

  /**
   * 一時停止
   */
  pause() {
    this.isPaused = true;
  }

  /**
   * 再開
   */
  resume() {
    this.isPaused = false;
  }

  /**
   * 停止
   */
  stop() {
    this.isRunning = false;
    this.isPaused = false;
  }

  /**
   * ページネーション情報を取得
   */
  getPaginationInfo() {
    // TODO: 実際のページネーション構造に基づいて実装
    return {
      currentPage: 1,
      totalPages: 1,
      hasNext: false,
      nextUrl: null
    };
  }

  /**
   * 次のページに移動
   */
  async goToNextPage() {
    const paginationInfo = this.getPaginationInfo();
    if (paginationInfo.hasNext && paginationInfo.nextUrl) {
      window.location.href = paginationInfo.nextUrl;
      return true;
    }
    return false;
  }
}

// グローバルに公開
window.RikunaviHRTechScraper = RikunaviHRTechScraper;

// エクスポート
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RikunaviHRTechScraper;
}