// DOM要素
const elements = {
  // API設定
  apiEndpoint: document.getElementById('apiEndpoint'),
  
  // スクレイピング設定
  batchSize: document.getElementById('batchSize'),
  pageDelay: document.getElementById('pageDelay'),
  retryAttempts: document.getElementById('retryAttempts'),
  
  // デバッグ設定
  debugMode: document.getElementById('debugMode'),
  saveHtml: document.getElementById('saveHtml'),
  
  // 通知設定
  notifyOnComplete: document.getElementById('notifyOnComplete'),
  notifyOnError: document.getElementById('notifyOnError'),
  
  // ボタン
  saveBtn: document.getElementById('saveBtn'),
  resetBtn: document.getElementById('resetBtn'),
  clearCacheBtn: document.getElementById('clearCacheBtn'),
  exportSettingsBtn: document.getElementById('exportSettingsBtn'),
  importSettingsBtn: document.getElementById('importSettingsBtn'),
  importFile: document.getElementById('importFile'),
  
  // メッセージ
  message: document.getElementById('message')
};

// デフォルト設定
const DEFAULT_SETTINGS = {
  apiEndpoint: API_CONFIG.BASE_URL,
  batchSize: SCRAPING_CONFIG.BATCH_SIZE,
  pageDelay: SCRAPING_CONFIG.PAGE_DELAY / 1000, // ミリ秒を秒に変換
  retryAttempts: SCRAPING_CONFIG.RETRY_ATTEMPTS,
  debugMode: DEBUG_CONFIG.ENABLED,
  saveHtml: false,
  notifyOnComplete: true,
  notifyOnError: true
};

// 初期化
async function initialize() {
  await loadSettings();
  setupEventListeners();
}

// 設定の読み込み
async function loadSettings() {
  try {
    const settings = await StorageUtil.get(STORAGE_KEYS.SETTINGS) || {};
    const mergedSettings = { ...DEFAULT_SETTINGS, ...settings };
    
    // フォームに値を設定
    elements.apiEndpoint.value = mergedSettings.apiEndpoint;
    elements.batchSize.value = mergedSettings.batchSize;
    elements.pageDelay.value = mergedSettings.pageDelay;
    elements.retryAttempts.value = mergedSettings.retryAttempts;
    elements.debugMode.checked = mergedSettings.debugMode;
    elements.saveHtml.checked = mergedSettings.saveHtml;
    elements.notifyOnComplete.checked = mergedSettings.notifyOnComplete;
    elements.notifyOnError.checked = mergedSettings.notifyOnError;
  } catch (error) {
    DebugUtil.error('Failed to load settings:', error);
    showMessage('設定の読み込みに失敗しました', 'error');
  }
}

// 設定の保存
async function saveSettings() {
  try {
    const settings = {
      apiEndpoint: elements.apiEndpoint.value,
      batchSize: parseInt(elements.batchSize.value, 10),
      pageDelay: parseInt(elements.pageDelay.value, 10),
      retryAttempts: parseInt(elements.retryAttempts.value, 10),
      debugMode: elements.debugMode.checked,
      saveHtml: elements.saveHtml.checked,
      notifyOnComplete: elements.notifyOnComplete.checked,
      notifyOnError: elements.notifyOnError.checked
    };
    
    // バリデーション
    if (!validateSettings(settings)) {
      return;
    }
    
    await StorageUtil.set(STORAGE_KEYS.SETTINGS, settings);
    
    // バックグラウンドスクリプトに設定変更を通知
    await chrome.runtime.sendMessage({
      type: 'SETTINGS_UPDATED',
      data: settings
    });
    
    showMessage('設定を保存しました', 'success');
  } catch (error) {
    DebugUtil.error('Failed to save settings:', error);
    showMessage('設定の保存に失敗しました', 'error');
  }
}

// 設定のバリデーション
function validateSettings(settings) {
  if (!settings.apiEndpoint) {
    showMessage('APIエンドポイントを入力してください', 'error');
    elements.apiEndpoint.focus();
    return false;
  }
  
  if (settings.batchSize < 1 || settings.batchSize > 100) {
    showMessage('バッチサイズは1-100の範囲で入力してください', 'error');
    elements.batchSize.focus();
    return false;
  }
  
  if (settings.pageDelay < 1 || settings.pageDelay > 60) {
    showMessage('待機時間は1-60秒の範囲で入力してください', 'error');
    elements.pageDelay.focus();
    return false;
  }
  
  if (settings.retryAttempts < 0 || settings.retryAttempts > 10) {
    showMessage('リトライ回数は0-10の範囲で入力してください', 'error');
    elements.retryAttempts.focus();
    return false;
  }
  
  return true;
}

// デフォルトに戻す
async function resetToDefaults() {
  if (confirm('設定をデフォルトに戻しますか？')) {
    await StorageUtil.set(STORAGE_KEYS.SETTINGS, DEFAULT_SETTINGS);
    await loadSettings();
    showMessage('設定をデフォルトに戻しました', 'info');
  }
}

// キャッシュクリア
async function clearCache() {
  if (confirm('キャッシュをクリアしますか？')) {
    try {
      await chrome.storage.local.clear();
      showMessage('キャッシュをクリアしました', 'success');
    } catch (error) {
      DebugUtil.error('Failed to clear cache:', error);
      showMessage('キャッシュのクリアに失敗しました', 'error');
    }
  }
}

// 設定のエクスポート
async function exportSettings() {
  try {
    const settings = await StorageUtil.get(STORAGE_KEYS.SETTINGS) || DEFAULT_SETTINGS;
    const data = JSON.stringify(settings, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rpo-automation-settings-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showMessage('設定をエクスポートしました', 'success');
  } catch (error) {
    DebugUtil.error('Failed to export settings:', error);
    showMessage('設定のエクスポートに失敗しました', 'error');
  }
}

// 設定のインポート
async function importSettings() {
  elements.importFile.click();
}

async function handleFileImport(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  try {
    const text = await file.text();
    const settings = JSON.parse(text);
    
    // バリデーション
    if (!validateSettings(settings)) {
      showMessage('無効な設定ファイルです', 'error');
      return;
    }
    
    await StorageUtil.set(STORAGE_KEYS.SETTINGS, settings);
    await loadSettings();
    showMessage('設定をインポートしました', 'success');
  } catch (error) {
    DebugUtil.error('Failed to import settings:', error);
    showMessage('設定のインポートに失敗しました', 'error');
  }
  
  // ファイル選択をリセット
  elements.importFile.value = '';
}

// メッセージ表示
function showMessage(text, type = 'info') {
  elements.message.textContent = text;
  elements.message.className = `message ${type}`;
  elements.message.style.display = 'block';
  
  setTimeout(() => {
    elements.message.style.display = 'none';
  }, 3000);
}

// イベントリスナーの設定
function setupEventListeners() {
  elements.saveBtn.addEventListener('click', saveSettings);
  elements.resetBtn.addEventListener('click', resetToDefaults);
  elements.clearCacheBtn.addEventListener('click', clearCache);
  elements.exportSettingsBtn.addEventListener('click', exportSettings);
  elements.importSettingsBtn.addEventListener('click', importSettings);
  elements.importFile.addEventListener('change', handleFileImport);
  
  // エンターキーで保存
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      saveSettings();
    }
  });
}

// 初期化実行
document.addEventListener('DOMContentLoaded', initialize);