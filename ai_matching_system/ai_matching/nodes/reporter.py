"""
最終レポート生成ノード
"""

from typing import Dict, List
import google.generativeai as genai

from .base import BaseNode, ResearchState, CycleResult


class ReportGeneratorNode(BaseNode):
    """最終的な判定レポートを生成するノード"""
    
    def __init__(self, api_key: str):
        super().__init__("ReportGenerator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def process(self, state: ResearchState) -> ResearchState:
        """最終判定レポートを生成"""
        self.state = "processing"
        
        print(f"評価履歴数: {len(state.evaluation_history)}サイクル")
        print(f"収集情報数: {len(state.search_results)}件")
        
        # 評価の変遷をフォーマット
        journey = self._format_evaluation_journey(state.evaluation_history)
        
        # 収集した追加情報をフォーマット
        additional_info = self._format_collected_info(state.search_results)
        
        # スコア内訳のフォーマット
        score_breakdown_text = ""
        if state.current_evaluation and hasattr(state.current_evaluation, 'score_breakdown') and state.current_evaluation.score_breakdown:
            score_breakdown_text = "\n### スコア内訳"
            for category_key, detail in state.current_evaluation.score_breakdown.items():
                score_breakdown_text += f"\n- {detail.category}: {detail.actual_score:.1f}/{detail.max_score}点"
                if detail.reasoning:
                    score_breakdown_text += f" ({detail.reasoning})"
        
        # 最適化されたプロンプト
        prompt = f"""採用委員会の最終意思決定者として、最終判定を行います。

# 評価データ
## 評価プロセス
{journey}

## 追加情報
{additional_info}

## 最終評価
- スコア: {state.current_evaluation.score if state.current_evaluation else 'N/A'}/100
- 確信度: {state.current_evaluation.confidence if state.current_evaluation else 'N/A'}
- 強み: {', '.join(state.current_evaluation.strengths[:2]) if state.current_evaluation else 'N/A'}
- 懸念: {', '.join(state.current_evaluation.concerns[:2]) if state.current_evaluation else 'N/A'}
{score_breakdown_text}

# 推奨度基準（厳格化）
- A (強く推奨): スコア85以上 + 必須要件を100%明確に満たす + 直近3年以内の実績
- B (推奨): スコア70-84 + 必須要件を90%以上満たす + 具体的成果が明確
- C (条件付き推奨): スコア50-69 + 必須要件を70%以上満たす
- D (非推奨): スコア49以下 または 必須要件の半数以上が未充足/不明確

# 判定理由の作成方法
判定理由は候補者の具体的な経験を2行で記載すること：
- 具体的な技術名、システム名、ツール名を含める
- 数値化できる実績（年数、規模、改善率など）を明記
- 特筆すべきプロジェクトや成果を具体的に記述
- 推薦理由や評価コメントは記載しない（具体的な経験のみ）
- 必須要件不足がある場合は、その不足項目を明示（例：「但し経理財務の実務経験は未確認」）

# 良い例（具体的な経験のみ）
例1: PythonとAWSを活用した決済システム開発5年、月間1億件のトランザクション処理システムの設計・構築経験
マイクロサービス化プロジェクトで処理速度を3倍に改善、CI/CDパイプライン構築により開発効率を50%向上

例2: 製造業3社でSAP導入プロジェクトをリード、売上100億円規模の企業で経理部門の業務効率を40%改善
財務モジュールのカスタマイズと自動仕訳システム開発により月次決算を5営業日から2営業日に短縮

# 悪い例（評価コメントを含む）
例: 必須要件を満たし、豊富な実務経験があります。即戦力として期待できるため推奨します。

# 注意事項
- 「強く推奨します」「推奨します」などの述語は使用しない
- 推薦度はA/B/C/Dの記号で示すため、文章での推薦表現は不要

# 出力フォーマット
推奨度: [A/B/C/D]

判定理由: [候補者の具体的な経験を2行で記載。技術名・システム名・数値を含む実績のみ。評価コメントは含めない]

強み:
- [強み1：具体的実績]
- [強み2：定量的成果]
- [強み3：付加価値]

懸念点:
- [懸念1：必須要件不足の場合はその業務上の重大性を明記]
- [懸念2：無理な楽観視は避け、事実のみ記載]

総合評価: [必ず3-4文で最終判断を記載。空欄にしないこと。以下を必ず含める：
1. 必須要件の充足度（○個中○個を明確に充足、不足の場合はその項目を具体的に）
2. 必須要件不足がある場合、その業務遂行上の重大な影響
3. 主要な強みと実績（具体的数値を含む）
4. 主要な懸念点（必須要件不足を最優先で記載）
5. 最終的な推薦判断（必須要件不足がある場合は原則非推奨）]"""
        
        print(f"LLMに最終判定を依頼中...")
        response = self.model.generate_content(prompt)
        print(f"LLMから応答受信")
        
        final_judgment = self._parse_final_judgment(response.text)
        print(f"最終判定パース完了: 推奨度{final_judgment['recommendation']}")
        
        # 状態を更新
        state.final_judgment = final_judgment
        self.state = "completed"
        
        return state
    
    def _format_evaluation_journey(self, history: List[CycleResult]) -> str:
        """評価の変遷をフォーマット"""
        if not history:
            return "初回評価のみ実施"
        
        text = f"### 評価プロセス概要\n全{len(history)}回の評価サイクルを実施\n"
        
        for cycle in history:
            text += f"\n#### サイクル{cycle.cycle_number}"
            text += f"\n- **スコア**: {cycle.evaluation.score}点（確信度: {cycle.evaluation.confidence}）"
            
            if cycle.gaps:
                text += f"\n- **特定された情報ギャップ**: {len(cycle.gaps)}件"
                for gap in cycle.gaps[:2]:  # 上位2つのみ表示
                    text += f"\n  - {gap.info_type} (重要度: {gap.importance})"
            
            if cycle.search_results:
                text += f"\n- **収集した情報**: {len(cycle.search_results)}件"
            
            if cycle.evaluation.summary:
                text += f"\n- **評価サマリー**: {cycle.evaluation.summary}"
            
            # スコアの変化を強調
            if cycle.cycle_number > 1 and len(history) >= cycle.cycle_number - 1:
                prev_score = history[cycle.cycle_number - 2].evaluation.score
                score_diff = cycle.evaluation.score - prev_score
                if score_diff != 0:
                    text += f"\n- **スコア変化**: {'+' if score_diff > 0 else ''}{score_diff}点"
        
        return text
    
    def _format_collected_info(self, search_results: Dict) -> str:
        """収集した情報をフォーマット"""
        if not search_results:
            return "追加情報の収集なし"
        
        text = "### 収集された追加情報の要約\n"
        for i, (key, result) in enumerate(search_results.items(), 1):
            text += f"\n#### {i}. {key}"
            text += f"\n{result.summary}"
            if result.sources:
                text += f"\n*情報源: {', '.join(result.sources[:2])}*"
        
        return text
    
    def _parse_final_judgment(self, text: str) -> Dict:
        """最終判定をパース"""
        print(f"  判定パース開始（文字数: {len(text)}）")
        
        # デフォルト値
        judgment = {
            'recommendation': 'C',
            'reason': '',
            'strengths': [],
            'concerns': [],
            'overall_assessment': ''
        }
        
        lines = text.strip().split('\n')
        current_section = None
        overall_lines = []  # 総合評価の行を集める
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 推奨度
            if line.startswith('推奨度:') or '推奨度:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    rec = parts[1].strip()
                    if 'A' in rec:
                        judgment['recommendation'] = 'A'
                    elif 'B' in rec:
                        judgment['recommendation'] = 'B'
                    elif 'C' in rec:
                        judgment['recommendation'] = 'C'
                    elif 'D' in rec:
                        judgment['recommendation'] = 'D'
                    print(f"    推奨度検出: {judgment['recommendation']}")
            
            # 判定理由
            elif line.startswith('判定理由:'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    judgment['reason'] = parts[1].strip()
                # 次の行も理由の続きかもしれない
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith(('強み', '懸念', '総合評価')):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith(('-', '・')):
                        judgment['reason'] += ' ' + next_line
            
            # セクション開始
            elif '強み' in line and ':' in line:
                current_section = 'strengths'
            elif '懸念' in line and ':' in line:
                current_section = 'concerns'
            elif ('総合評価' in line) and (':' in line or '：' in line):
                parts = line.split(':', 1) if ':' in line else line.split('：', 1)
                if len(parts) > 1 and parts[1].strip():
                    overall_lines.append(parts[1].strip())
                current_section = 'overall'
            
            # 項目収集
            elif line.startswith('-') or line.startswith('・'):
                item = line[1:].strip()
                if current_section == 'strengths' and len(judgment['strengths']) < 3:
                    judgment['strengths'].append(item)
                elif current_section == 'concerns' and len(judgment['concerns']) < 3:
                    judgment['concerns'].append(item)
            
            # 総合評価の続き
            elif current_section == 'overall' and line and not line.startswith(('-', '・')):
                # 次のセクションの開始を検出
                if any(keyword in line for keyword in ['推奨度:', '判定理由:', '強み:', '懸念点:', '面接確認事項:']):
                    current_section = None
                else:
                    overall_lines.append(line)
        
        # 総合評価を結合
        if overall_lines:
            judgment['overall_assessment'] = ' '.join(overall_lines).strip()
            print(f"    総合評価検出: {len(judgment['overall_assessment'])}文字")
        
        # デフォルト値の設定
        if not judgment['strengths']:
            judgment['strengths'] = ['詳細な強みは評価中']
        if not judgment['concerns']:
            judgment['concerns'] = ['特筆すべき懸念なし']
        
        # 総合評価のデフォルト値を改善
        if not judgment['overall_assessment']:
            # recommendationとreasonから自動生成
            if judgment['reason']:
                assessment = f"候補者は{judgment['reason']} "
                
                if judgment['recommendation'] == 'A':
                    assessment += "以上の経験・スキルから、本ポジションに非常に適した人材と判断します。"
                elif judgment['recommendation'] == 'B':
                    assessment += "必要な要件を概ね満たしており、本ポジションでの活躍が期待できます。"
                elif judgment['recommendation'] == 'C':
                    assessment += "一定の要件は満たしているものの、面接での詳細確認が必要です。"
                else:
                    assessment += "現時点では必須要件との適合度が低いと判断します。"
                
                judgment['overall_assessment'] = assessment
                print(f"    総合評価を自動生成: {len(assessment)}文字")
            else:
                # 最終手段のデフォルト
                judgment['overall_assessment'] = '詳細な評価結果については、強みと懸念点をご確認ください。'
                print(f"    総合評価にデフォルト値を設定")
        
        print(f"    パース完了: 推奨度={judgment['recommendation']}, 強み={len(judgment['strengths'])}, 懸念={len(judgment['concerns'])}")
        
        return judgment