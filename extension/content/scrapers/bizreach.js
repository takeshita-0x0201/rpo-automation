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
    console.log('BizReachScraper: 初期化開始');
    
    // 設定を取得
    const settings = await StorageUtil.get('settings');
    this.config = {
      batchSize: settings?.batchSize || 10,
      pageDelay: settings?.pageDelay || 5000,
      saveHtml: settings?.saveHtml || false
    };
    
    console.log('BizReachScraper: 設定読み込み完了', this.config);
  }

  // メイン処理（ループなし版）
  async scrapeCurrentPage() {
    try {
      console.log('BizReachScraper: 現在のページをスクレイピング開始');
      
      // セッション情報を取得
      const sessionData = await StorageUtil.get('rpo_current_session');
      if (!sessionData) {
        throw new Error('セッション情報が見つかりません');
      }
      
      this.sessionInfo = sessionData;
      console.log('BizReachScraper: セッション情報:', this.sessionInfo);
      
      // lapPageInner要素を全て取得
      const resumeElements = document.querySelectorAll('.lapPageInner.ns-drawer-resume');
      console.log(`BizReachScraper: ${resumeElements.length}件の候補者を検出`);
      
      if (resumeElements.length === 0) {
        console.log('BizReachScraper: 候補者が見つかりません');
        return { success: false, message: '候補者が見つかりません' };
      }
      
      // 進捗の総数を通知
      await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.UPDATE_PROGRESS,
        data: {
          current: 0,
          total: resumeElements.length,
          success: 0,
          error: 0
        }
      });

      // 各候補者の情報を抽出
      for (let i = 0; i < resumeElements.length; i++) {
        const element = resumeElements[i];
        const candidateData = await this.extractCandidateData(element, i);
        
        if (candidateData) {
          this.currentBatch.push(candidateData);
          console.log(`BizReachScraper: 候補者 ${i + 1}/${resumeElements.length} を抽出完了`);
        }
      }

      // バッチデータを送信
      if (this.currentBatch.length > 0) {
        await this.sendBatchData();
      }

      console.log('BizReachScraper: スクレイピング完了');
      return { 
        success: true, 
        message: `${this.currentBatch.length}件の候補者データを取得しました`,
        count: this.currentBatch.length
      };

    } catch (error) {
      console.error('BizReachScraper: エラー発生', error);
      return { success: false, message: error.message };
    }
  }

  // 候補者データの抽出
  async extractCandidateData(element, index) {
    try {
      console.log(`BizReachScraper: 候補者${index + 1}のデータ抽出開始`);
      
      // デバッグ用: 要素の構造を確認
      console.log('BizReachScraper: Element structure:', {
        hasLapPageHeader: !!element.querySelector('.lapPageHeader.cf'),
        hasDataClipboard: !!element.querySelector('[data-clipboard-text]'),
        hasTitleAttribute: !!element.querySelector('[title="jsi_company_header_name_0_0"]'),
        hasResumeTable: !!element.querySelector('.tblCol2.wf.ns-drawer-resume-table'),
        hasResumeBlockById: !!element.querySelector('#jsi_resume_ja_block'),
        hasResumeView: !!element.querySelector('.resumeView')
      });
      
      // candidate_idの抽出 (resumePageID fl)
      const pageHeader = element.querySelector('.lapPageHeader.cf');
      let candidateId = null;
      if (pageHeader) {
        const resumePageIdElement = pageHeader.querySelector('.resumePageID.fl');
        if (resumePageIdElement) {
          candidateId = resumePageIdElement.textContent.trim();
          console.log(`BizReachScraper: candidate_id found: ${candidateId}`);
        }
      }
      
      // candidate_linkの抽出 (data-clipboard-text)
      let candidateLink = null;
      const clipboardElement = element.querySelector('[data-clipboard-text]');
      if (clipboardElement) {
        candidateLink = clipboardElement.getAttribute('data-clipboard-text');
        console.log(`BizReachScraper: candidate_link found: ${candidateLink}`);
      }
      
      // candidate_companyの抽出 (title="jsi_company_header_name_0_0"の中身)
      let candidateCompany = null;
      // まず、title属性で検索
      const companyElementByTitle = element.querySelector('[title="jsi_company_header_name_0_0"]');
      if (companyElementByTitle) {
        candidateCompany = companyElementByTitle.textContent.trim();
        console.log(`BizReachScraper: candidate_company found by title: ${candidateCompany}`);
      } else {
        // title属性で見つからない場合は、テーブル内を検索
        const tableElement = element.querySelector('.tblCol2.wf.ns-drawer-resume-table');
        if (tableElement) {
          const companyCell = tableElement.querySelector('[title*="jsi_company_header_name"]');
          if (companyCell) {
            candidateCompany = companyCell.textContent.trim();
            console.log(`BizReachScraper: candidate_company found in table: ${candidateCompany}`);
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
        console.log(`BizReachScraper: candidate_resume full length: ${candidateResume.length} characters`);
      } else {
        // IDで見つからない場合は、別の方法で検索
        const resumeBlock = element.querySelector('.resumeView');
        if (resumeBlock) {
          candidateResume = resumeBlock.textContent.trim();
          console.log(`BizReachScraper: candidate_resume found by class, length: ${candidateResume.length} characters`);
        }
      }
      
      // レジュメが非常に長い場合の警告（10000文字以上）
      if (candidateResume && candidateResume.length > 10000) {
        console.warn(`BizReachScraper: Very long resume detected (${candidateResume.length} characters)`);
        // 必要に応じて、ここで適切な上限を設定することも可能
        // candidateResume = candidateResume.substring(0, 10000) + '\n...[省略]';
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
        candidate_company: candidateCompany || '不明',
        candidate_resume: candidateResume || candidateLink, // レジュメがない場合はリンクを使用
        
        // プラットフォーム情報（拡張機能で選択された内容）
        platform: selectedPlatform,
        
        // リレーション情報
        client_id: this.sessionInfo.clientId,
        requirement_id: selectedRequirementId,
        scraping_session_id: this.sessionInfo.sessionId,
        
        // メタデータ
        scraped_at: new Date().toISOString()
      };

      console.log('BizReachScraper: 抽出データ:', data);
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

    console.log('BizReachScraper: 追加抽出データ:', {
      age: data.age,
      current_salary: data.current_salary,
      tenure_years: data.tenure_years,
      job_changes: data.job_changes,
      last_login: data.last_login,
      desired_location: data.desired_location
    });
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
      console.log('BizReachScraper: バッチデータ送信開始', this.currentBatch.length + '件');
      
      // セッション情報を取得
      const sessionData = await StorageUtil.get('rpo_current_session');
      
      // バックグラウンドスクリプトに送信
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.SEND_CANDIDATES,
        data: {
          candidates: this.currentBatch,
          platform: 'bizreach',
          sessionId: sessionData?.sessionId
        }
      });

      if (response.success) {
        console.log('BizReachScraper: バッチデータ送信成功');
        this.candidates.push(...this.currentBatch);
        this.currentBatch = [];
      } else {
        throw new Error(response.error || 'バッチデータの送信に失敗しました');
      }

    } catch (error) {
      console.error('BizReachScraper: バッチデータ送信エラー', error);
      throw error;
    }
  }

  // 次のページボタンをクリック（将来のループ処理用）
  async clickNextPage() {
    try {
      // 次へボタンを探す
      const nextButton = document.querySelector('[onclick*="LAP.showNext()"]');
      
      if (!nextButton) {
        console.log('BizReachScraper: 次のページボタンが見つかりません');
        return false;
      }

      // ボタンが無効化されているかチェック
      if (nextButton.disabled || nextButton.classList.contains('disabled')) {
        console.log('BizReachScraper: 最後のページに到達しました');
        return false;
      }

      console.log('BizReachScraper: 次のページへ移動');
      nextButton.click();
      
      // ページの読み込みを待つ
      await this.waitForPageLoad();
      
      return true;

    } catch (error) {
      console.error('BizReachScraper: 次ページ遷移エラー', error);
      return false;
    }
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
}

// グローバルに公開
window.BizReachScraper = BizReachScraper;