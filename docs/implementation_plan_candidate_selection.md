# 候補者選択・送客機能の実装計画

## 概要
AIマッチング完了後の候補者をWebApp上で確認し、選択した候補者のみをGoogle Sheetsに出力する機能を実装します。

## 実装内容

### 1. 候補者一覧画面の作成

#### 1.1 新規ルートの追加
```python
# src/web/routers/candidates.py (新規作成)

@router.get("/job/{job_id}/candidates", response_class=HTMLResponse)
async def job_candidates_list(request: Request, job_id: str, user: dict = Depends(get_current_user)):
    """ジョブ完了後の候補者一覧表示"""
    # ai_evaluationsテーブルから候補者とスコアを取得
    # 高スコア順にソート
    # テンプレートに渡す

@router.post("/job/{job_id}/export-selected")
async def export_selected_candidates(
    job_id: str,
    selected_candidate_ids: List[str],
    user: dict = Depends(get_current_user)
):
    """選択した候補者をGoogle Sheetsに出力"""
    # 選択された候補者のデータを取得
    # Google Sheets APIで出力
    # candidate_submissionsテーブルに記録
```

#### 1.2 候補者一覧テンプレート
```html
<!-- src/web/templates/admin/job_candidates.html -->

<h1>AIマッチング結果 - 候補者選択</h1>

<div class="candidate-filters mb-4">
    <button class="btn btn-sm btn-outline-primary" onclick="filterByScore('high')">高評価のみ</button>
    <button class="btn btn-sm btn-outline-primary" onclick="filterByScore('all')">全て表示</button>
    <div class="float-end">
        <span id="selected-count">0</span>件選択中
        <button class="btn btn-primary" onclick="exportToSheets()" disabled>
            <i class="bi bi-file-spreadsheet"></i> Sheetsに出力
        </button>
    </div>
</div>

<table class="table table-hover">
    <thead>
        <tr>
            <th><input type="checkbox" id="select-all"></th>
            <th>候補者ID</th>
            <th>会社名</th>
            <th>AIスコア</th>
            <th>推奨度</th>
            <th>マッチ理由</th>
            <th>懸念事項</th>
            <th>詳細</th>
        </tr>
    </thead>
    <tbody>
        {% for eval in evaluations %}
        <tr class="candidate-row" data-score="{{ eval.recommendation }}">
            <td>
                <input type="checkbox" class="candidate-select" 
                       value="{{ eval.candidate_id }}"
                       data-candidate="{{ eval.candidate.to_json() }}">
            </td>
            <td>{{ eval.candidate.candidate_id }}</td>
            <td>{{ eval.candidate.candidate_company }}</td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar 
                         {% if eval.ai_score >= 0.8 %}bg-success
                         {% elif eval.ai_score >= 0.6 %}bg-warning
                         {% else %}bg-danger{% endif %}"
                         style="width: {{ eval.ai_score * 100 }}%">
                        {{ "%.0f"|format(eval.ai_score * 100) }}%
                    </div>
                </div>
            </td>
            <td>
                <span class="badge bg-{{ eval.recommendation_color }}">
                    {{ eval.recommendation_text }}
                </span>
            </td>
            <td>
                <ul class="mb-0">
                    {% for reason in eval.match_reasons[:2] %}
                    <li>{{ reason }}</li>
                    {% endfor %}
                </ul>
            </td>
            <td>
                {% if eval.concerns %}
                    <ul class="mb-0 text-danger">
                        {% for concern in eval.concerns[:2] %}
                        <li>{{ concern }}</li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <span class="text-muted">なし</span>
                {% endif %}
            </td>
            <td>
                <button class="btn btn-sm btn-info" 
                        onclick="showCandidateDetail('{{ eval.candidate_id }}')">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<!-- 候補者詳細モーダル -->
<div class="modal fade" id="candidateDetailModal">
    <!-- 詳細表示 -->
</div>

<script>
// 選択状態の管理
let selectedCandidates = new Map();

// チェックボックスのイベントハンドラ
document.querySelectorAll('.candidate-select').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            selectedCandidates.set(this.value, JSON.parse(this.dataset.candidate));
        } else {
            selectedCandidates.delete(this.value);
        }
        updateSelectedCount();
    });
});

function updateSelectedCount() {
    const count = selectedCandidates.size;
    document.getElementById('selected-count').textContent = count;
    document.querySelector('button[onclick="exportToSheets()"]').disabled = count === 0;
}

async function exportToSheets() {
    if (selectedCandidates.size === 0) {
        alert('候補者を選択してください');
        return;
    }
    
    const candidateIds = Array.from(selectedCandidates.keys());
    
    try {
        const response = await fetch(`/api/candidates/job/{{ job_id }}/export-selected`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({selected_candidate_ids: candidateIds})
        });
        
        const result = await response.json();
        if (result.success) {
            alert(`${candidateIds.length}件の候補者をGoogle Sheetsに出力しました`);
            window.open(result.sheets_url, '_blank');
        }
    } catch (error) {
        alert('エラーが発生しました');
    }
}
</script>
```

### 2. Google Sheets出力機能の実装

#### 2.1 Sheets出力サービス
```python
# src/services/sheets_exporter.py

from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

class SheetsExporter:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH'),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.service = build('sheets', 'v4', credentials=self.creds)
    
    def export_candidates(self, job_info, candidates_data):
        """選択された候補者をGoogle Sheetsに出力"""
        
        # 新しいシートを作成またはテンプレートをコピー
        spreadsheet_id = self.create_or_get_spreadsheet(job_info)
        
        # ヘッダー行
        headers = [
            '候補者ID', '会社名', 'プラットフォーム',
            'AIスコア', '推奨度', 'マッチ理由', '懸念事項',
            '職務経歴（要約）', '候補者リンク'
        ]
        
        # データ行
        rows = [headers]
        for candidate in candidates_data:
            rows.append([
                candidate['candidate_id'],
                candidate['candidate_company'],
                candidate['platform'],
                f"{candidate['ai_score'] * 100:.0f}%",
                self.get_recommendation_text(candidate['recommendation']),
                '\n'.join(candidate['match_reasons']),
                '\n'.join(candidate['concerns'] or []),
                candidate['resume_summary'][:500] + '...',
                candidate['candidate_link']
            ])
        
        # シートに書き込み
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='USER_ENTERED',
            body={'values': rows}
        ).execute()
        
        # フォーマット設定
        self.format_sheet(spreadsheet_id)
        
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
```

### 3. データベース更新

#### 3.1 candidate_submissionsテーブルへの記録
```python
async def record_submission(job_id, candidate_ids, sheets_url, user_id):
    """送客履歴を記録"""
    supabase = get_supabase_client()
    
    submissions = []
    for candidate_id in candidate_ids:
        submission = {
            'job_id': job_id,
            'candidate_id': candidate_id,
            'submitted_at': datetime.now().isoformat(),
            'submitted_by': user_id,
            'status': 'submitted',
            'sheets_url': sheets_url
        }
        submissions.append(submission)
    
    supabase.table('candidate_submissions').insert(submissions).execute()
```

### 4. UI/UXの改善点

1. **フィルタリング機能**
   - スコア別フィルタ（高/中/低）
   - キーワード検索
   - 懸念事項の有無

2. **一括操作**
   - 全選択/全解除
   - スコア閾値での一括選択

3. **プレビュー機能**
   - 職務経歴の詳細表示
   - 評価詳細の展開表示

4. **エクスポート設定**
   - シート名のカスタマイズ
   - 出力項目の選択

### 5. 実装手順

1. **Phase 1**: 候補者一覧画面の基本実装
   - ルーティング追加
   - テンプレート作成
   - 基本的な表示機能

2. **Phase 2**: 選択・フィルタ機能
   - チェックボックス実装
   - フィルタリング機能
   - 詳細表示モーダル

3. **Phase 3**: Google Sheets連携
   - Sheets API実装
   - エクスポート機能
   - URLの保存と表示

4. **Phase 4**: 履歴管理
   - candidate_submissionsへの記録
   - 送客履歴の表示機能

## 期待される効果

1. **品質向上**: 人間の判断を挟むことで、より適切な候補者のみをクライアントに提案
2. **効率化**: 一覧で比較検討でき、効率的な選定が可能
3. **追跡可能性**: どの候補者をいつ誰が送客したか記録が残る
4. **柔軟性**: 状況に応じて出力する候補者を調整可能