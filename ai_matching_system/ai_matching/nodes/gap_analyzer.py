"""
情報ギャップ分析ノード
"""

from typing import List
import google.generativeai as genai

from .base import BaseNode, ResearchState, InformationGap


class GapAnalyzerNode(BaseNode):
    """評価の不確実性から情報ギャップを特定するノード"""
    
    def __init__(self, api_key: str):
        super().__init__("GapAnalyzer")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def process(self, state: ResearchState) -> ResearchState:
        """情報ギャップを分析"""
        self.state = "processing"
        
        # 現在の評価を確認
        if not state.current_evaluation:
            print("  警告: 評価結果がありません")
            state.information_gaps = []
            self.state = "completed"
            return state
        
        eval_result = state.current_evaluation
        print(f"  現在の評価を分析: スコア{eval_result.score}, 確信度{eval_result.confidence}")
        
        # 既に収集した情報
        collected_info = list(state.search_results.keys())
        if collected_info:
            print(f"  既存の収集情報: {len(collected_info)}件")
        
        # 最適化されたプロンプト
        prompt = f"""情報分析専門家として、評価の確実性向上に必要な追加情報を特定します。

# 現在の評価
- スコア: {eval_result.score}/100
- 確信度: {eval_result.confidence}
- 強み: {', '.join(eval_result.strengths[:2])}
- 懸念: {', '.join(eval_result.concerns[:2])}
- 収集済み: {', '.join(collected_info) if collected_info else 'なし'}

# 終了条件
- 確信度「高」→ 追加情報不要
- スコア90以上/20以下 + 確信度「中」以上 → 追加情報不要

# 必要な場合の出力（最大3つ）
情報1:
種類: [技術トレンド/業界標準/スキル要件]
説明: [必要性]
検索クエリ: [具体的クエリ]
重要度: [高/中/低]
理由: [判断への影響]

# 良いクエリ例
- "財務システム Python 導入事例 2024"
- "IT企業 経理部門 必要スキル"

# 避けるべきクエリ
- 個人情報を含む
- 曖昧すぎる
- 範囲が広すぎる"""
        
        print(f"  LLMに情報ギャップ分析を依頼中...")
        response = self.model.generate_content(prompt)
        print(f"  LLMから応答受信")
        
        gaps = self._parse_gaps(response.text)
        print(f"  情報ギャップ分析完了: {len(gaps)}件の不足情報を特定")
        
        # 状態を更新
        state.information_gaps = gaps
        
        # 継続判定
        if not gaps or eval_result.confidence == "高":
            state.should_continue = False
            print(f"  継続判定: 終了（理由: {'確信度が高い' if eval_result.confidence == '高' else '追加情報不要'}）")
        else:
            print(f"  継続判定: 続行（追加情報収集が必要）")
        
        self.state = "completed"
        return state
    
    def _parse_gaps(self, text: str) -> List[InformationGap]:
        """LLMの出力を情報ギャップにパース"""
        gaps = []
        
        if "追加情報不要" in text:
            return gaps
        
        # 情報ブロックを分割
        blocks = text.strip().split('\n\n')
        
        current_gap = {}
        for line in text.strip().split('\n'):
            line = line.strip()
            
            if line.startswith("情報") and ":" in line:
                # 新しい情報ブロック開始
                if current_gap and all(k in current_gap for k in ['type', 'description', 'query', 'importance', 'rationale']):
                    gaps.append(InformationGap(
                        info_type=current_gap['type'],
                        description=current_gap['description'],
                        search_query=current_gap['query'],
                        importance=current_gap['importance'],
                        rationale=current_gap['rationale']
                    ))
                current_gap = {}
            elif line.startswith("種類:"):
                current_gap['type'] = line.split(':', 1)[1].strip()
            elif line.startswith("説明:"):
                current_gap['description'] = line.split(':', 1)[1].strip()
            elif line.startswith("検索クエリ:"):
                current_gap['query'] = line.split(':', 1)[1].strip()
            elif line.startswith("重要度:"):
                imp = line.split(':', 1)[1].strip()
                if imp in ["高", "中", "低"]:
                    current_gap['importance'] = imp
            elif line.startswith("理由:"):
                current_gap['rationale'] = line.split(':', 1)[1].strip()
        
        # 最後のギャップを追加
        if current_gap and all(k in current_gap for k in ['type', 'description', 'query', 'importance', 'rationale']):
            gaps.append(InformationGap(
                info_type=current_gap['type'],
                description=current_gap['description'],
                search_query=current_gap['query'],
                importance=current_gap['importance'],
                rationale=current_gap['rationale']
            ))
        
        # 最大3つに制限
        return gaps[:3]