// =============================================================================
// GOOGLE APPS SCRIPT - 議論ボットログ受信用
// =============================================================================

function doPost(e) {
  // ロックを取得（同時書き込みでデータが消えるのを防ぐ）
  var lock = LockService.getScriptLock();
  
  try {
    if (!lock.tryLock(10000)) {
      throw new Error("Could not obtain lock after 10 seconds.");
    }

    // スプレッドシートとシートを取得
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = spreadsheet.getActiveSheet();
    
    // リクエストボディの確認
    if (!e.postData || !e.postData.contents) {
      throw new Error("No POST data received");
    }
    
    // Pythonから送られてきたJSONをパース
    var rawData = JSON.parse(e.postData.contents);
    
    // データ形式の確認
    if (!rawData.row || !Array.isArray(rawData.row)) {
      throw new Error("Invalid data format: 'row' must be an array");
    }
    
    // データを行に追加
    sheet.appendRow(rawData.row);
    
    // ログ出力（GASログで確認可能）
    console.log("Row appended successfully:", rawData.row.length, "columns");
    
    // 成功レスポンス
    var result = {
      "status": "success", 
      "message": "Row appended successfully",
      "columns": rawData.row.length,
      "timestamp": new Date().toISOString()
    };
    
    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    // エラーログ出力
    console.error("GAS Error:", error.toString());
    
    // エラーレスポンス
    var errorResponse = {
      "status": "error", 
      "message": error.toString(),
      "timestamp": new Date().toISOString()
    };
    
    return ContentService.createTextOutput(JSON.stringify(errorResponse))
      .setMimeType(ContentService.MimeType.JSON);

  } finally {
    // 必ずロックを解放
    if (lock) {
      lock.releaseLock();
    }
  }
}

// =============================================================================
// テスト用関数（デバッグ時に使用）
// =============================================================================
function testDoPost() {
  // テストデータの作成
  var testEvent = {
    postData: {
      contents: JSON.stringify({
        row: ["2026-01-24 12:00:00", 1, "User", "テスト発言", 1, 0, 1, 0, 0, 1, 3, 0, 1, 0, 1, 0, 0, 3, 1.5, 0.8, 1.2, 3.6, '{"A":-5,"B":3,"C":1,"D":0,"E":2}', "議論継続中", "ONGOING"]
      })
    }
  };
  
  // doPost関数をテスト
  var result = doPost(testEvent);
  console.log("Test result:", result.getContent());
}

// =============================================================================
// スプレッドシート初期化用関数（初回のみ実行）
// =============================================================================
function setupSheet() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  // ヘッダー行を追加（25列）
  var headers = [
    "Timestamp", "Turn", "Speaker", "Content",
    "Logic", "Factuality", "Relevance", "Novelty", "Clarity", "Understanding", "Rationality_Sum",
    "Quantity", "Neg_Politeness", "Pos_Politeness", "Receptivity", "Metaphor", "Substantiation", "Rhetoric_Sum",
    "Presence", "Credit", "Multiplier", "Rhetoric_Impact", "Scores_JSON", "Status_Message", "Status_Code"
  ];
  
  // 既存のヘッダーをチェック
  if (sheet.getLastRow() === 0 || sheet.getRange(1, 1).getValue() !== "Timestamp") {
    sheet.insertRowBefore(1);
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold");
    sheet.getRange(1, 1, 1, headers.length).setBackground("#e1f5fe");
    console.log("Header row added successfully");
  } else {
    console.log("Header row already exists");
  }
}