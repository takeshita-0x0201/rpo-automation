// Service Worker - Chrome拡張機能のバックグラウンド処理

// APIクライアントをインポート（importScriptsを使用）
importScripts('./api-client.js');

// 状態管理
let authState = {
  isAuthenticated: false,
  token: null,
  user: null
};

let scrapingState = {
  status: 'idle',
  sessionId: null,
  clientId: null,
  clientName: null,
  requirementId: null,
  progress: {
    current: 0,
    total: 0,
    success: 0,
    error: 0
  }
};

// Service Workerの起動時に初期化
chrome.runtime.onInstalled.addListener(async () => {
  console.log('RPO Automation Extension installed');
  
  // 初期化処理
  await initializeExtension();
});

// Service Workerの起動時にも初期化（既にインストール済みの場合）
initializeExtension();

// 初期化
async function initializeExtension() {
  // 保存されているトークンを確認
  const token = await getStoredToken();
  if (token) {
    authState.isAuthenticated = true;
    authState.token = token;
    
    // ユーザー情報も復元
    const userInfo = await chrome.storage.local.get('rpo_user_info');
    if (userInfo.rpo_user_info) {
      authState.user = userInfo.rpo_user_info;
    }
  }
}

// メッセージリスナー
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // 非同期処理のためにtrueを返す
  handleMessage(request, sender).then(sendResponse);
  return true;
});

// メッセージハンドラー
async function handleMessage(request, sender) {
  console.log('Background received message:', request.type);
  
  switch (request.type) {
    case 'GET_AUTH_STATUS':
      return { isAuthenticated: authState.isAuthenticated, user: authState.user };
    
    case 'LOGIN':
      return await handleLogin(request.data);
    
    case 'LOGOUT':
      return await handleLogout();
    
    case 'GET_CLIENTS':
      return await getClients();
    
    case 'GET_REQUIREMENTS':
      return await getRequirements(request.data);
    
    case 'GET_ALL_REQUIREMENTS':
      return await getAllRequirements();
    
    case 'GET_REQUIREMENT':
      return await getRequirement(request.data);
    
    case 'START_SCRAPING':
      return await startScraping(request.data);
    
    case 'PAUSE_SCRAPING':
      return await pauseScraping();
    
    case 'RESUME_SCRAPING':
      return await resumeScraping();
    
    case 'STOP_SCRAPING':
      return await stopScraping();
    
    case 'SEND_CANDIDATES':
      return await sendCandidates(request.data);
    
    case 'SAVE_CANDIDATES':
      return await saveCandidates(request.data);
    
    case 'UPDATE_PROGRESS':
      return await updateProgress(request.data);
    
    default:
      return { error: 'Unknown message type' };
  }
}

// ログイン処理
async function handleLogin({ email, password }) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/auth/extension/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) {
      const error = await response.json();
      return { success: false, error: error.detail || 'ログインに失敗しました' };
    }
    
    const data = await response.json();
    
    // トークンと有効期限を保存
    await chrome.storage.local.set({
      rpo_auth_token: data.access_token,
      rpo_token_expiry: Date.now() + (30 * 60 * 1000), // 30分
      rpo_user_info: data.user
    });
    
    authState.isAuthenticated = true;
    authState.token = data.access_token;
    authState.user = data.user;
    
    return { success: true, user: data.user };
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, error: 'ネットワークエラーが発生しました' };
  }
}

// ログアウト処理
async function handleLogout() {
  try {
    // ストレージをクリア
    await chrome.storage.local.remove([
      'rpo_auth_token',
      'rpo_token_expiry',
      'rpo_user_info',
      'rpo_selected_client',
      'rpo_current_session'
    ]);
    
    authState.isAuthenticated = false;
    authState.token = null;
    authState.user = null;
    
    return { success: true };
  } catch (error) {
    console.error('Logout error:', error);
    return { success: false, error: 'ログアウトに失敗しました' };
  }
}

// クライアント一覧取得
async function getClients() {
  try {
    const clients = await apiClient.getClients();
    return { success: true, clients };
  } catch (error) {
    console.error('Get clients error:', error);
    // ApiErrorクラスが利用できない場合も考慮
    const isAuthError = (error instanceof ApiError && error.isAuthError()) || 
                       error.status === 401 || 
                       error.code === 'AUTH_FAILED';
    
    if (isAuthError) {
      authState.isAuthenticated = false;
      return { success: false, error: '認証の有効期限が切れました' };
    }
    return { success: false, error: error.message || 'クライアント一覧の取得に失敗しました' };
  }
}

// 採用要件取得（クライアント指定）
async function getRequirements({ clientId }) {
  try {
    if (!clientId) {
      return { success: false, error: 'クライアントIDが指定されていません' };
    }
    
    const requirements = await apiClient.getRequirements(clientId);
    return { success: true, requirements };
  } catch (error) {
    console.error('Get requirements error:', error);
    return { success: false, error: 'ネットワークエラーが発生しました' };
  }
}

// 全ての採用要件を取得
async function getAllRequirements() {
  try {
    console.log('Fetching all requirements...');
    console.log('Auth state:', authState);
    console.log('API client available:', typeof apiClient !== 'undefined');
    console.log('ApiError available:', typeof ApiError !== 'undefined');
    
    const requirements = await apiClient.getAllRequirements();
    console.log('Requirements fetched successfully:', requirements);
    return { success: true, requirements };
  } catch (error) {
    console.error('Get all requirements error:', error);
    console.error('Error type:', error.constructor.name);
    console.error('Error status:', error.status);
    console.error('Error code:', error.code);
    
    // ApiErrorクラスが利用できない場合も考慮
    const isAuthError = (error instanceof ApiError && error.isAuthError()) || 
                       error.status === 401 || 
                       error.code === 'AUTH_FAILED';
    
    if (isAuthError) {
      authState.isAuthenticated = false;
      return { success: false, error: '認証の有効期限が切れました' };
    }
    return { success: false, error: error.message || '採用要件の取得に失敗しました' };
  }
}

// 採用要件詳細取得
async function getRequirement({ requirementId }) {
  try {
    if (!requirementId) {
      return { success: false, error: '採用要件IDが指定されていません' };
    }
    
    const requirement = await apiClient.getRequirement(requirementId);
    return { success: true, requirement };
  } catch (error) {
    console.error('Get requirement error:', error);
    return { success: false, error: 'ネットワークエラーが発生しました' };
  }
}

// スクレイピング開始
async function startScraping({ clientId, clientName, requirementId }) {
  try {
    console.log('Starting scraping session:', { clientId, clientName, requirementId });
    console.log('Auth token available:', !!authState.token);
    
    // セッション開始APIを呼び出し
    const response = await fetch(`${getApiBaseUrl()}/api/extension/scraping/start`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        client_id: clientId,
        requirement_id: requirementId
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      console.error('Session start failed:', response.status, errorData);
      return { success: false, error: errorData.detail || 'セッションの開始に失敗しました' };
    }
    
    const data = await response.json();
    
    // スクレイピング状態を更新
    scrapingState.status = 'running';
    scrapingState.sessionId = data.session_id;
    scrapingState.clientId = clientId;
    scrapingState.clientName = clientName;
    scrapingState.requirementId = requirementId;
    scrapingState.progress = {
      current: 0,
      total: 0,
      success: 0,
      error: 0
    };
    
    // ストレージに保存
    await chrome.storage.local.set({
      rpo_current_session: {
        sessionId: data.session_id,
        clientId: clientId,
        requirementId: requirementId,
        status: 'running'
      }
    });
    
    // コンテンツスクリプトに開始を通知
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      try {
        // まずcontent scriptがロードされているか確認
        await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
      } catch (e) {
        // content scriptがロードされていない場合は手動でインジェクト
        console.log('Content script not loaded, injecting...');
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: [
            'shared/constants.js',
            'shared/utils.js',
            'content/scrapers/bizreach.js',
            'content/content.js'
          ]
        });
        // インジェクト後少し待つ
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      // メッセージ送信
      try {
        await chrome.tabs.sendMessage(tab.id, {
          type: 'START_SCRAPING',
          data: {
            sessionId: data.session_id,
            clientId: clientId,
            requirementId: requirementId
          }
        });
      } catch (error) {
        console.error('Failed to send message to content script:', error);
        throw new Error('コンテンツスクリプトとの通信に失敗しました');
      }
    }
    
    return { success: true, sessionId: data.session_id };
  } catch (error) {
    console.error('Start scraping error:', error);
    return { success: false, error: error.message || 'スクレイピングの開始に失敗しました' };
  }
}

// スクレイピング一時停止
async function pauseScraping() {
  scrapingState.status = 'paused';
  
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    await chrome.tabs.sendMessage(tab.id, { type: 'PAUSE_SCRAPING' });
  }
  
  return { success: true };
}

// スクレイピング再開
async function resumeScraping() {
  scrapingState.status = 'running';
  
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    await chrome.tabs.sendMessage(tab.id, { type: 'RESUME_SCRAPING' });
  }
  
  return { success: true };
}

// スクレイピング停止
async function stopScraping() {
  try {
    // セッション完了APIを呼び出し
    if (scrapingState.sessionId) {
      await fetch(`${getApiBaseUrl()}/api/extension/scraping/end`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authState.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: scrapingState.sessionId
        })
      });
    }
    
    // 状態をリセット
    scrapingState.status = 'idle';
    scrapingState.sessionId = null;
    scrapingState.clientId = null;
    
    // ストレージから削除
    await chrome.storage.local.remove('rpo_current_session');
    
    // コンテンツスクリプトに停止を通知
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      await chrome.tabs.sendMessage(tab.id, { type: 'STOP_SCRAPING' });
    }
    
    return { success: true };
  } catch (error) {
    console.error('Stop scraping error:', error);
    return { success: false, error: 'スクレイピングの停止に失敗しました' };
  }
}

// 候補者データ送信
async function sendCandidates({ candidates, sessionId }) {
  try {
    const requestData = {
      candidates: candidates,
      session_id: sessionId || scrapingState.sessionId,
      client_id: scrapingState.clientId,
      requirement_id: scrapingState.requirementId
    };
    
    console.log('Sending candidates data:', requestData);
    console.log('Session ID:', sessionId || scrapingState.sessionId);
    console.log('Client ID:', scrapingState.clientId);
    console.log('Requirement ID:', scrapingState.requirementId);
    
    const response = await fetch(`${getApiBaseUrl()}/api/extension/candidates/batch`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      let errorMessage = 'データ送信に失敗しました';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        // JSONパースエラーの場合はテキストを試す
        try {
          errorMessage = await response.text();
          console.error('API returned non-JSON response:', errorMessage);
        } catch (textError) {
          console.error('Failed to get error details');
        }
      }
      console.error('API Error:', response.status, errorMessage);
      return { success: false, error: errorMessage };
    }
    
    const data = await response.json();
    console.log('Candidates saved successfully:', data);
    
    // 進捗を更新
    scrapingState.progress.success += data.processed;
    scrapingState.progress.current += data.processed;
    
    // ポップアップに進捗を通知
    await updateProgress(scrapingState.progress);
    
    return { success: true, processed: data.processed };
  } catch (error) {
    console.error('Send candidates error:', error);
    return { success: false, error: 'データ送信に失敗しました' };
  }
}

// 進捗更新
async function updateProgress(progress) {
  scrapingState.progress = progress;
  
  // ポップアップに進捗を通知
  try {
    await chrome.runtime.sendMessage({
      type: 'UPDATE_PROGRESS',
      data: progress
    });
  } catch (error) {
    // ポップアップが閉じている場合はエラーを無視
  }
  
  return { success: true };
}

// トークン取得
async function getStoredToken() {
  const result = await chrome.storage.local.get(['rpo_auth_token', 'rpo_token_expiry']);
  
  if (!result.rpo_auth_token || !result.rpo_token_expiry) {
    return null;
  }
  
  // 有効期限チェック
  if (Date.now() > result.rpo_token_expiry) {
    await chrome.storage.local.remove(['rpo_auth_token', 'rpo_token_expiry']);
    return null;
  }
  
  return result.rpo_auth_token;
}

// API ベースURL取得
function getApiBaseUrl() {
  // 本番環境では環境変数から取得するように変更
  return 'http://localhost:8000';
}

// 候補者データの保存とBigQueryアップロード
async function saveCandidates({ candidates, platform }) {
  try {
    console.log('Saving candidates:', candidates.length);
    
    // 現在のセッション情報を取得
    const sessionData = {
      session_id: scrapingState.sessionId,
      client_id: scrapingState.clientId,
      requirement_id: scrapingState.requirementId,
      scraped_by: authState.user?.id || 'unknown',
      platform: platform || 'bizreach'
    };
    
    // 候補者データを整形
    const formattedCandidates = candidates.map(candidate => ({
      ...candidate,
      ...sessionData,
      bizreach_url: candidate.bizreach_url || '',
      scraped_at: new Date().toISOString()
    }));
    
    // APIエンドポイントに送信
    const response = await fetch(`${getApiBaseUrl()}/api/extension/candidates/batch`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        candidates: formattedCandidates,
        session_id: scrapingState.sessionId
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '候補者データの保存に失敗しました');
    }
    
    const result = await response.json();
    
    // 進捗を更新
    scrapingState.progress.current += candidates.length;
    scrapingState.progress.success += candidates.length;
    
    // ポップアップに進捗を通知
    await updateProgress(scrapingState.progress);
    
    console.log('Candidates saved successfully:', result);
    return { success: true, processed: candidates.length };
    
  } catch (error) {
    console.error('Save candidates error:', error);
    scrapingState.progress.error += candidates.length;
    await updateProgress(scrapingState.progress);
    
    return { success: false, error: error.message };
  }
}

// エラー通知
async function notifyError(error) {
  // ポップアップにエラーを通知
  try {
    await chrome.runtime.sendMessage({
      type: 'SCRAPING_ERROR',
      error: error
    });
  } catch (e) {
    // ポップアップが閉じている場合はエラーを無視
  }
  
  // 通知を表示
  chrome.notifications.create({
    type: 'basic',
    iconUrl: '/icons/icon-48.png',
    title: 'RPO Automation エラー',
    message: error
  });
}