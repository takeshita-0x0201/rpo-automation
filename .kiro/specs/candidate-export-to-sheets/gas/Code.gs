/**
 * 候補者データをスプレッドシートに出力するGoogle Apps Script
 * 
 * このスクリプトは、RPO自動化システムから候補者データを受け取り、
 * 指定されたスプレッドシートに新しいシートを作成して出力します。
 */

// スクリプトプロパティからスプレッドシートIDを取得
function getSpreadsheetId() {
  const scriptProperties = PropertiesService.getScriptProperties();
  return scriptProperties.getProperty('SPREADSHEET_ID');
}

/**
 * POSTリクエストを処理するメインエンドポイント
 * @param {Object} e - HTTPリクエストオブジェクト
 * @return {Object} HTTPレスポンス
 */
function doPost(e) {
  try {
    // リクエストデータを解析
    const requestData = JSON.parse(e.postData.contents);
    
    // スプレッドシートを開く
    const spreadsheetId = getSpreadsheetId();
    if (!spreadsheetId) {
      throw new Error('スプレッドシートIDが設定されていません');
    }
    
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
    // 出力先シートを取得または作成
    const targetSheet = getOrCreateTargetSheet(spreadsheet);
    
    // 候補者データを追記
    appendCandidateData(targetSheet, requestData.candidates, requestData);
    
    // スプレッドシート全体のURLを返す（シートIDは含めない）
    const spreadsheetUrl = spreadsheet.getUrl();
    
    return ContentService
      .createTextOutput(JSON.stringify({
        success: true,
        spreadsheet_url: spreadsheetUrl,
        sheet_name: targetSheet.getName(),
        added_count: requestData.candidates.length
      }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    // エラーログを簡潔に
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false,
        error: error.toString()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 出力先シートを取得または作成
 * @param {Spreadsheet} spreadsheet - スプレッドシートオブジェクト
 * @return {Sheet} 出力先シート
 */
function getOrCreateTargetSheet(spreadsheet) {
  const TARGET_SHEET_NAME = '候補者リスト'; // 固定のシート名
  
  // 既存のシートを探す
  let sheet = spreadsheet.getSheetByName(TARGET_SHEET_NAME);
  
  if (!sheet) {
    // シートが存在しない場合は新規作成
    sheet = spreadsheet.insertSheet(TARGET_SHEET_NAME);
    
    // ヘッダーを設定（B列から開始）
    const headers = [
      'Added Date',
      'added by',
      'Name',
      'Company',
      'CV/Profile Link/Bizreach Link',
      '性別',
      'Other (Workable/CV/git..)',
      '英語',
      'ピックアップメモ',
      'Assigned HM (判断者)',
      'Judgement / Meeting Type',
      'Note',
      '送客日時',
      'クライアント',
      '求人タイトル',
      '送客者',
      'Uploaded' // Q列: アップロード済みフラグ
    ];
    
    sheet.getRange(1, 2, 1, headers.length).setValues([headers]);
    
    // ヘッダーのスタイリング（最小限に）
    sheet.getRange(1, 2, 1, headers.length)
      .setFontWeight('bold')
      .setBackground('#4a86e8')
      .setFontColor('#ffffff');
  }
  
  return sheet;
}

/**
 * 候補者データをシートに追記
 * @param {Sheet} sheet - 対象シート
 * @param {Array} candidates - 候補者データの配列
 * @param {Object} requestData - 基本情報を含むリクエストデータ
 */
function appendCandidateData(sheet, candidates, requestData) {
  if (!candidates || candidates.length === 0) {
    return;
  }
  
  // 最終行を取得（データがある最後の行）
  const lastRow = sheet.getLastRow();
  const startRow = lastRow + 1; // 新しいデータの開始行
  
  // 送客日時を Date オブジェクトとして取得
  const submittedDate = new Date(requestData.submitted_at || new Date());
  const addedDateStr = Utilities.formatDate(submittedDate, 'JST', 'MM/dd');
  
  // 候補者データを変換
  const candidateRows = candidates.map(candidate => [
    addedDateStr, // A列: Added Date (mm/dd形式)
    'sugawara', // B列: added by（固定値）
    candidate.candidate_id || '', // C列: Name
    candidate.candidate_company || '', // D列: Company
    candidate.candidate_link || '', // E列: CV/Profile Link
    candidate.gender || '', // F列: 性別（変換なし）
    '', // G列: Other (空欄)
    '', // H列: 英語 (空欄)
    candidate.reason || '', // I列: ピックアップメモ
    '', // J列: Assigned HM (空欄)
    '', // K列: Judgement (空欄)
    '', // L列: Note (空欄)
    submittedDate, // M列: 送客日時
    requestData.client_name || '', // N列: クライアント
    requestData.requirement_title || '', // O列: 求人タイトル
    requestData.submitted_by || '' // P列: 送客者
  ]);
  
  // A列に行番号の数式を先に設定
  try {
    // 各行に個別に数式を設定（より確実な方法）
    for (let i = 0; i < candidateRows.length; i++) {
      const currentRow = startRow + i;
      sheet.getRange(currentRow, 1).setFormula('=ROW()-1');
    }
  } catch (error) {
    console.error('Error setting formulas:', error);
    // エラーが発生した場合は、代替として数値を直接設定
    const rowNumbers = [];
    for (let i = 0; i < candidateRows.length; i++) {
      rowNumbers.push([startRow + i - 1]);
    }
    sheet.getRange(startRow, 1, candidateRows.length, 1).setValues(rowNumbers);
  }
  
  // データを追記（B列から開始）
  sheet.getRange(startRow, 2, candidateRows.length, 16).setValues(candidateRows);
}




/**
 * スクリプトプロパティを設定するヘルパー関数
 * （初回セットアップ時に使用）
 */
function setSpreadsheetId(spreadsheetId) {
  const scriptProperties = PropertiesService.getScriptProperties();
  scriptProperties.setProperty('SPREADSHEET_ID', spreadsheetId);
}