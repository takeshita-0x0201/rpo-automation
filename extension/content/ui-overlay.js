// UI オーバーレイモジュール

class UIOverlay {
  constructor() {
    this.overlayElement = null;
    this.shadowRoot = null;
    this.isVisible = false;
    this.progress = {
      current: 0,
      total: 0,
      success: 0,
      error: 0
    };
  }

  // オーバーレイの初期化
  init() {
    if (this.overlayElement) return;

    // オーバーレイコンテナを作成
    this.overlayElement = document.createElement('div');
    this.overlayElement.id = 'rpo-scraping-overlay';
    
    // Shadow DOMを使用してスタイルの競合を防ぐ
    this.shadowRoot = this.overlayElement.attachShadow({ mode: 'open' });
    
    // スタイルとHTMLを設定
    this.shadowRoot.innerHTML = this.getTemplate();
    
    // イベントリスナーを設定
    this.setupEventListeners();
    
    // DOMに追加
    document.body.appendChild(this.overlayElement);
  }

  // テンプレートHTML
  getTemplate() {
    return `
      <style>
        :host {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 999999;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        
        .overlay-container {
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
          width: 320px;
          overflow: hidden;
          transition: all 0.3s ease;
          transform: translateX(340px);
        }
        
        .overlay-container.visible {
          transform: translateX(0);
        }
        
        .overlay-header {
          background: #2c3e50;
          color: white;
          padding: 12px 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .overlay-title {
          font-size: 14px;
          font-weight: 600;
          margin: 0;
        }
        
        .close-button {
          background: none;
          border: none;
          color: white;
          cursor: pointer;
          font-size: 18px;
          line-height: 1;
          opacity: 0.7;
          transition: opacity 0.2s;
        }
        
        .close-button:hover {
          opacity: 1;
        }
        
        .overlay-body {
          padding: 16px;
        }
        
        .status-section {
          margin-bottom: 16px;
        }
        
        .status-label {
          font-size: 12px;
          color: #666;
          margin-bottom: 4px;
        }
        
        .status-value {
          font-size: 14px;
          font-weight: 500;
          color: #2c3e50;
        }
        
        .progress-section {
          margin-bottom: 16px;
        }
        
        .progress-bar {
          height: 6px;
          background: #e0e0e0;
          border-radius: 3px;
          overflow: hidden;
          margin-bottom: 8px;
        }
        
        .progress-fill {
          height: 100%;
          background: #3498db;
          transition: width 0.3s ease;
          position: relative;
        }
        
        .progress-fill::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          bottom: 0;
          right: 0;
          background: linear-gradient(
            45deg,
            rgba(255, 255, 255, 0.2) 25%,
            transparent 25%,
            transparent 50%,
            rgba(255, 255, 255, 0.2) 50%,
            rgba(255, 255, 255, 0.2) 75%,
            transparent 75%,
            transparent
          );
          background-size: 20px 20px;
          animation: progress-animation 1s linear infinite;
        }
        
        @keyframes progress-animation {
          0% {
            background-position: 0 0;
          }
          100% {
            background-position: 20px 20px;
          }
        }
        
        .progress-text {
          font-size: 12px;
          color: #666;
          text-align: center;
        }
        
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          margin-top: 16px;
        }
        
        .stat-item {
          text-align: center;
          padding: 8px;
          background: #f8f9fa;
          border-radius: 4px;
        }
        
        .stat-value {
          font-size: 18px;
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 4px;
        }
        
        .stat-value.success {
          color: #27ae60;
        }
        
        .stat-value.error {
          color: #e74c3c;
        }
        
        .stat-label {
          font-size: 11px;
          color: #666;
        }
        
        .control-buttons {
          display: flex;
          gap: 8px;
          margin-top: 16px;
        }
        
        .btn {
          flex: 1;
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .btn-pause {
          background: #f39c12;
          color: white;
        }
        
        .btn-pause:hover:not(:disabled) {
          background: #e67e22;
        }
        
        .btn-resume {
          background: #00bcd4;
          color: white;
        }
        
        .btn-resume:hover:not(:disabled) {
          background: #00acc1;
        }
        
        .btn-stop {
          background: #e74c3c;
          color: white;
        }
        
        .btn-stop:hover:not(:disabled) {
          background: #c0392b;
        }
        
        .error-message {
          padding: 8px;
          background: #fee;
          border: 1px solid #fcc;
          border-radius: 4px;
          color: #c00;
          font-size: 12px;
          margin-top: 12px;
          display: none;
        }
        
        .error-message.visible {
          display: block;
        }
      </style>
      
      <div class="overlay-container" id="overlayContainer">
        <div class="overlay-header">
          <h3 class="overlay-title">RPO 候補者収集</h3>
          <button class="close-button" id="closeButton">×</button>
        </div>
        
        <div class="overlay-body">
          <div class="status-section">
            <div class="status-label">ステータス</div>
            <div class="status-value" id="statusText">準備中...</div>
          </div>
          
          <div class="progress-section">
            <div class="progress-bar">
              <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
            <div class="progress-text">
              <span id="progressCurrent">0</span> / <span id="progressTotal">0</span> 件
            </div>
          </div>
          
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value" id="statTotal">0</div>
              <div class="stat-label">総数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value success" id="statSuccess">0</div>
              <div class="stat-label">成功</div>
            </div>
            <div class="stat-item">
              <div class="stat-value error" id="statError">0</div>
              <div class="stat-label">エラー</div>
            </div>
          </div>
          
          <div class="control-buttons">
            <button class="btn btn-pause" id="pauseButton">一時停止</button>
            <button class="btn btn-resume" id="resumeButton" style="display: none;">再開</button>
            <button class="btn btn-stop" id="stopButton">停止</button>
          </div>
          
          <div class="error-message" id="errorMessage"></div>
        </div>
      </div>
    `;
  }

  // イベントリスナーの設定
  setupEventListeners() {
    const closeButton = this.shadowRoot.getElementById('closeButton');
    const pauseButton = this.shadowRoot.getElementById('pauseButton');
    const resumeButton = this.shadowRoot.getElementById('resumeButton');
    const stopButton = this.shadowRoot.getElementById('stopButton');
    
    closeButton.addEventListener('click', () => this.hide());
    pauseButton.addEventListener('click', () => this.handlePause());
    resumeButton.addEventListener('click', () => this.handleResume());
    stopButton.addEventListener('click', () => this.handleStop());
  }

  // 表示
  show() {
    this.init();
    setTimeout(() => {
      const container = this.shadowRoot.getElementById('overlayContainer');
      container.classList.add('visible');
      this.isVisible = true;
    }, 100);
  }

  // 非表示
  hide() {
    if (!this.shadowRoot) return;
    
    const container = this.shadowRoot.getElementById('overlayContainer');
    container.classList.remove('visible');
    this.isVisible = false;
  }

  // ステータス更新
  updateStatus(status) {
    if (!this.shadowRoot) return;
    
    const statusText = this.shadowRoot.getElementById('statusText');
    const statusMessages = {
      'idle': '待機中',
      'running': '収集中...',
      'paused': '一時停止中',
      'completed': '完了',
      'error': 'エラーが発生しました'
    };
    
    statusText.textContent = statusMessages[status] || status;
  }

  // 進捗更新
  updateProgress(progress) {
    if (!this.shadowRoot) return;
    
    this.progress = progress;
    
    // 進捗バー
    const progressFill = this.shadowRoot.getElementById('progressFill');
    const percentage = progress.total > 0 ? (progress.current / progress.total) * 100 : 0;
    progressFill.style.width = `${percentage}%`;
    
    // 進捗テキスト
    this.shadowRoot.getElementById('progressCurrent').textContent = progress.current;
    this.shadowRoot.getElementById('progressTotal').textContent = progress.total;
    
    // 統計
    this.shadowRoot.getElementById('statTotal').textContent = progress.total;
    this.shadowRoot.getElementById('statSuccess').textContent = progress.success;
    this.shadowRoot.getElementById('statError').textContent = progress.error;
  }

  // エラー表示
  showError(message) {
    if (!this.shadowRoot) return;
    
    const errorElement = this.shadowRoot.getElementById('errorMessage');
    errorElement.textContent = message;
    errorElement.classList.add('visible');
    
    // 5秒後に自動的に非表示
    setTimeout(() => {
      errorElement.classList.remove('visible');
    }, 5000);
  }

  // 一時停止処理
  handlePause() {
    chrome.runtime.sendMessage({ type: MESSAGE_TYPES.PAUSE_SCRAPING });
    
    const pauseButton = this.shadowRoot.getElementById('pauseButton');
    const resumeButton = this.shadowRoot.getElementById('resumeButton');
    
    pauseButton.style.display = 'none';
    resumeButton.style.display = 'block';
    
    this.updateStatus('paused');
  }

  // 再開処理
  handleResume() {
    chrome.runtime.sendMessage({ type: MESSAGE_TYPES.RESUME_SCRAPING });
    
    const pauseButton = this.shadowRoot.getElementById('pauseButton');
    const resumeButton = this.shadowRoot.getElementById('resumeButton');
    
    pauseButton.style.display = 'block';
    resumeButton.style.display = 'none';
    
    this.updateStatus('running');
  }

  // 停止処理
  handleStop() {
    if (confirm('収集を停止しますか？')) {
      chrome.runtime.sendMessage({ type: MESSAGE_TYPES.STOP_SCRAPING });
      this.updateStatus('idle');
      setTimeout(() => this.hide(), 2000);
    }
  }

  // 完了処理
  complete() {
    this.updateStatus('completed');
    
    // コントロールボタンを無効化
    const buttons = this.shadowRoot.querySelectorAll('.btn');
    buttons.forEach(btn => btn.disabled = true);
    
    // 5秒後に自動的に非表示
    setTimeout(() => this.hide(), 5000);
  }
}

// グローバルに公開
window.uiOverlay = new UIOverlay();