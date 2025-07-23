// BizReach用スクレイピングロジック

class BizReachScraper {
  constructor() {
    this.candidates = [];
    this.currentBatch = [];
    this.config = null;
    this.sessionInfo = null;
  }

  // 初期化
  async initialize() {
    // 設定を取得
    const settings = await StorageUtil.get('settings');
    this.config = {
      batchSize: 1, // 一時的に1に設定してテスト
      pageDelay: settings?.pageDelay || 5000,
      saveHtml: settings?.saveHtml || false
    };
    this.totalScrapedCount = 0; // 総スクレイピング数を追跡
  }

  // メイン処理（ループ版）
  async startScraping(sessionData) {
    try {
      console.log('BizReachScraper.startScraping called with:', sessionData);
      
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
      
      // ページ数制限を設定（デフォルト5ページ）
      const pageLimit = sessionData.pageLimit || 5;
      
      let pageNumber = 1;
      let hasNextPage = true;
      
      // スクレイピング開始を通知
      await this.updateProgress({
        status: 'running',
        currentPage: pageNumber,
        totalCandidates: 0,
        message: `スクレイピングを開始しました（最大${pageLimit}ページ）`
      });
      
      // ページごとにループ処理（ページ数制限付き）
      while (hasNextPage && this.isRunning && pageNumber <= pageLimit) {
        // 一時停止チェック
        while (this.isPaused && this.isRunning) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        if (!this.isRunning) break;
        
        // 現在のページをスクレイピング
        const pageResult = await this.scrapeCurrentPage();
        
        if (!pageResult.success) {
          await this.updateProgress({
            status: 'error',
            currentPage: pageNumber,
            totalCandidates: this.candidates.length,
            message: `エラー: ${pageResult.message}`
          });
          break;
        }
        
        // 10件ごとに休憩
        if (this.totalScrapedCount > 0 && this.totalScrapedCount % 10 === 0) {
          const breakTime = Math.floor(Math.random() * 10000) + 20000; // 20-30秒
          await this.updateProgress({
            status: 'break',
            currentPage: pageNumber,
            totalCandidates: this.candidates.length,
            message: `${Math.floor(breakTime / 1000)}秒間休憩中...`
          });
          await new Promise(resolve => setTimeout(resolve, breakTime));
        }
        
        // 次のページへの遷移（ページ数制限をチェック）
        if (pageNumber < pageLimit) {
          hasNextPage = await this.goToNextPage();
          
          if (hasNextPage) {
            pageNumber++;
            // ページ遷移後の待機時間（5-10秒）
            const waitTime = Math.floor(Math.random() * 5000) + 5000;
            await this.updateProgress({
              status: 'waiting',
              currentPage: pageNumber,
              totalCandidates: this.candidates.length,
              message: `ページ ${pageNumber}/${pageLimit} を読み込み中... (${Math.floor(waitTime / 1000)}秒)`
            });
            await new Promise(resolve => setTimeout(resolve, waitTime));
          }
        } else {
          // ページ数制限に達した
          await this.updateProgress({
            status: 'info',
            currentPage: pageNumber,
            totalCandidates: this.candidates.length,
            message: `ページ数制限（${pageLimit}ページ）に達しました`
          });
          hasNextPage = false;
        }
      }
      
      // 完了通知
      const completionMessage = this.isRunning ? 
        (pageNumber >= pageLimit ? 
          `完了: ${pageNumber}ページから${this.candidates.length}件の候補者を取得しました` :
          `完了: ${this.candidates.length}件の候補者を取得しました`) :
        `停止: ${pageNumber}ページ目で停止（${this.candidates.length}件取得）`;
      
      await this.updateProgress({
        status: this.isRunning ? 'completed' : 'stopped',
        currentPage: pageNumber,
        totalCandidates: this.candidates.length,
        message: completionMessage
      });
      
      return {
        success: true,
        message: `${this.candidates.length}件の候補者データを取得しました`,
        count: this.candidates.length
      };
      
    } catch (error) {
      console.error('BizReachScraper: エラー', error);
      return { success: false, message: error.message };
    }
  }

  // 現在のページをスクレイピング（ループから呼ばれる）
  async scrapeCurrentPage() {
    try {
      // ドロワー形式のUIのため、現在表示中の候補者詳細を取得
      // 通常は1人分のみ表示される
      const resumeElement = document.querySelector('.lapPageInner.ns-drawer-resume') || 
                           document.querySelector('#jsi_resume_page_inner');
      
      if (!resumeElement) {
        return { success: false, message: '候補者情報が表示されていません' };
      }
      
      // ドロワーに表示されている1人の候補者情報を抽出
      const candidateData = await this.extractCandidateData(resumeElement, this.totalScrapedCount);
      
      if (candidateData) {
        this.currentBatch.push(candidateData);
        this.totalScrapedCount++;
        
        // 進捗を通知
        await chrome.runtime.sendMessage({
          type: MESSAGE_TYPES.UPDATE_PROGRESS,
          data: {
            current: this.candidates.length + 1,
            total: this.candidates.length + 1,
            success: this.candidates.length + 1,
            error: 0
          }
        });
        
        // バッチサイズに達したら送信
        if (this.currentBatch.length >= this.config.batchSize) {
          await this.sendBatchData();
        }
        
        // 1人の候補者を正常に抽出
        return { 
          success: true, 
          message: '1件の候補者データを取得しました',
          count: 1
        };
      } else {
        return { 
          success: false, 
          message: '候補者データの抽出に失敗しました'
        };
      }

      // 残りのバッチデータを送信
      if (this.currentBatch.length > 0) {
        await this.sendBatchData();
      }

      // ここには到達しない（上でreturnしているため）

    } catch (error) {
      console.error('BizReachScraper: エラー発生', error);
      return { success: false, message: error.message };
    }
  }

  // 候補者データの抽出
  async extractCandidateData(element, index) {
    try {
      
      // candidate_idの抽出 (resumePageID fl)
      const pageHeader = element.querySelector('.lapPageHeader.cf');
      let candidateId = null;
      if (pageHeader) {
        const resumePageIdElement = pageHeader.querySelector('.resumePageID.fl');
        if (resumePageIdElement) {
          candidateId = resumePageIdElement.textContent.trim();
        }
      }
      
      // 年齢の抽出 (XPath使用)
      let age = null;
      try {
        const ageXPath = '//*[@id="jsi_resume_detail"]/div[3]/ul/li[1]';
        const ageElement = document.evaluate(
          ageXPath, 
          element, 
          null, 
          XPathResult.FIRST_ORDERED_NODE_TYPE, 
          null
        ).singleNodeValue;
        
        if (ageElement) {
          const ageText = ageElement.textContent.trim();
          // "XX歳" のような形式から数値を抽出
          const ageMatch = ageText.match(/(\d+)歳/);
          if (ageMatch) {
            age = parseInt(ageMatch[1]);
          }
        }
      } catch (e) {
        console.warn('年齢の抽出に失敗:', e);
      }
      
      // 性別の抽出 (XPath使用)
      let gender = null;
      try {
        const genderXPath = '//*[@id="jsi_resume_detail"]/div[3]/ul/li[2]';
        const genderElement = document.evaluate(
          genderXPath, 
          element, 
          null, 
          XPathResult.FIRST_ORDERED_NODE_TYPE, 
          null
        ).singleNodeValue;
        
        if (genderElement) {
          const genderText = genderElement.textContent.trim();
          // 性別情報を正規化（M/F）
          if (genderText.includes('男') || genderText.toLowerCase().includes('male')) {
            gender = 'M';
          } else if (genderText.includes('女') || genderText.toLowerCase().includes('female')) {
            gender = 'F';
          } else if (genderText) {
            // その他の場合は最初の1文字を大文字で保存（念のため）
            gender = genderText.charAt(0).toUpperCase();
          }
        }
      } catch (e) {
        console.warn('性別の抽出に失敗:', e);
      }
      
      // 在籍企業数の抽出 (XPath使用)
      let enrolledCompanyCount = 0;
      try {
        const companyListXPath = '//*[@id="jsi_resume_ja_block"]/table/tbody/tr[1]/td/ul';
        const companyListElement = document.evaluate(
          companyListXPath,
          element,
          null,
          XPathResult.FIRST_ORDERED_NODE_TYPE,
          null
        ).singleNodeValue;
        
        if (companyListElement) {
          // li要素の数をカウント
          const liElements = companyListElement.querySelectorAll('li');
          enrolledCompanyCount = liElements.length;
        }
      } catch (e) {
        console.warn('在籍企業数の抽出に失敗:', e);
      }
      
      // candidate_linkの抽出 (data-clipboard-text)
      let candidateLink = null;
      const clipboardElement = element.querySelector('[data-clipboard-text]');
      if (clipboardElement) {
        candidateLink = clipboardElement.getAttribute('data-clipboard-text');
      }
      
      // candidate_companyの抽出 (title="jsi_company_header_name_0_0"の中身)
      let candidateCompany = null;
      // まず、title属性で検索
      const companyElementByTitle = element.querySelector('[title="jsi_company_header_name_0_0"]');
      if (companyElementByTitle) {
        candidateCompany = companyElementByTitle.textContent.trim();
      } else {
        // title属性で見つからない場合は、テーブル内を検索
        const tableElement = element.querySelector('.tblCol2.wf.ns-drawer-resume-table');
        if (tableElement) {
          const companyCell = tableElement.querySelector('[title*="jsi_company_header_name"]');
          if (companyCell) {
            candidateCompany = companyCell.textContent.trim();
          }
        }
      }
      
      // candidate_resumeの抽出 (id="jsi_resume_ja_block" class="resumeView")
      let candidateResume = null;
      // ID で直接検索
      const resumeBlockById = element.querySelector('#jsi_resume_ja_block.resumeView');
      if (resumeBlockById) {
        // レジュメの内容を全て取得
        candidateResume = resumeBlockById.textContent.trim();
      } else {
        // IDで見つからない場合は、別の方法で検索
        const resumeBlock = element.querySelector('.resumeView');
        if (resumeBlock) {
          candidateResume = resumeBlock.textContent.trim();
        }
      }
      
      
      // フォールバック: 必須フィールドが見つからない場合
      if (!candidateId) {
        // URLからIDを抽出を試みる
        candidateId = this.extractCandidateIdFromUrl(candidateLink) || `bizreach_${Date.now()}_${index}`;
      }
      
      if (!candidateLink) {
        // 現在のページURLを使用
        candidateLink = window.location.href;
      }
      
      // platformとrequirement_idは拡張機能の選択内容から取得
      const selectedPlatform = await this.getSelectedPlatform() || 'bizreach';
      const selectedRequirementId = this.sessionInfo.requirementId;
      
      const data = {
        // 必須フィールド
        candidate_id: candidateId,
        candidate_link: candidateLink,
        candidate_company: candidateCompany || '',
        candidate_resume: candidateResume || '', 
        platform: selectedPlatform,
        
        // 追加フィールド
        age: age,
        gender: gender,
        enrolled_company_count: enrolledCompanyCount,
        
        // リレーション情報（APIが要求する必須フィールド）
        client_id: this.sessionInfo.clientId,
        requirement_id: this.sessionInfo.requirementId,
        scraping_session_id: this.sessionInfo.sessionId
      };

      return data;

    } catch (error) {
      console.error(`BizReachScraper: 候補者${index + 1}のデータ抽出エラー`, error);
      return null;
    }
  }

  // 全テキストから追加情報を抽出
  extractFromFullText(data, text) {
    // 年齢の抽出（例：35歳、35才など）
    const ageMatch = text.match(/(\d{2,3})[歳才]/);
    if (ageMatch) {
      data.age = ageMatch[1];
    }

    // 年収の抽出（例：800万円、1,200万円など）
    const salaryMatch = text.match(/([\d,]+)万円/);
    if (salaryMatch) {
      data.current_salary = salaryMatch[1].replace(/,/g, '');
    }

    // 勤続年数の抽出
    const tenureMatch = text.match(/勤続[\s]*(\d+)年/);
    if (tenureMatch) {
      data.tenure_years = tenureMatch[1];
    }

    // 転職回数の抽出
    const jobChangeMatch = text.match(/転職[\s]*(\d+)回/);
    if (jobChangeMatch) {
      data.job_changes = jobChangeMatch[1];
    }

    // 最終ログインの抽出
    const lastLoginMatch = text.match(/最終ログイン[\s:]*([\d\/\-]+)/);
    if (lastLoginMatch) {
      data.last_login = lastLoginMatch[1];
    }

    // 希望勤務地の抽出
    const locationMatch = text.match(/希望勤務地[\s:：]*([\u4e00-\u9fa5]+)/);
    if (locationMatch) {
      data.desired_location = locationMatch[1];
    }

  }

  // テキスト抽出ヘルパー
  extractText(element, selector) {
    const el = element.querySelector(selector);
    return el ? el.textContent.trim() : '';
  }

  // 経験年数の抽出
  extractExperience(element) {
    // 経験年数の要素を探す（セレクタは実際のHTML構造に合わせて調整が必要）
    const expElement = element.querySelector('.js-resume-experience, .experience-years');
    if (expElement) {
      return expElement.textContent.trim();
    }
    
    // テキストから経験年数を抽出
    const text = element.textContent;
    const match = text.match(/(\d+)年/);
    return match ? `${match[1]}年` : '';
  }

  // スキルの抽出
  extractSkills(element) {
    const skills = [];
    
    // スキルタグを探す（セレクタは実際のHTML構造に合わせて調整が必要）
    const skillElements = element.querySelectorAll('.skill-tag, .js-skill, [class*="skill"]');
    skillElements.forEach(el => {
      const skill = el.textContent.trim();
      if (skill && !skills.includes(skill)) {
        skills.push(skill);
      }
    });

    return skills;
  }

  // 学歴の抽出
  extractEducation(element) {
    // 学歴要素を探す（セレクタは実際のHTML構造に合わせて調整が必要）
    const eduElement = element.querySelector('.js-resume-education, .education');
    return eduElement ? eduElement.textContent.trim() : '';
  }

  // 候補者詳細URLの抽出
  extractCandidateUrl(element) {
    // 詳細ページへのリンクを探す
    const linkElement = element.querySelector('a[href*="/resume/"], a[href*="/candidate/"]');
    if (linkElement) {
      const href = linkElement.getAttribute('href');
      // 相対URLの場合は絶対URLに変換
      if (href.startsWith('/')) {
        return `${window.location.origin}${href}`;
      }
      return href;
    }
    
    // リンクが見つからない場合は現在のURLを使用
    return window.location.href;
  }

  // URLからcandidate_idを抽出（フォールバック用）
  extractCandidateIdFromUrl(url) {
    if (!url) return null;
    
    // パターン1: candidate=123456
    const candidateMatch = url.match(/candidate=(\d+)/);
    if (candidateMatch) {
      return candidateMatch[1];
    }
    
    // パターン2: /resume/123456 または /candidate/123456
    const pathMatch = url.match(/\/(resume|candidate)\/(\d+)/);
    if (pathMatch) {
      return pathMatch[2];
    }
    
    // パターン3: その他のIDパターン
    const idMatch = url.match(/id=(\d+)/);
    if (idMatch) {
      return idMatch[1];
    }
    
    return null;
  }
  
  // 選択されたプラットフォームを取得
  async getSelectedPlatform() {
    try {
      // ストレージから選択されたプラットフォームを取得
      const settings = await StorageUtil.get('selected_platform');
      return settings?.selected_platform || 'bizreach';
    } catch (error) {
      console.error('BizReachScraper: プラットフォーム取得エラー', error);
      return 'bizreach';
    }
  }

  // テキストからパターンで抽出
  extractFromPattern(text, pattern) {
    const match = text.match(pattern);
    return match ? match[1] : '';
  }

  // バッチデータの送信
  async sendBatchData() {
    try {
      console.log('Sending batch data:', this.currentBatch.length, 'candidates');
      console.log('Session info:', this.sessionInfo);
      console.log('First candidate data:', this.currentBatch[0]);
      
      // セッション情報の検証
      if (!this.sessionInfo || !this.sessionInfo.sessionId || !this.sessionInfo.clientId || !this.sessionInfo.requirementId) {
        console.error('Invalid session info:', this.sessionInfo);
        throw new Error('セッション情報が不完全です');
      }
      
      // バックグラウンドスクリプトに送信
      const messageData = {
        candidates: this.currentBatch,
        platform: 'bizreach',
        sessionId: this.sessionInfo.sessionId,
        clientId: this.sessionInfo.clientId,
        requirementId: this.sessionInfo.requirementId
      };
      
      console.log('Sending message:', messageData);
      console.log('Candidate data structure:', JSON.stringify(this.currentBatch, null, 2));
      
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
        // エラーの詳細を確認
        let errorMessage = 'バッチデータの送信に失敗しました';
        if (response && response.error) {
          if (typeof response.error === 'string') {
            errorMessage = response.error;
          } else if (Array.isArray(response.error)) {
            console.error('Validation error details:', response.error);
            // エラー配列の内容を詳細にログ出力
            response.error.forEach((err, index) => {
              console.error(`Error ${index + 1}:`, err);
              if (err.loc) {
                console.error(`  Field path: ${err.loc.join(' -> ')}`);
              }
            });
            errorMessage = response.error.join('\n');
          } else if (typeof response.error === 'object') {
            errorMessage = response.error.message || JSON.stringify(response.error);
          }
        }
        throw new Error(errorMessage);
      }

    } catch (error) {
      console.error('BizReachScraper: エラー', error);
      throw error;
    }
  }

  // 次の候補者へ遷移（ドロワーUI）
  async goToNextPage() {
    try {
      // 現在の候補者IDを記録
      const currentCandidateId = this.getCurrentCandidateId();
      
      // XPathで次へボタンを検索（ユーザーが提供したXPath）
      const xpath = '//*[@id="jsi_resume_page_inner"]/div/div[1]/ul/li[2]/a';
      const nextButton = document.evaluate(
        xpath, 
        document, 
        null, 
        XPathResult.FIRST_ORDERED_NODE_TYPE, 
        null
      ).singleNodeValue;
      
      if (!nextButton) {
        // 他の可能性のあるセレクタを試す
        const alternativeSelectors = [
          '[onclick*="LAP.showNext()"]',
          'a[title="次へ"]',
          'a:contains("次へ")',
          '.ns-resume-navigation-next',
          '[class*="next"][class*="button"]',
          'a[href*="next"]'
        ];
        
        let foundButton = null;
        for (const selector of alternativeSelectors) {
          try {
            const button = document.querySelector(selector);
            if (button && !button.disabled && !button.classList.contains('disabled')) {
              foundButton = button;
              break;
            }
          } catch (e) {
            // セレクタエラーを無視
          }
        }
        
        if (!foundButton) {
          return false;
        }
        
        foundButton.click();
      } else {
        // ボタンの状態確認
        if (nextButton.disabled || nextButton.classList.contains('disabled') || nextButton.hasAttribute('disabled')) {
          return false;
        }
        
        nextButton.click();
      }
      
      // ドロワーの内容が更新されるのを待つ
      await this.waitForDrawerUpdate(currentCandidateId);
      
      return true;

    } catch (error) {
      console.error('BizReachScraper: エラー', error);
      return false;
    }
  }
  
  // 現在の候補者IDを取得
  getCurrentCandidateId() {
    const idElement = document.querySelector('.resumePageID');
    return idElement ? idElement.textContent.trim() : null;
  }
  
  // ドロワーの更新を待つ
  async waitForDrawerUpdate(previousCandidateId) {
    return new Promise((resolve) => {
      let checkCount = 0;
      const maxChecks = 30; // 最大3秒待機
      
      const checkInterval = setInterval(() => {
        checkCount++;
        
        // 新しい候補者IDを確認
        const newCandidateId = this.getCurrentCandidateId();
        
        // IDが変わったか、または最大待機時間に達した
        if ((newCandidateId && newCandidateId !== previousCandidateId) || checkCount >= maxChecks) {
          clearInterval(checkInterval);
          // 追加の安定待機時間
          setTimeout(resolve, 1000);
        }
      }, 100);
    });
  }
  
  // ページ遷移を待つ
  async waitForPageTransition(oldUrl) {
    return new Promise((resolve) => {
      let checkCount = 0;
      const maxChecks = 50; // 最大5秒待機
      
      const checkInterval = setInterval(() => {
        checkCount++;
        
        // URL変更またはコンテンツ変更を確認
        const newUrl = window.location.href;
        const newElements = document.querySelectorAll('.lapPageInner.ns-drawer-resume');
        
        // URL が変わったか、新しい要素が読み込まれたか
        if (newUrl !== oldUrl || newElements.length > 0 || checkCount >= maxChecks) {
          clearInterval(checkInterval);
          // 追加の安定待機時間
          setTimeout(resolve, 1500);
        }
      }, 100);
    });
  }

  // ページ読み込み待機
  async waitForPageLoad() {
    return new Promise((resolve) => {
      let checkCount = 0;
      const maxChecks = 30; // 最大15秒待機
      
      const checkInterval = setInterval(() => {
        checkCount++;
        
        // 新しい候補者要素が読み込まれたかチェック
        const elements = document.querySelectorAll('.lapPageInner.ns-drawer-resume');
        
        if (elements.length > 0 || checkCount >= maxChecks) {
          clearInterval(checkInterval);
          // 追加の待機時間
          setTimeout(resolve, 1000);
        }
      }, 500);
    });
  }

  // 統計情報の取得
  getStatistics() {
    return {
      total: this.candidates.length,
      currentBatch: this.currentBatch.length
    };
  }
  
  // 進捗状況を更新
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
  
  // 一時停止
  pause() {
    this.isPaused = true;
  }
  
  // 再開
  resume() {
    this.isPaused = false;
  }
  
  // 停止
  stop() {
    this.isRunning = false;
    this.isPaused = false;
  }
}

// グローバルに公開
window.BizReachScraper = BizReachScraper;