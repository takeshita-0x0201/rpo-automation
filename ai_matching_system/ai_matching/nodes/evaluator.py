"""
候補者評価ノード
"""

import os
from typing import Dict, List
import google.generativeai as genai

from .base import BaseNode, ResearchState, EvaluationResult


class EvaluatorNode(BaseNode):
    """候補者を評価するノード"""
    
    def __init__(self, api_key: str):
        super().__init__("Evaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def process(self, state: ResearchState) -> ResearchState:
        """候補者を現在の情報で評価"""
        self.state = "processing"
        
        print(f"  候補者評価を開始（サイクル{state.current_cycle}）")
        
        # 追加情報のフォーマット
        additional_info = self._format_additional_info(state.search_results)
        if additional_info:
            print(f"  追加情報を含めて評価: {len(state.search_results)}件の検索結果")
        
        # 評価履歴のフォーマット
        history_text = self._format_history(state.evaluation_history)
        if state.evaluation_history:
            print(f"  過去の評価履歴を考慮: {len(state.evaluation_history)}サイクル分")
        
        # 最適化されたプロンプト
        prompt = f"""採用評価エキスパートとして、レジュメと求人要件のマッチング評価を行います。

# 入力データ
## 候補者レジュメ
{state.resume}

## 求人要件
{state.job_description}

## 追加情報
{state.job_memo}
{additional_info}
{history_text}

# 評価基準（配点）
- 必須要件: 60%（最重要 - 1つでも欠けると最大40点減点）
- 実務経験の深さ: 25%（2年未満:-15点、5年以上:+10点）
- システム/技術力: 15%（具体的な実績必須）

# スコアレンジ
- 0-30点: 明らかに不適格（必須要件を複数欠く）
- 31-50点: 要件不足（重要な必須要件を欠く）
- 51-70点: 条件付き検討可能
- 71-85点: 推奨
- 86-100点: 強く推奨

# 出力フォーマット（厳密に従うこと）
適合度スコア: [0-100の整数]
確信度: [低/中/高]

主な強み:
- [強み1]
- [強み2]
- [強み3]

主な懸念点:
- [懸念1]
- [懸念2]

評価サマリー: [必須要件の充足状況を明確に記載。「○○経験2年」など具体的年数必須。「情報不足」「面接で確認」等の曖昧表現は使用禁止。不足要件は「なし」と明記。最後に重要な合致/不合致ポイントを1文でまとめる]

# 経験年数の評価
- 該当業務経験1年未満: 「経験不足」として大幅減点（-20点）
- 2-3年: 標準評価
- 5年以上: 加点対象（+10点）
※「○○業務経験あり」だけでなく、必ず経験年数を抽出して評価

# 技術評価のポイント
- 具体的なシステム名・ツール名の記載: 加点
- 「業務効率化」「システム導入」の具体的成果: 必須
- プログラミング・自動化スキル: 大幅加点（+15点）

# 制約
- レジュメ記載内容のみで判断
- 推測・期待での評価禁止
- 「面接で確認」「情報不足」等の曖昧表現は使用禁止
- 不明な要件は「記載なし」として減点対象
- ミッション・バリューへの共感度は評価対象外
- 企業文化適合性は考慮しない"""
        
        print(f"  LLMにプロンプト送信中... (文字数: {len(prompt)})")
        response = self.model.generate_content(prompt)
        print(f"  LLMから応答受信")
        
        # デバッグモードの場合、生の応答を表示
        if os.getenv('DEBUG_MODE'):
            print(f"  LLM応答（最初の500文字）:")
            print(f"    {response.text[:500]}")
            print("    ...")
        
        evaluation = self._parse_evaluation(response.text)
        print(f"  評価結果パース完了")
        
        # 状態を更新
        state.current_evaluation = evaluation
        self.state = "completed"
        
        return state
    
    def _format_additional_info(self, search_results: Dict) -> str:
        """検索結果をフォーマット"""
        if not search_results:
            return ""
        
        text = "\n### Web検索による追加情報"
        for key, result in search_results.items():
            text += f"\n\n**{key}**"
            text += f"\n{result.summary}"
            if result.sources:
                text += f"\n情報源: {', '.join(result.sources[:2])}"
        
        return text
    
    def _format_history(self, history: List) -> str:
        """評価履歴をフォーマット"""
        if not history:
            return ""
        
        text = "\n### 過去の評価推移"
        for cycle in history:
            text += f"\n\n**サイクル{cycle.cycle_number}**"
            text += f"\n- スコア: {cycle.evaluation.score}点（確信度: {cycle.evaluation.confidence}）"
            text += f"\n- 主な懸念: {cycle.evaluation.concerns[0] if cycle.evaluation.concerns else 'なし'}"
            if len(cycle.search_results) > 0:
                text += f"\n- 収集情報: {len(cycle.search_results)}件"
        
        return text
    
    def _parse_evaluation(self, text: str) -> EvaluationResult:
        """LLMの出力を評価結果にパース"""
        print(f"  パース開始（応答文字数: {len(text)}）")
        
        # デフォルト値
        score = 50
        confidence = "低"
        strengths = []
        concerns = []
        summary = ""
        
        # 各セクションを探す
        lines = text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # スコアを探す（複数のパターンに対応）
            if "適合度スコア" in line and ":" in line:
                try:
                    # 数値部分を抽出
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        score = int(numbers[0])
                        print(f"    スコア検出: {score}")
                except Exception as e:
                    print(f"    スコアパースエラー: {e}")
            
            # 確信度を探す
            elif "確信度" in line and ":" in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    conf_text = parts[1].strip()
                    if "低" in conf_text:
                        confidence = "低"
                    elif "中" in conf_text:
                        confidence = "中"
                    elif "高" in conf_text:
                        confidence = "高"
                    print(f"    確信度検出: {confidence}")
            
            # セクションの開始を検出
            elif "強み" in line and (":" in line or "：" in line):
                current_section = "strengths"
            elif "懸念" in line and (":" in line or "：" in line):
                current_section = "concerns"
            elif ("評価サマリー" in line or "サマリー" in line) and (":" in line or "：" in line):
                parts = line.split(':', 1) if ':' in line else line.split('：', 1)
                if len(parts) > 1:
                    summary = parts[1].strip()
                current_section = "summary"
            
            # 箇条書き項目を収集
            elif current_section and (line.startswith("- ") or line.startswith("・ ") or line.startswith("* ")):
                item = line[2:].strip()
                if current_section == "strengths" and len(strengths) < 3:
                    strengths.append(item)
                elif current_section == "concerns" and len(concerns) < 3:
                    concerns.append(item)
            
            # サマリーの続きを収集
            elif current_section == "summary" and line and not line.startswith('-'):
                summary += ' ' + line
        
        # 情報が取得できなかった場合の処理
        if not strengths:
            print("    警告: 強みが検出できませんでした")
            strengths = ["候補者の具体的な強みを評価中"]
        if not concerns:
            print("    警告: 懸念点が検出できませんでした")
            concerns = ["特筆すべき懸念点なし"]
        if not summary:
            print("    警告: サマリーが検出できませんでした")
            # 全テキストから「評価サマリー」を探す別の方法
            for i, line in enumerate(lines):
                if "評価サマリー" in line:
                    # 次の行から内容を取得
                    if i + 1 < len(lines):
                        summary = lines[i + 1].strip()
                        # 空行まで続きを取得
                        for j in range(i + 2, len(lines)):
                            if lines[j].strip() and not lines[j].startswith('-'):
                                summary += ' ' + lines[j].strip()
                            else:
                                break
                    break
            
            if not summary:
                summary = "総合的な評価を実施中"
        
        print(f"    パース結果: スコア={score}, 確信度={confidence}, 強み={len(strengths)}件, 懸念={len(concerns)}件")
        
        return EvaluationResult(
            score=score,
            confidence=confidence,
            strengths=strengths,
            concerns=concerns,
            summary=summary,
            raw_response=text
        )