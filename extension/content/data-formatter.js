// データ整形モジュール

class DataFormatter {
  constructor() {
    this.requiredFields = [
      'name',
      'current_company',
      'current_position',
      'bizreach_url'
    ];
  }

  // 候補者データを整形
  formatCandidate(rawData) {
    try {
      const formatted = {
        // 基本情報
        name: this.cleanText(rawData.name || ''),
        email: this.extractEmail(rawData.email || rawData.contact || ''),
        phone: this.formatPhoneNumber(rawData.phone || ''),
        
        // 現在の職務
        current_company: this.cleanText(rawData.current_company || rawData.company || ''),
        current_position: this.cleanText(rawData.current_position || rawData.position || rawData.title || ''),
        
        // 経験・スキル
        experience_years: this.parseExperienceYears(rawData.experience || rawData.years || ''),
        skills: this.extractSkills(rawData.skills || []),
        
        // 学歴
        education: this.formatEducation(rawData.education || rawData.school || ''),
        
        // Bizreach情報
        bizreach_url: rawData.url || rawData.bizreach_url || window.location.href,
        
        // メタデータ
        scraped_at: new Date().toISOString(),
        raw_html: rawData.html || '',
        
        // 採用要件との紐付け
        requirement_id: rawData.requirement_id || null,
        session_id: rawData.session_id || null,
        client_id: rawData.client_id || null
      };

      // 必須フィールドの検証
      const isValid = this.validateCandidate(formatted);
      if (!isValid) {
        console.warn('Invalid candidate data:', formatted);
        return null;
      }

      return formatted;
    } catch (error) {
      console.error('Error formatting candidate:', error);
      return null;
    }
  }

  // 複数の候補者データを整形
  formatCandidates(rawDataArray) {
    return rawDataArray
      .map(data => this.formatCandidate(data))
      .filter(candidate => candidate !== null);
  }

  // テキストのクリーニング
  cleanText(text) {
    if (!text) return '';
    
    return text
      .replace(/\s+/g, ' ') // 連続する空白を1つに
      .replace(/[\n\r\t]/g, ' ') // 改行・タブをスペースに
      .trim();
  }

  // メールアドレスの抽出
  extractEmail(text) {
    if (!text) return '';
    
    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
    const match = text.match(emailRegex);
    return match ? match[0] : '';
  }

  // 電話番号のフォーマット
  formatPhoneNumber(phone) {
    if (!phone) return '';
    
    // 数字以外を削除
    const numbers = phone.replace(/\D/g, '');
    
    // 日本の電話番号形式にフォーマット
    if (numbers.length === 10) {
      return numbers.replace(/(\d{3})(\d{4})(\d{3})/, '$1-$2-$3');
    } else if (numbers.length === 11) {
      return numbers.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3');
    }
    
    return phone;
  }

  // 経験年数のパース
  parseExperienceYears(text) {
    if (!text) return 0;
    
    // 数字を抽出
    const numbers = text.match(/\d+/g);
    if (numbers && numbers.length > 0) {
      return parseInt(numbers[0], 10);
    }
    
    // テキストから推測
    const patterns = {
      '新卒': 0,
      '1年未満': 0,
      '1年以上': 1,
      '3年以上': 3,
      '5年以上': 5,
      '10年以上': 10,
      '15年以上': 15,
      '20年以上': 20
    };
    
    for (const [pattern, years] of Object.entries(patterns)) {
      if (text.includes(pattern)) {
        return years;
      }
    }
    
    return 0;
  }

  // スキルの抽出
  extractSkills(skills) {
    if (Array.isArray(skills)) {
      return skills.map(skill => this.cleanText(skill)).filter(skill => skill);
    }
    
    if (typeof skills === 'string') {
      // カンマ、スラッシュ、中黒で分割
      return skills
        .split(/[,、\/・]/)
        .map(skill => this.cleanText(skill))
        .filter(skill => skill && skill.length > 1);
    }
    
    return [];
  }

  // 学歴のフォーマット
  formatEducation(education) {
    if (!education) return '';
    
    // 最終学歴のみを抽出する簡単な処理
    const cleaned = this.cleanText(education);
    
    // 大学名が含まれる場合は抽出
    const universityMatch = cleaned.match(/([^大学]*大学[^卒業]*)/);
    if (universityMatch) {
      return universityMatch[0];
    }
    
    return cleaned;
  }

  // 候補者データの検証
  validateCandidate(candidate) {
    // 必須フィールドが存在するか
    for (const field of this.requiredFields) {
      if (!candidate[field]) {
        console.warn(`Missing required field: ${field}`);
        return false;
      }
    }
    
    // 名前が有効か
    if (candidate.name.length < 2) {
      console.warn('Invalid name length');
      return false;
    }
    
    // URLが有効か
    try {
      new URL(candidate.bizreach_url);
    } catch {
      console.warn('Invalid URL');
      return false;
    }
    
    return true;
  }

  // 採用要件との紐付け情報を追加
  addRequirementContext(candidate, requirementId, sessionId, clientId) {
    return {
      ...candidate,
      requirement_id: requirementId,
      session_id: sessionId,
      client_id: clientId,
      matched_at: new Date().toISOString()
    };
  }

  // バッチデータの準備
  prepareBatchData(candidates, batchSize = 10) {
    const batches = [];
    
    for (let i = 0; i < candidates.length; i += batchSize) {
      batches.push(candidates.slice(i, i + batchSize));
    }
    
    return batches;
  }

  // エラーレポートの整形
  formatError(error, context = {}) {
    return {
      message: error.message || String(error),
      stack: error.stack || '',
      timestamp: new Date().toISOString(),
      context: {
        url: window.location.href,
        ...context
      }
    };
  }
}

// グローバルに公開
window.dataFormatter = new DataFormatter();