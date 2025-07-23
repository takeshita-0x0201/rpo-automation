/**
 * クライアント評価アップローダー
 * スプレッドシートからclient_evaluationsテーブルへのデータ同期
 */

// FastAPIエンドポイントのURL（スクリプトプロパティから取得）
function getApiEndpoint() {
  const scriptProperties = PropertiesService.getScriptProperties();
  return scriptProperties.getProperty('API_ENDPOINT') || 'http://localhost:8000/api/client-evaluations/batch-upload';
}

// APIキー（認証用）
function getApiKey() {
  const scriptProperties = PropertiesService.getScriptProperties();
  return scriptProperties.getProperty('API_KEY');
}

/**
 * 定期実行用のメイン関数（1時間ごとに実行）
 */
function syncClientEvaluations() {
  try {
    console.log('クライアント評価の同期を開始します');
    
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
    
    // APIにデータを送信
    const result = uploadToApi(evaluationsToUpload);
    
    if (result.success) {
      // 成功した行に処理済みフラグを設定
      markAsUploaded(sheet, result.uploaded_rows);
      console.log(`${result.uploaded_rows.length}件の評価をアップロードしました`);
    } else {
      console.error('APIへのアップロードに失敗しました:', result.error);
    }
    
  } catch (error) {
    console.error('同期処理中にエラーが発生しました:', error);
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
 * FastAPIエンドポイントにデータをアップロード
 * @param {Array} evaluations - アップロードするデータ
 * @return {Object} 結果オブジェクト
 */
function uploadToApi(evaluations) {
  try {
    const apiEndpoint = getApiEndpoint();
    const apiKey = getApiKey();
    
    const payload = {
      evaluations: evaluations,
      source: 'google_sheets',
      uploaded_at: new Date().toISOString()
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(apiEndpoint, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode === 200 || responseCode === 201) {
      const responseData = JSON.parse(response.getContentText());
      return {
        success: true,
        uploaded_rows: evaluations.map(e => e.row_number),
        response: responseData
      };
    } else {
      return {
        success: false,
        error: `APIエラー: ${responseCode} - ${response.getContentText()}`
      };
    }
    
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
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
 * 定期実行トリガーを設定（初回セットアップ用）
 */
function setupTrigger() {
  // 既存のトリガーを削除
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'syncClientEvaluations') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // 1時間ごとのトリガーを設定
  ScriptApp.newTrigger('syncClientEvaluations')
    .timeBased()
    .everyHours(1)
    .create();
  
  console.log('定期実行トリガーを設定しました（1時間ごと）');
}

/**
 * 手動テスト用：少数のデータでテスト
 */
function testSyncWithLimit() {
  try {
    const spreadsheetId = getSpreadsheetId();
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    const sheet = spreadsheet.getSheetByName('候補者リスト');
    
    if (!sheet) {
      console.error('候補者リストシートが見つかりません');
      return;
    }
    
    // 最初の3件のみ取得してテスト
    const evaluations = findEvaluationsToUpload(sheet).slice(0, 3);
    
    if (evaluations.length === 0) {
      console.log('テスト対象の評価が見つかりませんでした');
      return;
    }
    
    console.log('テストデータ:', JSON.stringify(evaluations, null, 2));
    
    // ここでAPIを呼ばずにデータ確認のみ行う
    // 実際のアップロードはコメントアウト
    // const result = uploadToApi(evaluations);
  } catch (error) {
    console.error('テスト中にエラーが発生しました:', error);
  }
}

/**
 * スクリプトプロパティの設定（初回セットアップ用）
 */
function setupScriptProperties() {
  const scriptProperties = PropertiesService.getScriptProperties();
  
  // 既存のスプレッドシートIDを使用
  const existingSpreadsheetId = scriptProperties.getProperty('SPREADSHEET_ID');
  if (existingSpreadsheetId) {
    console.log('既存のSPREADSHEET_IDを使用します:', existingSpreadsheetId);
  }
  
  // APIエンドポイントとキーを設定（本番環境では適切な値に変更）
  scriptProperties.setProperty('API_ENDPOINT', 'https://your-api-domain.com/api/client-evaluations/batch-upload');
  scriptProperties.setProperty('API_KEY', 'your-api-key-here');
  
  console.log('スクリプトプロパティを設定しました');
}