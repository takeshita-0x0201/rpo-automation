/**
 * クライアント評価アップローダー（Supabase直接接続版）
 * スプレッドシートから直接Supabaseのclient_evaluationsテーブルへデータ同期
 */

// Supabase設定（スクリプトプロパティから取得）
function getSupabaseConfig() {
  const scriptProperties = PropertiesService.getScriptProperties();
  return {
    url: scriptProperties.getProperty('SUPABASE_URL') || 'https://agpoeoexuirxzdszdtlu.supabase.co',
    anonKey: scriptProperties.getProperty('SUPABASE_ANON_KEY'),
    serviceKey: scriptProperties.getProperty('SUPABASE_SERVICE_KEY') // service_roleキーを使用
  };
}

/**
 * 定期実行用のメイン関数（1時間ごとに実行）
 */
function syncClientEvaluationsDirectly() {
  try {
    console.log('Supabase直接同期を開始します');
    
    // スプレッドシートを開く
    const spreadsheetId = getSpreadsheetId();
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    const sheet = spreadsheet.getSheetByName('候補者リスト');
    
    if (!sheet) {
      console.error('候補者リストシートが見つかりません');
      return;
    }
    
    // 処理対象の行を検出
    const evaluationsToUpload = findEvaluationsToUpload(sheet);
    
    if (evaluationsToUpload.length === 0) {
      console.log('アップロード対象の評価が見つかりませんでした');
      return;
    }
    
    console.log(`${evaluationsToUpload.length}件の評価をアップロードします`);
    
    // Supabaseに直接データを保存
    const results = uploadToSupabase(evaluationsToUpload);
    
    if (results.success > 0) {
      // 成功した行に処理済みフラグを設定
      markAsUploaded(sheet, results.uploaded_rows);
      console.log(`${results.success}件の評価をアップロードしました`);
    }
    
    if (results.failed > 0) {
      console.error(`${results.failed}件の評価のアップロードに失敗しました`);
      results.errors.forEach(error => console.error(error));
    }
    
  } catch (error) {
    console.error('同期処理中にエラーが発生しました:', error);
  }
}

/**
 * Supabaseに直接データをアップロード
 * @param {Array} evaluations - アップロードするデータ
 * @return {Object} 結果オブジェクト
 */
function uploadToSupabase(evaluations) {
  const config = getSupabaseConfig();
  const results = {
    success: 0,
    failed: 0,
    uploaded_rows: [],
    errors: []
  };
  
  evaluations.forEach(evaluation => {
    try {
      // 1. candidate_idの解決（candidate_nameから検索）
      const candidateId = findCandidateId(evaluation.candidate_name);
      if (!candidateId) {
        throw new Error(`候補者 '${evaluation.candidate_name}' が見つかりません`);
      }
      
      // 2. requirement_idの解決（job_titleから検索）
      const requirementId = findRequirementId(evaluation.job_title);
      if (!requirementId) {
        throw new Error(`求人 '${evaluation.job_title}' が見つかりません`);
      }
      
      // 3. client_evaluationsテーブルに保存/更新
      const evaluationData = {
        candidate_id: evaluation.candidate_name, // TEXT型なので名前をそのまま使用
        requirement_id: requirementId,
        client_evaluation: evaluation.judgement,
        client_feedback: evaluation.note,
        evaluation_date: new Date().toISOString().split('T')[0], // YYYY-MM-DD形式
        created_by: evaluation.assigned_hm,
        updated_at: new Date().toISOString(),
        synced_to_pinecone: false,
        sync_retry_count: 0
      };
      
      // 既存のレコードを確認
      const existingRecord = checkExistingEvaluation(
        evaluation.candidate_name,
        requirementId
      );
      
      let success = false;
      if (existingRecord) {
        // 更新
        success = updateEvaluation(evaluationData);
      } else {
        // 新規作成
        evaluationData.created_at = new Date().toISOString();
        success = insertEvaluation(evaluationData);
      }
      
      if (success) {
        results.success++;
        results.uploaded_rows.push(evaluation.row_number);
      } else {
        throw new Error('Supabaseへの保存に失敗しました');
      }
      
    } catch (error) {
      results.failed++;
      results.errors.push({
        row: evaluation.row_number,
        error: error.toString()
      });
    }
  });
  
  return results;
}

/**
 * candidatesテーブルからcandidate_idを検索
 */
function findCandidateId(candidateName) {
  const config = getSupabaseConfig();
  const url = `${config.url}/rest/v1/candidates?candidate_id=eq.${encodeURIComponent(candidateName)}&select=id`;
  
  const response = UrlFetchApp.fetch(url, {
    method: 'GET',
    headers: {
      'apikey': config.serviceKey,
      'Authorization': `Bearer ${config.serviceKey}`
    }
  });
  
  const data = JSON.parse(response.getContentText());
  return data.length > 0 ? data[0].id : null;
}

/**
 * job_requirementsテーブルからrequirement_idを検索
 */
function findRequirementId(jobTitle) {
  const config = getSupabaseConfig();
  const url = `${config.url}/rest/v1/job_requirements?title=eq.${encodeURIComponent(jobTitle)}&select=requirement_id,id`;
  
  const response = UrlFetchApp.fetch(url, {
    method: 'GET',
    headers: {
      'apikey': config.serviceKey,
      'Authorization': `Bearer ${config.serviceKey}`
    }
  });
  
  const data = JSON.parse(response.getContentText());
  if (data.length > 0) {
    return data[0].requirement_id || data[0].id;
  }
  return null;
}

/**
 * 既存の評価を確認
 */
function checkExistingEvaluation(candidateId, requirementId) {
  const config = getSupabaseConfig();
  const url = `${config.url}/rest/v1/client_evaluations?candidate_id=eq.${encodeURIComponent(candidateId)}&requirement_id=eq.${encodeURIComponent(requirementId)}`;
  
  const response = UrlFetchApp.fetch(url, {
    method: 'GET',
    headers: {
      'apikey': config.serviceKey,
      'Authorization': `Bearer ${config.serviceKey}`
    }
  });
  
  const data = JSON.parse(response.getContentText());
  return data.length > 0 ? data[0] : null;
}

/**
 * 評価を新規作成
 */
function insertEvaluation(evaluationData) {
  const config = getSupabaseConfig();
  const url = `${config.url}/rest/v1/client_evaluations`;
  
  try {
    const response = UrlFetchApp.fetch(url, {
      method: 'POST',
      headers: {
        'apikey': config.serviceKey,
        'Authorization': `Bearer ${config.serviceKey}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      payload: JSON.stringify(evaluationData)
    });
    
    return response.getResponseCode() === 201;
  } catch (error) {
    console.error('Insert error:', error);
    return false;
  }
}

/**
 * 評価を更新
 */
function updateEvaluation(evaluationData) {
  const config = getSupabaseConfig();
  const candidateId = encodeURIComponent(evaluationData.candidate_id);
  const requirementId = encodeURIComponent(evaluationData.requirement_id);
  const url = `${config.url}/rest/v1/client_evaluations?candidate_id=eq.${candidateId}&requirement_id=eq.${requirementId}`;
  
  try {
    const response = UrlFetchApp.fetch(url, {
      method: 'PATCH',
      headers: {
        'apikey': config.serviceKey,
        'Authorization': `Bearer ${config.serviceKey}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      payload: JSON.stringify(evaluationData)
    });
    
    return response.getResponseCode() === 204;
  } catch (error) {
    console.error('Update error:', error);
    return false;
  }
}

/**
 * アップロード対象の評価を検出
 * @param {Sheet} sheet - 対象シート
 * @return {Array} アップロード対象のデータ配列
 */
function findEvaluationsToUpload(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return []; // ヘッダーのみの場合
  
  const lastCol = sheet.getLastColumn();
  const dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
  const data = dataRange.getValues();
  
  const evaluations = [];
  
  // 列インデックス（0ベース）
  const COL_NAME = 2;           // C列: Name
  const COL_COMPANY = 3;         // D列: Company
  const COL_CV_LINK = 4;         // E列: CV/Profile Link
  const COL_ASSIGNED_HM = 9;     // J列: Assigned HM
  const COL_JUDGEMENT = 10;      // K列: Judgement
  const COL_NOTE = 11;           // L列: Note
  const COL_CLIENT = 13;         // N列: クライアント
  const COL_JOB_TITLE = 14;      // O列: 求人タイトル
  const COL_UPLOADED = 16;       // Q列: アップロード済みフラグ（新規追加）
  
  data.forEach((row, index) => {
    const assignedHm = row[COL_ASSIGNED_HM];
    const judgement = row[COL_JUDGEMENT];
    const uploaded = row[COL_UPLOADED];
    
    // アップロード条件：
    // 1. Assigned HMが入力されている
    // 2. Judgementが入力されている
    // 3. まだアップロードされていない（Q列が空またはfalse）
    if (assignedHm && judgement && !uploaded) {
      evaluations.push({
        row_number: index + 2, // 実際の行番号（1ベース、ヘッダー込み）
        candidate_name: row[COL_NAME] || '',
        candidate_company: row[COL_COMPANY] || '',
        candidate_link: row[COL_CV_LINK] || '',
        assigned_hm: assignedHm,
        judgement: judgement,
        note: row[COL_NOTE] || '',
        client_name: row[COL_CLIENT] || '',
        job_title: row[COL_JOB_TITLE] || '',
        evaluation_date: new Date().toISOString()
      });
    }
  });
  
  return evaluations;
}

/**
 * アップロード済みの行にフラグを設定
 * @param {Sheet} sheet - 対象シート
 * @param {Array} rowNumbers - 処理済みの行番号配列
 */
function markAsUploaded(sheet, rowNumbers) {
  const COL_UPLOADED = 17; // Q列（1ベース）
  const uploadedAt = new Date().toISOString();
  
  rowNumbers.forEach(rowNum => {
    // Q列にアップロード日時を記録
    sheet.getRange(rowNum, COL_UPLOADED).setValue(uploadedAt);
  });
}

/**
 * スクリプトプロパティの設定（初回セットアップ用）
 */
function setupSupabaseProperties() {
  const scriptProperties = PropertiesService.getScriptProperties();
  
  // 既存のスプレッドシートIDを保持
  const existingSpreadsheetId = scriptProperties.getProperty('SPREADSHEET_ID');
  if (existingSpreadsheetId) {
    console.log('既存のSPREADSHEET_IDを使用します:', existingSpreadsheetId);
  }
  
  // Supabase接続情報を設定（.envファイルの値を使用）
  scriptProperties.setProperty('SUPABASE_URL', 'https://agpoeoexuirxzdszdtlu.supabase.co');
  scriptProperties.setProperty('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFncG9lb2V4dWlyeHpkc3pkdGx1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE1OTMzOTEsImV4cCI6MjA2NzE2OTM5MX0.gCx3hYQLcL8wrWk7LBSK3wo-4rPWt7vyDdy-B2loByA');
  scriptProperties.setProperty('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFncG9lb2V4dWlyeHpkc3pkdGx1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTU5MzM5MSwiZXhwIjoyMDY3MTY5MzkxfQ.ro0Leni7Dp9ag7DtWY-Uenrp35Y_Ybtlafb7JkCOL_0');
  
  console.log('Supabaseプロパティを設定しました');
}

/**
 * 定期実行トリガーを設定（Supabase直接版）
 */
function setupDirectSyncTrigger() {
  // 既存のトリガーを削除
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'syncClientEvaluationsDirectly') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // 1時間ごとのトリガーを設定
  ScriptApp.newTrigger('syncClientEvaluationsDirectly')
    .timeBased()
    .everyHours(1)
    .create();
  
  console.log('Supabase直接同期トリガーを設定しました（1時間ごと）');
}