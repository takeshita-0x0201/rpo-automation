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
    
    try {
      // 現在のページから開始
      await this.scrapeCurrentBatch();
      
      // 自動的に次のページへ進む場合
      if (this.sessionData.auto_pagination) {
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
      
      // レジュメ内容を取得（詳細ページにアクセスが必要な場合）
      if (this.sessionData.scrape_resume) {
        await this.wait(1000); // レート制限対策
        
        // レジュメページを開く
        const resumeResponse = await fetch(data.candidate_link, {
          credentials: 'include',
          headers: {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
          }
        });
        
        if (resumeResponse.ok) {
          const resumeHtml = await resumeResponse.text();
          const parser = new DOMParser();
          const resumeDoc = parser.parseFromString(resumeHtml, 'text/html');
          
          const resumeElement = resumeDoc.querySelector('#jsContainerContents section div div:first-child');
          if (resumeElement) {
            data.candidate_resume = this.cleanText(resumeElement);
          }
        }
      }
      
      // その他の必須フィールド
      data.client_id = this.sessionData.clientId || this.sessionData.client_id;
      data.requirement_id = this.sessionData.requirementId || this.sessionData.requirement_id;
      data.scraped_by = this.sessionData.scraped_by || 'extension';
      data.scraped_at = new Date().toISOString();
      
      console.log('Extracted candidate data:', data);
      
      // 必須フィールドの確認
      const requiredFields = ['candidate_id', 'platform', 'client_id', 'requirement_id'];
      const missingFields = requiredFields.filter(field => !data[field]);
      if (missingFields.length > 0) {
        console.error('Missing required fields:', missingFields);
      }
      
      // データ型の確認
      console.log('Data types check:', {
        candidate_id: typeof data.candidate_id,
        client_id: typeof data.client_id,
        requirement_id: typeof data.requirement_id,
        age: typeof data.age,
        enrolled_company_count: typeof data.enrolled_company_count
      });
      
      // 実際の値も確認
      console.log('Field values:', {
        client_id: data.client_id,
        requirement_id: data.requirement_id
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
    
    // 次へボタンを探す
    const nextButton = this.getElementByXPath('//*[@id="testDrawer"]/div[1]/div/div/div[1]/ul/li[2]/a');
    
    if (nextButton && !nextButton.disabled && !nextButton.classList.contains('disabled')) {
      console.log('Moving to next candidate...');
      
      // クリック前に待機
      await this.wait(this.sessionData.scraping_delay || 2000);
      
      // 次の候補者へ
      nextButton.click();
      
      // ページが更新されるのを待つ
      await this.wait(1500);
      
      // 次の候補者をスクレイピング
      await this.scrapeCurrentBatch();
      
      // 再帰的に続行
      await this.continueScraping();
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
      .replace(/\s+/g, ' ')
      .replace(/[\n\r]+/g, ' ')
      .trim();
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

// 読み込み確認
console.log('OpenWorkScraper loaded successfully');