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

# 推奨度基準（厳格化）
- A (強く推奨): スコア71以上 + 必須要件を全て満たす + 実務経験5年以上
- B (推奨): スコア51-70 + 必須要件を7割以上満たす
- C (条件付き推奨): スコア31-50
- D (非推奨): スコア30以下 または 重要必須要件を欠く

# 出力フォーマット
推奨度: [A/B/C/D]

判定理由: [必須要件の充足状況と経験年数を明確に記載。システム/技術面の評価も含める。曖昧表現禁止。2-3文で簡潔に]

強み:
- [強み1：具体的実績]
- [強み2：定量的成果]
- [強み3：付加価値]

懸念点:
- [懸念1：代替案含む]
- [懸念2：改善可能性含む]

総合評価: [3-4文で最終判断]"""
        
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
        
        for line in lines:
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
            
            # セクション開始
            elif '強み' in line and ':' in line:
                current_section = 'strengths'
            elif '懸念' in line and ':' in line:
                current_section = 'concerns'
            elif ('総合評価' in line) and (':' in line or '：' in line):
                parts = line.split(':', 1) if ':' in line else line.split('：', 1)
                if len(parts) > 1:
                    judgment['overall_assessment'] = parts[1].strip()
                current_section = 'overall'
            
            # 項目収集
            elif line.startswith('-') or line.startswith('・'):
                item = line[1:].strip()
                if current_section == 'strengths' and len(judgment['strengths']) < 3:
                    judgment['strengths'].append(item)
                elif current_section == 'concerns' and len(judgment['concerns']) < 3:
                    judgment['concerns'].append(item)
            
            # 総合評価の続き
            elif current_section == 'overall' and line and not line.startswith('-'):
                judgment['overall_assessment'] += ' ' + line
        
        # デフォルト値の設定
        if not judgment['strengths']:
            judgment['strengths'] = ['詳細な強みは評価中']
        if not judgment['concerns']:
            judgment['concerns'] = ['特筆すべき懸念なし']
        if not judgment['overall_assessment']:
            judgment['overall_assessment'] = '総合的な評価を実施中'
        
        print(f"    パース完了: 推奨度={judgment['recommendation']}, 強み={len(judgment['strengths'])}, 懸念={len(judgment['concerns'])}")
        
        return judgment