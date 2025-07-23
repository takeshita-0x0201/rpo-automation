/**
 * パフォーマンス最適化版の関数
 */

/**
 * スプレッドシートのデータ読み取りを最適化
 */
function findEvaluationsToUploadOptimized(sheet) {
  console.time('データ読み取り');
  
  // 最終行を効率的に取得
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    console.timeEnd('データ読み取り');
    return [];
  }
  
  // 必要な列のみを読み取る（A列〜Q列）
  const dataRange = sheet.getRange(2, 1, lastRow - 1, 17); // Q列まで
  const data = dataRange.getValues();
  
  console.timeEnd('データ読み取り');
  console.log(`${lastRow - 1}行のデータを読み取りました`);
  
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
  const COL_UPLOADED = 16;       // Q列: アップロード済みフラグ
  
  data.forEach((row, index) => {
    const assignedHm = row[COL_ASSIGNED_HM];
    const judgement = row[COL_JUDGEMENT];
    const uploaded = row[COL_UPLOADED];
    
    if (assignedHm && judgement && !uploaded) {
      evaluations.push({
        row_number: index + 2,
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
  
  console.log(`${evaluations.length}件の評価対象を検出しました`);
  return evaluations;
}

/**
 * バッチ処理でアップロード済みフラグを設定
 */
function markAsUploadedBatch(sheet, rowNumbers) {
  if (rowNumbers.length === 0) return;
  
  console.time('フラグ更新');
  
  const COL_UPLOADED = 17; // Q列（1ベース）
  const uploadedAt = new Date().toISOString();
  
  // バッチ更新用の値配列を作成
  const updates = [];
  rowNumbers.forEach(rowNum => {
    updates.push([rowNum, COL_UPLOADED, uploadedAt]);
  });
  
  // 一括更新（より効率的）
  updates.forEach(([row, col, value]) => {
    sheet.getRange(row, col).setValue(value);
  });
  
  console.timeEnd('フラグ更新');
  console.log(`${rowNumbers.length}行のフラグを更新しました`);
}

/**
 * デバッグ用: パフォーマンス測定付きテスト実行
 */
function testPerformance() {
  console.time('全体処理時間');
  
  try {
    const spreadsheetId = getSpreadsheetId();
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    const sheet = spreadsheet.getSheetByName('候補者リスト');
    
    if (!sheet) {
      console.error('候補者リストシートが見つかりません');
      return;
    }
    
    // 最適化版を使用
    const evaluations = findEvaluationsToUploadOptimized(sheet);
    
    console.log(`処理対象: ${evaluations.length}件`);
    
    // 最初の1件だけ処理（テスト用）
    if (evaluations.length > 0) {
      const testEval = evaluations[0];
      console.log('テストデータ:', testEval);
    }
    
  } catch (error) {
    console.error('エラー:', error);
  } finally {
    console.timeEnd('全体処理時間');
  }
}