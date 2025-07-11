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
  
  // 媒体選択
  platformSelect: document.getElementById('platformSelect'),
  
  // 採用要件選択
  requirementGroup: document.getElementById('requirementGroup'),
  requirementSelect: document.getElementById('requirementSelect'),
  requirementDetails: document.getElementById('requirementDetails'),
  clientName: document.getElementById('clientName'),
  requirementPosition: document.getElementById('requirementPosition'),
  requirementSkills: document.getElementById('requirementSkills'),
  
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
  selectedPlatform: null,
  requirements: [],
  selectedRequirement: null,
  scrapingStatus: SCRAPING_STATUS.IDLE,
  progress: {
    current: 0,
    total: 0,
    success: 0,
    error: 0
  }
};

// 初期表示用：全ての採用要件を読み込んで表示
async function loadAllRequirements() {
  try {
    // 採用要件セクションを表示
    if (elements.requirementGroup) {
      elements.requirementGroup.style.display = 'flex'; // ← blockではなくflex
    }
    
    // 採用要件を読み込み
    await loadRequirements();
    
    // 現在のタブを確認して、対応する媒体を自動選択
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      if (tab.url.includes('bizreach.jp') && elements.platformSelect) {
        elements.platformSelect.value = 'bizreach';
        state.selectedPlatform = 'bizreach';
      }
    }
  } catch (error) {
    DebugUtil.error('Failed to load all requirements:', error);
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
      // ログイン後、自動的に採用要件を読み込む
      await loadAllRequirements();
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
    const token = await TokenUtil.getToken();
    if (!token) return false;
    
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
  
  // 選択したプラットフォームをストレージに保存
  await chrome.storage.local.set({ selected_platform: platform });
  
  // 現在のタブが対応するプラットフォームか確認
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url) {
    const isCorrectPlatform = checkPlatformMatch(platform, tab.url);
    
    if (!isCorrectPlatform) {
      showError(`現在のページは${getPlatformName(platform)}ではありません`);
      elements.requirementGroup.style.display = 'none';
      elements.startBtn.disabled = true;
      return;
    }
  }
  
  // 採用要件を読み込み
  elements.requirementGroup.style.display = 'flex'; // ← blockではなくflex
  await loadRequirements();
}

// プラットフォームのマッチング確認
function checkPlatformMatch(platform, url) {
  switch (platform) {
    case 'bizreach':
      return url.includes('cr-support.jp');
    case 'direct':
      return url.includes('directrecruiting.jp');
    case 'green':
      return url.includes('green-japan.com');
    default:
      return false;
  }
}

// プラットフォーム名を取得
function getPlatformName(platform) {
  const names = {
    'bizreach': 'BizReach',
    'direct': 'Direct Recruiting',
    'green': 'Green'
  };
  return names[platform] || platform;
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
      
      // 採用要件を読み込み
      await loadAllRequirements();
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
        requirementId: state.selectedRequirement.id
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

// 採用要件の読み込み（全ての採用要件を取得）
async function loadRequirements() {
  try {
    showLoading(true);
    elements.requirementSelect.innerHTML = '<option value="">選択してください</option>';
    elements.requirementDetails.style.display = 'none';
    
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_ALL_REQUIREMENTS
    });
    
    DebugUtil.log('Get requirements response:', response);
    
    if (response && response.success && response.requirements) {
      state.requirements = response.requirements;
      console.log('Loaded requirements:', state.requirements);
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
    const isActive = requirement.is_active || requirement.status === 'active';
    const status = isActive ? 'アクティブ' : '非アクティブ';
    option.textContent = `${title} (${status})`;
    elements.requirementSelect.appendChild(option);
  });
}

// 採用要件選択処理
async function handleRequirementSelect(e) {
  const requirementId = e.target.value;
  
  if (!requirementId) {
    state.selectedRequirement = null;
    elements.requirementDetails.style.display = 'none';
    elements.startBtn.disabled = true;
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
    
    // 詳細表示
    elements.clientName.textContent = requirement.client_name || requirement.client?.name || '-';
    elements.requirementPosition.textContent = requirement.title || '-';
    
    // structured_dataから必須スキルを取得
    let requiredSkills = '-';
    if (requirement.structured_data) {
      try {
        const data = typeof requirement.structured_data === 'string' 
          ? JSON.parse(requirement.structured_data) 
          : requirement.structured_data;
        requiredSkills = data.required_skills?.join(', ') || '-';
      } catch (e) {
        console.error('Failed to parse structured_data:', e);
      }
    }
    elements.requirementSkills.textContent = requiredSkills;
    elements.requirementDetails.style.display = 'block';
    
    // 選択した媒体と現在のタブが一致しているか確認
    if (state.selectedPlatform) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url && checkPlatformMatch(state.selectedPlatform, tab.url)) {
        elements.startBtn.disabled = false;
      }
    }
  }
}

// 初期化実行
document.addEventListener('DOMContentLoaded', initialize);