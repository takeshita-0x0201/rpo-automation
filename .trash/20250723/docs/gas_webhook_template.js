/**
 * Google Apps Script - RPO Automation Webhook Handler
 * 
 * このスクリプトは、RPO AutomationシステムからのWebhookを受け取り、
 * Google Sheetsに候補者データを書き込みます。
 */

// 設定
const SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID'; // スプレッドシートのID
const SHEET_TEMPLATE_NAME = 'テンプレート'; // テンプレートシート名

/**
 * POSTリクエストを処理
 */
function doPost(e) {
  try {
    // リクエストデータをパース
    const data = JSON.parse(e.postData.contents);
    
    // スプレッドシートを開く
    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    
    // 新しいシートを作成（テンプレートをコピー）
    const templateSheet = spreadsheet.getSheetByName(SHEET_TEMPLATE_NAME);
    const newSheetName = `${data.client_name}_${new Date().toISOString().split('T')[0]}`;
    const newSheet = templateSheet.copyTo(spreadsheet);
    newSheet.setName(newSheetName);
    
    // ヘッダー情報を設定
    newSheet.getRange('A1').setValue(`クライアント: ${data.client_name}`);
    newSheet.getRange('A2').setValue(`採用要件: ${data.requirement_title}`);
    newSheet.getRange('A3').setValue(`送客日: ${new Date().toLocaleString('ja-JP')}`);
    newSheet.getRange('A4').setValue(`送客者: ${data.submitted_by}`);
    newSheet.getRange('A5').setValue(`候補者数: ${data.submission_count}`);
    
    // 候補者データのヘッダー
    const headers = [
      '候補者ID',
      '会社名',
      'プラットフォーム',
      'AIスコア',
      '推奨度',
      'マッチ理由',
      '懸念事項',
      '職務経歴（要約）',
      '候補者リンク'
    ];
    
    // ヘッダーを書き込み
    const headerRange = newSheet.getRange(7, 1, 1, headers.length);
    headerRange.setValues([headers]);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#4285f4');
    headerRange.setFontColor('#ffffff');
    
    // 候補者データを書き込み
    const candidateRows = data.candidates.map(candidate => [
      candidate.candidate_id,
      candidate.candidate_company || '-',
      candidate.platform,
      `${Math.round(candidate.ai_score * 100)}%`,
      translateRecommendation(candidate.recommendation),
      candidate.match_reasons.join('\n'),
      candidate.concerns.join('\n') || 'なし',
      candidate.resume_summary,
      candidate.candidate_link
    ]);
    
    if (candidateRows.length > 0) {
      const dataRange = newSheet.getRange(8, 1, candidateRows.length, headers.length);
      dataRange.setValues(candidateRows);
      
      // 自動調整
      newSheet.autoResizeColumns(1, headers.length);
      
      // リンクをハイパーリンクに変換
      for (let i = 0; i < candidateRows.length; i++) {
        const linkCell = newSheet.getRange(8 + i, 9);
        const linkValue = candidateRows[i][8];
        if (linkValue) {
          linkCell.setFormula(`=HYPERLINK("${linkValue}", "リンク")`);
        }
      }
    }
    
    // スプレッドシートのURLを返す
    const spreadsheetUrl = spreadsheet.getUrl() + '#gid=' + newSheet.getSheetId();
    
    // 成功レスポンス
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      spreadsheet_url: spreadsheetUrl,
      sheet_name: newSheetName,
      processed_count: candidateRows.length
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    // エラーレスポンス
    console.error('Error:', error);
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 推奨度を日本語に変換
 */
function translateRecommendation(recommendation) {
  const translations = {
    'high': '強く推奨',
    'medium': '推奨',
    'low': '要検討'
  };
  return translations[recommendation] || recommendation;
}

/**
 * テスト用のGETリクエスト処理
 */
function doGet(e) {
  return ContentService.createTextOutput('RPO Automation Webhook Handler is running');
}

/**
 * 初期設定用関数（手動実行）
 */
function setupTemplate() {
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
  
  // テンプレートシートが存在しない場合は作成
  let templateSheet = spreadsheet.getSheetByName(SHEET_TEMPLATE_NAME);
  if (!templateSheet) {
    templateSheet = spreadsheet.insertSheet(SHEET_TEMPLATE_NAME);
  }
  
  // テンプレートの設定
  templateSheet.clear();
  templateSheet.getRange('A1:A5').setFontWeight('bold');
  templateSheet.setColumnWidth(1, 150); // 候補者ID
  templateSheet.setColumnWidth(2, 200); // 会社名
  templateSheet.setColumnWidth(3, 100); // プラットフォーム
  templateSheet.setColumnWidth(4, 80);  // AIスコア
  templateSheet.setColumnWidth(5, 80);  // 推奨度
  templateSheet.setColumnWidth(6, 300); // マッチ理由
  templateSheet.setColumnWidth(7, 250); // 懸念事項
  templateSheet.setColumnWidth(8, 400); // 職務経歴
  templateSheet.setColumnWidth(9, 100); // リンク
  
  // テンプレートを非表示
  templateSheet.hideSheet();
}