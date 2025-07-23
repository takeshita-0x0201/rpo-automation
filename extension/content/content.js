// Content Script - メインエントリーポイント

// スクレイピング制御
let isScrapingActive = false;
let scrapingSession = null;
let scraper = null;

// 初期化
async function initialize() {
  // 現在のドメインを確認
  const currentDomain = window.location.hostname;
  
  // BizReachの場合、スクレイパーを初期化
  if (currentDomain.includes('cr-support.jp') || currentDomain.includes('bizreach')) {
    if (typeof BizReachScraper !== 'undefined') {
      scraper = new BizReachScraper();
      await scraper.initialize();
    }
  }
  
  // メッセージリスナーを設定
  setupMessageListener();
}

// メッセージリスナーの設定
function setupMessageListener() {
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    
    switch (request.type) {
      case 'PING':
        sendResponse({ success: true });
        break;
        
      case 'START_SCRAPING':
        handleStartScraping(request.data).then(sendResponse);
        return true; // 非同期レスポンスを示す
        
      case 'PAUSE_SCRAPING':
        handlePauseScraping();
        sendResponse({ success: true });
        break;
        
      case 'RESUME_SCRAPING':
        handleResumeScraping();
        sendResponse({ success: true });
        break;
        
      case 'STOP_SCRAPING':
        handleStopScraping();
        sendResponse({ success: true });
        break;
        
      case 'SCRAPE_CURRENT_PAGE':
        handleScrapeCurrentPage().then(sendResponse);
        return true; // 非同期レスポンスを示す
        
      default:
        sendResponse({ error: 'Unknown message type: ' + request.type });
    }
  });
}

// スクレイピング開始処理
async function handleStartScraping(data) {
  try {
    console.log('handleStartScraping called with:', data);
    
    if (!scraper) {
      throw new Error('スクレイパーが初期化されていません');
    }
    
    // ストレージから最新のセッション情報を取得
    const storageData = await chrome.storage.local.get(['rpo_current_session']);
    console.log('Session from storage:', storageData.rpo_current_session);
    
    // dataとストレージの情報をマージ
    const sessionData = {
      ...data,
      ...(storageData.rpo_current_session || {})
    };
    
    console.log('Merged session data:', sessionData);
    
    isScrapingActive = true;
    scrapingSession = sessionData;
    
    // UIオーバーレイを表示
    showScrapingOverlay();
    
    // スクレイピングを開始（BizReachScraperのstartScrapingメソッドを使用）
    const result = await scraper.startScraping(sessionData);
    
    if (result.success) {
      return { success: true, message: 'スクレイピングを開始しました' };
    } else {
      throw new Error(result.error || 'スクレイピングの開始に失敗しました');
    }
    
  } catch (error) {
    console.error('Scraping error:', error);
    updateOverlayStatus(`エラー: ${error.message}`, 'error');
    return { success: false, error: error.message };
  }
}

// 現在のページのみスクレイピング
async function handleScrapeCurrentPage() {
  try {
    if (!scraper) {
      throw new Error('スクレイパーが初期化されていません');
    }
    
    const result = await scraper.scrapeCurrentPage();
    return result;
    
  } catch (error) {
    console.error('Scrape current page error:', error);
    return { success: false, error: error.message };
  }
}

// スクレイピング一時停止
function handlePauseScraping() {
  isScrapingActive = false;
  updateOverlayStatus('一時停止中', 'paused');
}

// スクレイピング再開
function handleResumeScraping() {
  isScrapingActive = true;
  updateOverlayStatus('再開しました', 'running');
}

// スクレイピング停止
function handleStopScraping() {
  isScrapingActive = false;
  scrapingSession = null;
  hideScrapingOverlay();
}

// UIオーバーレイの表示
function showScrapingOverlay() {
  // 既存のオーバーレイがあれば削除
  const existing = document.querySelector('#rpo-scraping-overlay');
  if (existing) {
    existing.remove();
  }
  
  // オーバーレイを作成
  const overlay = document.createElement('div');
  overlay.id = 'rpo-scraping-overlay';
  overlay.innerHTML = `
    <div class="rpo-overlay-content">
      <div class="rpo-overlay-header">
        <h3>RPO Automation - スクレイピング中</h3>
        <button id="rpo-close-overlay">×</button>
      </div>
      <div class="rpo-overlay-body">
        <div class="rpo-status" id="rpo-status">初期化中...</div>
        <div class="rpo-progress">
          <div class="rpo-progress-bar" id="rpo-progress-bar"></div>
        </div>
        <div class="rpo-stats">
          <span>処理済み: <strong id="rpo-processed">0</strong></span>
          <span>成功: <strong id="rpo-success">0</strong></span>
          <span>エラー: <strong id="rpo-error">0</strong></span>
        </div>
      </div>
    </div>
  `;
  
  // スタイルを追加
  const style = document.createElement('style');
  style.textContent = `
    #rpo-scraping-overlay {
      position: fixed;
      top: 20px;
      right: 20px;
      width: 300px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    .rpo-overlay-content {
      padding: 16px;
    }
    
    .rpo-overlay-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    
    .rpo-overlay-header h3 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }
    
    #rpo-close-overlay {
      background: none;
      border: none;
      font-size: 20px;
      cursor: pointer;
      padding: 0;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .rpo-status {
      font-size: 13px;
      margin-bottom: 8px;
      color: #333;
    }
    
    .rpo-status.error {
      color: #dc3545;
    }
    
    .rpo-status.paused {
      color: #ffc107;
    }
    
    .rpo-progress {
      height: 4px;
      background: #e9ecef;
      border-radius: 2px;
      margin-bottom: 12px;
      overflow: hidden;
    }
    
    .rpo-progress-bar {
      height: 100%;
      background: #007bff;
      width: 0%;
      transition: width 0.3s ease;
    }
    
    .rpo-stats {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #666;
    }
    
    .rpo-stats strong {
      color: #333;
    }
  `;
  
  document.head.appendChild(style);
  document.body.appendChild(overlay);
  
  // 閉じるボタンのイベント
  document.getElementById('rpo-close-overlay').addEventListener('click', () => {
    overlay.style.display = 'none';
  });
}

// オーバーレイの状態更新
function updateOverlayStatus(message, type = 'normal') {
  const statusEl = document.getElementById('rpo-status');
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.className = `rpo-status ${type}`;
  }
}

// オーバーレイの統計更新
function updateOverlayStats(stats) {
  if (stats.processed !== undefined) {
    const el = document.getElementById('rpo-processed');
    if (el) el.textContent = stats.processed;
  }
  
  if (stats.success !== undefined) {
    const el = document.getElementById('rpo-success');
    if (el) el.textContent = stats.success;
  }
  
  if (stats.error !== undefined) {
    const el = document.getElementById('rpo-error');
    if (el) el.textContent = stats.error;
  }
  
  // プログレスバーの更新
  if (stats.progress !== undefined) {
    const bar = document.getElementById('rpo-progress-bar');
    if (bar) bar.style.width = `${stats.progress}%`;
  }
}

// オーバーレイを非表示
function hideScrapingOverlay() {
  const overlay = document.querySelector('#rpo-scraping-overlay');
  if (overlay) {
    overlay.remove();
  }
}

// スクレイピング一時停止処理
function handlePauseScraping() {
  if (scraper && scraper.pause) {
    scraper.pause();
  }
}

// スクレイピング再開処理
function handleResumeScraping() {
  if (scraper && scraper.resume) {
    scraper.resume();
  }
}

// スクレイピング停止処理
function handleStopScraping() {
  if (scraper && scraper.stop) {
    scraper.stop();
  }
  isScrapingActive = false;
  hideScrapingOverlay();
}

// 初期化実行
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}