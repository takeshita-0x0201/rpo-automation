// DOM要素の取得
const elements = {
  // セクション
  loginSection: document.getElementById('loginSection'),
  mainSection: document.getElementById('mainSection'),
  
  // ログインフォーム
  loginForm: document.getElementById('loginForm'),
  emailInput: document.getElementById('email'),
  passwordInput: document.getElementById('password'),
  
  // ステータス
  statusIndicator: document.getElementById('statusIndicator'),
  userName: document.getElementById('userName'),
  
  // クライアント選択
  clientSelect: document.getElementById('clientSelect'),
  
  // 媒体選択
  platformSelect: document.getElementById('platformSelect'),
  
  // 採用要件選択
  requirementGroup: document.getElementById('requirementGroup'),
  requirementSelect: document.getElementById('requirementSelect'),
  
  // ページ数設定
  pageCountGroup: document.getElementById('pageCountGroup'),
  pageCountInput: document.getElementById('pageCountInput'),
  
  // スクレイピング制御
  startBtn: document.getElementById('startBtn'),
  pauseBtn: document.getElementById('pauseBtn'),
  resumeBtn: document.getElementById('resumeBtn'),
  stopBtn: document.getElementById('stopBtn'),
  
  // 進捗表示
  scrapingStatus: document.getElementById('scrapingStatus'),
  statusMessage: document.querySelector('.status-message'),
  progressBar: document.querySelector('.progress-bar'),
  progressFill: document.querySelector('.progress-fill'),
  progressText: document.querySelector('.progress-text'),
  progressCurrent: document.getElementById('progressCurrent'),
  progressTotal: document.getElementById('progressTotal'),
  
  // 統計
  statistics: document.getElementById('statistics'),
  statTotal: document.getElementById('statTotal'),
  statSuccess: document.getElementById('statSuccess'),
  statError: document.getElementById('statError'),
  
  // その他
  errorMessage: document.getElementById('errorMessage'),
  logoutBtn: document.getElementById('logoutBtn'),
  settingsLink: document.getElementById('settingsLink')
};

// 状態管理
let state = {
  isAuthenticated: false,
  user: null,
  clients: [],
  selectedClient: null,
  selectedPlatform: null,
  requirements: [],
  selectedRequirement: null,
  pageCount: 5,
  scrapingStatus: SCRAPING_STATUS.IDLE,
  progress: {
    current: 0,
    total: 0,
    success: 0,
    error: 0
  }
};

// 初期表示用：初期データを読み込む
async function loadInitialData() {
  try {
    // クライアント一覧を読み込み
    await loadClients();
    
    // 媒体プラットフォームを読み込み
    await loadMediaPlatforms();
  } catch (error) {
    DebugUtil.error('Failed to load initial data:', error);
  }
}

// クライアント一覧の読み込み
async function loadClients() {
  try {
    console.log('Loading clients...');
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_CLIENTS
    });
    
    console.log('Clients response:', response);
    
    if (response && response.success && response.clients) {
      state.clients = response.clients;
      
      // selectをクリア
      elements.clientSelect.innerHTML = '<option value="">選択してください</option>';
      
      console.log(`Adding ${response.clients.length} clients to select`);
      
      // クライアントを追加
      response.clients.forEach(client => {
        console.log('Adding client:', client.id, client.name);
        const option = document.createElement('option');
        option.value = client.id;
        option.textContent = client.name;
        elements.clientSelect.appendChild(option);
      });
    } else {
      console.error('Failed to load clients:', response);
      DebugUtil.error('Failed to load clients:', response?.error);
    }
  } catch (error) {
    console.error('Exception in loadClients:', error);
    DebugUtil.error('Failed to load clients:', error);
  }
}

// 媒体プラットフォームの読み込み
async function loadMediaPlatforms() {
  try {
    console.log('Loading media platforms...');
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_MEDIA_PLATFORMS
    });
    
    console.log('Media platforms response:', response);
    
    if (response && response.success && response.platforms) {
      // selectをクリア
      elements.platformSelect.innerHTML = '<option value="">選択してください</option>';
      
      console.log(`Adding ${response.platforms.length} platforms to select`);
      
      // プラットフォームを追加
      response.platforms.forEach(platform => {
        console.log('Adding platform:', platform.name, platform.display_name);
        const option = document.createElement('option');
        option.value = platform.name;
        option.textContent = platform.display_name;
        elements.platformSelect.appendChild(option);
      });
      
      // 現在のタブを確認して、対応する媒体を自動選択
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        // URLパターンマッチング
        for (const platform of response.platforms) {
          if (platform.url_patterns && Array.isArray(platform.url_patterns)) {
            const matched = platform.url_patterns.some(pattern => 
              tab.url.includes(pattern)
            );
            if (matched && elements.platformSelect) {
              elements.platformSelect.value = platform.name;
              state.selectedPlatform = platform.name;
              // 選択が変更されたことを通知
              await handlePlatformSelect({ target: elements.platformSelect });
              break;
            }
          }
        }
      }
    } else {
      console.error('Failed to load media platforms:', response);
      DebugUtil.error('Failed to load media platforms:', response?.error);
    }
  } catch (error) {
    console.error('Exception in loadMediaPlatforms:', error);
    DebugUtil.error('Failed to load media platforms:', error);
  }
}

// 初期化
async function initialize() {
  try {
    DebugUtil.log('Initializing popup...');
    
    // DOM要素の存在チェック
    const requiredElements = ['loginForm', 'platformSelect', 'requirementSelect'];
    for (const elementName of requiredElements) {
      if (!elements[elementName]) {
        console.error(`Required element not found: ${elementName}`);
      }
    }
    
    // 認証状態の確認
    const isAuthenticated = await checkAuthStatus();
    DebugUtil.log('Auth status:', isAuthenticated);
    
    if (isAuthenticated) {
      await loadUserData();
      showMainSection();
      // ログイン後、自動的に初期データを読み込む
      await loadInitialData();
    } else {
      showLoginSection();
    }
    
    // イベントリスナーの設定
    setupEventListeners();
  } catch (error) {
    DebugUtil.error('Initialize error:', error);
    showLoginSection();
  }
}

// 認証状態の確認
async function checkAuthStatus() {
  try {
    // デバッグ: ストレージの内容を確認
    const storageData = await chrome.storage.local.get(['rpo_auth_token', 'rpo_token_expiry']);
    console.log('Storage data check:');
    console.log('- Has token:', !!storageData.rpo_auth_token);
    console.log('- Token expiry:', storageData.rpo_token_expiry);
    console.log('- Expiry date:', storageData.rpo_token_expiry ? new Date(storageData.rpo_token_expiry).toLocaleString() : 'not set');
    console.log('- Current time:', new Date().toLocaleString());
    console.log('- Is expired:', storageData.rpo_token_expiry ? Date.now() > storageData.rpo_token_expiry : 'no expiry set');
    
    const token = await TokenUtil.getToken();
    if (!token) {
      console.log('Token not found or expired');
      return false;
    }
    
    // バックグラウンドスクリプトに認証状態を確認
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_AUTH_STATUS
    });
    
    return response && response.isAuthenticated;
  } catch (error) {
    DebugUtil.error('Auth check failed:', error);
    return false;
  }
}

// ユーザーデータの読み込み
async function loadUserData() {
  try {
    const userInfo = await StorageUtil.get(STORAGE_KEYS.USER_INFO);
    if (userInfo) {
      state.user = userInfo;
      elements.userName.textContent = userInfo.full_name || userInfo.email;
      elements.statusIndicator.classList.add('connected');
      elements.statusIndicator.querySelector('.status-text').textContent = '接続済み';
    }
  } catch (error) {
    DebugUtil.error('Failed to load user data:', error);
  }
}

// 媒体選択処理
async function handlePlatformSelect(e) {
  const platform = e.target.value;
  
  if (!platform) {
    elements.requirementGroup.style.display = 'none';
    state.selectedPlatform = null;
    elements.startBtn.disabled = true;
    return;
  }
  
  state.selectedPlatform = platform;
  
  // プラットフォームに応じてラベルを変更
  updatePageCountLabel(platform);
  
  // 選択したプラットフォームをストレージに保存
  await chrome.storage.local.set({ selected_platform: platform });
  
  // 現在のタブが対応するプラットフォームか確認
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url) {
    const isCorrectPlatform = await checkPlatformMatch(platform, tab.url);
    
    if (!isCorrectPlatform) {
      const platformName = await getPlatformName(platform);
      showError(`現在のページは${platformName}ではありません`);
      elements.requirementGroup.style.display = 'none';
      elements.startBtn.disabled = true;
      return;
    }
  }
  
  // クライアントが選択されている場合は採用要件を読み込み
  if (state.selectedClient) {
    await loadRequirements();
  }
}

// ページ数/カード数のラベルを更新
function updatePageCountLabel(platform) {
  const label = document.getElementById('pageCountLabel');
  const hint = document.getElementById('pageCountHint');
  
  if (!label || !hint) return;
  
  // プラットフォームのURLを取得
  const platformData = state.mediaPlatforms.find(p => p.id === platform);
  const platformUrl = platformData?.url || '';
  
  // リクナビの場合はカード数として表示
  if (platformUrl.includes('rikunabi.com') || platform === 'rikunavihrtech') {
    label.textContent = '取得カード数';
    hint.textContent = '件（1-100）';
  } else {
    label.textContent = '取得ページ数';
    hint.textContent = 'ページ（1-100）';
  }
}

// プラットフォームのマッチング確認
async function checkPlatformMatch(platform, url) {
  try {
    // 媒体プラットフォーム情報を取得
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_MEDIA_PLATFORMS
    });
    
    if (response && response.success && response.platforms) {
      const platformData = response.platforms.find(p => p.name === platform);
      if (platformData && platformData.url_patterns && Array.isArray(platformData.url_patterns)) {
        return platformData.url_patterns.some(pattern => url.includes(pattern));
      }
    }
    
    // フォールバック（デフォルト値）
    switch (platform) {
      case 'bizreach':
        return url.includes('cr-support.jp') || url.includes('bizreach.jp');
      case 'direct':
        return url.includes('directrecruiting.jp');
      case 'green':
        return url.includes('green-japan.com');
      default:
        return false;
    }
  } catch (error) {
    console.error('Failed to check platform match:', error);
    return false;
  }
}

// プラットフォーム名を取得
async function getPlatformName(platform) {
  try {
    // 媒体プラットフォーム情報を取得
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_MEDIA_PLATFORMS
    });
    
    if (response && response.success && response.platforms) {
      const platformData = response.platforms.find(p => p.name === platform);
      if (platformData) {
        return platformData.display_name;
      }
    }
  } catch (error) {
    console.error('Failed to get platform name:', error);
  }
  
  // フォールバック
  const names = {
    'bizreach': 'BizReach',
    'direct': 'Direct Recruiting',
    'green': 'Green'
  };
  return names[platform] || platform;
}

// クライアント選択処理
async function handleClientSelect(e) {
  const clientId = e.target.value;
  
  if (!clientId) {
    state.selectedClient = null;
    // 採用要件をクリア
    elements.requirementSelect.innerHTML = '<option value="">選択してください</option>';
    elements.requirementGroup.style.display = 'none';
    elements.startBtn.disabled = true;
    return;
  }
  
  state.selectedClient = state.clients.find(c => c.id === clientId);
  console.log('Selected client:', state.selectedClient);
  
  // 選択したクライアントをストレージに保存
  await chrome.storage.local.set({ selected_client: state.selectedClient });
  
  // 採用要件を読み込み
  await loadRequirements();
}

// イベントリスナーの設定
function setupEventListeners() {
  // ログインフォーム
  if (elements.loginForm) {
    elements.loginForm.addEventListener('submit', handleLogin);
  }
  
  // ログアウト
  if (elements.logoutBtn) {
    elements.logoutBtn.addEventListener('click', handleLogout);
  }
  
  // クライアント選択
  if (elements.clientSelect) {
    elements.clientSelect.addEventListener('change', handleClientSelect);
  }
  
  // 媒体選択
  if (elements.platformSelect) {
    elements.platformSelect.addEventListener('change', handlePlatformSelect);
  }
  
  // 採用要件選択
  if (elements.requirementSelect) {
    elements.requirementSelect.addEventListener('change', handleRequirementSelect);
  }
  
  // スクレイピング制御
  if (elements.startBtn) {
    elements.startBtn.addEventListener('click', handleStart);
  }
  if (elements.pauseBtn) {
    elements.pauseBtn.addEventListener('click', handlePause);
  }
  if (elements.resumeBtn) {
    elements.resumeBtn.addEventListener('click', handleResume);
  }
  if (elements.stopBtn) {
    elements.stopBtn.addEventListener('click', handleStop);
  }
  
  // ページ数設定
  if (elements.pageCountInput) {
    elements.pageCountInput.addEventListener('change', (e) => {
      state.pageCount = parseInt(e.target.value) || 5;
      // 値の範囲を制限
      if (state.pageCount < 1) state.pageCount = 1;
      if (state.pageCount > 100) state.pageCount = 100;
      e.target.value = state.pageCount;
    });
  }
  
  // 設定リンク
  if (elements.settingsLink) {
    elements.settingsLink.addEventListener('click', (e) => {
      e.preventDefault();
      chrome.runtime.openOptionsPage();
    });
  }
  
  // メッセージリスナー
  chrome.runtime.onMessage.addListener(handleMessage);
}

// ログイン処理
async function handleLogin(e) {
  e.preventDefault();
  
  const email = elements.emailInput.value;
  const password = elements.passwordInput.value;
  
  showLoading(true);
  hideError();
  
  try {
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.LOGIN,
      data: { email, password }
    });
    
    if (response.success) {
      DebugUtil.log('Login successful:', response);
      state.isAuthenticated = true;
      state.user = response.user;
      
      // ユーザー情報を表示
      elements.userName.textContent = response.user.full_name || response.user.email;
      elements.statusIndicator.classList.add('connected');
      elements.statusIndicator.querySelector('.status-text').textContent = '接続済み';
      
      // 画面を切り替え
      showMainSection();
      
      // 初期データを読み込み
      await loadInitialData();
    } else {
      showError(response.error || 'ログインに失敗しました');
    }
  } catch (error) {
    DebugUtil.error('Login failed:', error);
    showError('ログイン処理中にエラーが発生しました');
  } finally {
    showLoading(false);
  }
}

// ログアウト処理
async function handleLogout() {
  try {
    await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.LOGOUT
    });
    
    state.isAuthenticated = false;
    state.user = null;
    state.selectedPlatform = null;
    state.requirements = [];
    state.selectedRequirement = null;
    
    showLoginSection();
  } catch (error) {
    DebugUtil.error('Logout failed:', error);
  }
}


// スクレイピング開始
async function handleStart() {
  if (!state.selectedPlatform) {
    showError('スカウト媒体を選択してください');
    return;
  }
  
  if (!state.selectedRequirement) {
    showError('採用要件を選択してください');
    return;
  }
  
  try {
    console.log('Selected requirement:', state.selectedRequirement);
    console.log('Client ID:', state.selectedRequirement.client_id);
    console.log('Requirement ID:', state.selectedRequirement.id);
    
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.START_SCRAPING,
      data: {
        platform: state.selectedPlatform,
        clientId: state.selectedRequirement.client_id,
        clientName: state.selectedRequirement.client_name || state.selectedRequirement.client?.name,
        requirementId: state.selectedRequirement.id,
        pageLimit: state.pageCount,
        scrape_resume: true // 常時レジュメを取得するよう修正
      }
    });
    
    if (response.success) {
      updateScrapingStatus(SCRAPING_STATUS.RUNNING);
      elements.statistics.style.display = 'block';
    } else {
      showError(response.error || 'スクレイピングの開始に失敗しました');
    }
  } catch (error) {
    DebugUtil.error('Failed to start scraping:', error);
    showError('スクレイピングの開始に失敗しました');
  }
}

// スクレイピング一時停止
async function handlePause() {
  await chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.PAUSE_SCRAPING
  });
  updateScrapingStatus(SCRAPING_STATUS.PAUSED);
}

// スクレイピング再開
async function handleResume() {
  await chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.RESUME_SCRAPING
  });
  updateScrapingStatus(SCRAPING_STATUS.RUNNING);
}

// スクレイピング停止
async function handleStop() {
  await chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.STOP_SCRAPING
  });
  updateScrapingStatus(SCRAPING_STATUS.IDLE);
}

// メッセージハンドラー
function handleMessage(request, sender, sendResponse) {
  switch (request.type) {
    case MESSAGE_TYPES.UPDATE_PROGRESS:
      updateProgress(request.data);
      break;
      
    case MESSAGE_TYPES.SCRAPING_ERROR:
      showError(request.error);
      updateScrapingStatus(SCRAPING_STATUS.ERROR);
      break;
  }
}

// スクレイピング状態の更新
function updateScrapingStatus(status) {
  state.scrapingStatus = status;
  
  // ボタンの表示切り替え
  switch (status) {
    case SCRAPING_STATUS.IDLE:
      elements.startBtn.style.display = 'block';
      elements.pauseBtn.style.display = 'none';
      elements.resumeBtn.style.display = 'none';
      elements.stopBtn.style.display = 'none';
      elements.statusMessage.textContent = '待機中';
      elements.progressBar.style.display = 'none';
      elements.progressText.style.display = 'none';
      break;
      
    case SCRAPING_STATUS.RUNNING:
      elements.startBtn.style.display = 'none';
      elements.pauseBtn.style.display = 'block';
      elements.resumeBtn.style.display = 'none';
      elements.stopBtn.style.display = 'block';
      elements.statusMessage.textContent = '収集中...';
      elements.progressBar.style.display = 'block';
      elements.progressText.style.display = 'block';
      break;
      
    case SCRAPING_STATUS.PAUSED:
      elements.startBtn.style.display = 'none';
      elements.pauseBtn.style.display = 'none';
      elements.resumeBtn.style.display = 'block';
      elements.stopBtn.style.display = 'block';
      elements.statusMessage.textContent = '一時停止中';
      break;
      
    case SCRAPING_STATUS.COMPLETED:
      elements.startBtn.style.display = 'block';
      elements.pauseBtn.style.display = 'none';
      elements.resumeBtn.style.display = 'none';
      elements.stopBtn.style.display = 'none';
      elements.statusMessage.textContent = '完了';
      break;
      
    case SCRAPING_STATUS.ERROR:
      elements.startBtn.style.display = 'block';
      elements.pauseBtn.style.display = 'none';
      elements.resumeBtn.style.display = 'none';
      elements.stopBtn.style.display = 'none';
      elements.statusMessage.textContent = 'エラーが発生しました';
      break;
  }
}

// 進捗の更新
function updateProgress(data) {
  state.progress = data;
  
  elements.progressCurrent.textContent = data.current;
  elements.progressTotal.textContent = data.total;
  elements.statTotal.textContent = data.total;
  elements.statSuccess.textContent = data.success;
  elements.statError.textContent = data.error;
  
  const percentage = data.total > 0 ? (data.current / data.total) * 100 : 0;
  elements.progressFill.style.width = `${percentage}%`;
  
  if (data.current >= data.total && data.total > 0) {
    updateScrapingStatus(SCRAPING_STATUS.COMPLETED);
  }
}

// UI表示制御
function showLoginSection() {
  elements.loginSection.style.display = 'block';
  elements.mainSection.style.display = 'none';
}

function showMainSection() {
  elements.loginSection.style.display = 'none';
  elements.mainSection.style.display = 'block';
}

function showLoading(show) {
  if (show) {
    elements.loginForm.classList.add('loading');
  } else {
    elements.loginForm.classList.remove('loading');
  }
}

function showError(message) {
  elements.errorMessage.textContent = message;
  elements.errorMessage.style.display = 'block';
}

function hideError() {
  elements.errorMessage.style.display = 'none';
}

function enableScrapingControls() {
  if (state.selectedClient && state.selectedRequirement) {
    elements.startBtn.disabled = false;
  }
}

// 採用要件の読み込み（クライアントIDでフィルタリング）
async function loadRequirements() {
  try {
    showLoading(true);
    elements.requirementSelect.innerHTML = '<option value="">選択してください</option>';
    
    if (!state.selectedClient) {
      elements.requirementGroup.style.display = 'none';
      return;
    }
    
    // クライアントIDで採用要件を取得
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_REQUIREMENTS,
      data: { clientId: state.selectedClient.id }
    });
    
    DebugUtil.log('Get requirements response:', response);
    
    if (response && response.success && response.requirements) {
      state.requirements = response.requirements;
      console.log('Loaded requirements for client:', state.selectedClient.name, state.requirements);
      
      // 採用要件セクションを表示
      elements.requirementGroup.style.display = 'flex';
      
      updateRequirementSelect();
    } else if (response && response.error) {
      DebugUtil.error('Failed to load requirements:', response.error);
      showError(response.error);
    }
  } catch (error) {
    DebugUtil.error('Failed to load requirements:', error);
    showError('採用要件の取得に失敗しました');
  } finally {
    showLoading(false);
  }
}

// 採用要件選択肢の更新
function updateRequirementSelect() {
  state.requirements.forEach(requirement => {
    const option = document.createElement('option');
    option.value = requirement.id;
    // タイトルを表示
    const title = requirement.title || '';
    option.textContent = title;
    elements.requirementSelect.appendChild(option);
  });
}

// 採用要件選択処理
async function handleRequirementSelect(e) {
  const requirementId = e.target.value;
  
  if (!requirementId) {
    state.selectedRequirement = null;
    elements.startBtn.disabled = true;
    elements.pageCountGroup.style.display = 'none';
    return;
  }
  
  const requirement = state.requirements.find(r => r.id === requirementId);
  console.log('Finding requirement with ID:', requirementId);
  console.log('Found requirement:', requirement);
  
  if (requirement) {
    state.selectedRequirement = requirement;
    console.log('Selected requirement details:', {
      id: requirement.id,
      client_id: requirement.client_id,
      title: requirement.title,
      client_name: requirement.client_name
    });
    
    // ページ数設定を表示
    elements.pageCountGroup.style.display = 'flex';
    
    // 選択した媒体と現在のタブが一致しているか確認
    if (state.selectedPlatform) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url && await checkPlatformMatch(state.selectedPlatform, tab.url)) {
        elements.startBtn.disabled = false;
      }
    }
  }
}

// メッセージリスナーを設定（進捗更新を受け取る）
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SCRAPING_PROGRESS_UPDATE') {
    updateScrapingProgress(message.data);
  }
});

// スクレイピング進捗を更新
function updateScrapingProgress(progressData) {
  if (progressData.status) {
    // ステータスに応じてUIを更新
    switch (progressData.status) {
      case 'running':
        updateScrapingStatus(SCRAPING_STATUS.RUNNING);
        elements.statusMessage.textContent = progressData.message || '収集中...';
        break;
      case 'paused':
        updateScrapingStatus(SCRAPING_STATUS.PAUSED);
        elements.statusMessage.textContent = progressData.message || '一時停止中';
        break;
      case 'waiting':
      case 'break':
        elements.statusMessage.textContent = progressData.message || '待機中...';
        break;
      case 'completed':
        updateScrapingStatus(SCRAPING_STATUS.COMPLETED);
        elements.statusMessage.textContent = progressData.message || '完了';
        elements.statistics.style.display = 'block';
        break;
      case 'stopped':
        updateScrapingStatus(SCRAPING_STATUS.IDLE);
        elements.statusMessage.textContent = progressData.message || '停止しました';
        break;
      case 'error':
        updateScrapingStatus(SCRAPING_STATUS.ERROR);
        elements.statusMessage.textContent = progressData.message || 'エラーが発生しました';
        break;
    }
  }
  
  // 進捗数値を更新
  if (progressData.totalCandidates !== undefined) {
    elements.progressCurrent.textContent = progressData.totalCandidates;
    elements.progressTotal.textContent = progressData.totalCandidates;
    elements.statTotal.textContent = progressData.totalCandidates;
    elements.statSuccess.textContent = progressData.totalCandidates;
    elements.statError.textContent = '0';
    
    // 統計情報を表示
    if (progressData.totalCandidates > 0) {
      elements.statistics.style.display = 'block';
    }
  }
  
  // 現在のページ番号を表示（メッセージに含まれる）
  if (progressData.currentPage !== undefined && progressData.message) {
    // メッセージはすでにページ情報を含んでいる
  }
}

// ポップアップが開いた時に保存された進捗を読み込む
async function loadSavedProgress() {
  const { scraping_progress } = await chrome.storage.local.get(['scraping_progress']);
  if (scraping_progress && scraping_progress.lastUpdated) {
    // 5分以内の進捗なら表示
    if (Date.now() - scraping_progress.lastUpdated < 5 * 60 * 1000) {
      updateScrapingProgress(scraping_progress);
    }
  }
}

// 初期化実行
document.addEventListener('DOMContentLoaded', () => {
  initialize().then(() => {
    loadSavedProgress();
  });
});