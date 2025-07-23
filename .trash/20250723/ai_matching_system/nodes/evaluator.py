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
        
        # RAG洞察のフォーマット
        rag_insights_text = self._format_rag_insights(state)
        if hasattr(state, 'rag_insights') and state.rag_insights:
            print(f"  類似ケースの洞察を活用")
        
        # 最適化されたプロンプト
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
クライアント企業の採用成功のため、候補者を適切に評価してください。

# 入力データ
## 候補者レジュメ
{state.resume}

## 求人要件
{state.job_description}

## 追加情報
{state.job_memo}
{additional_info}
{history_text}
{rag_insights_text}

# 評価方針（厳格基準）
1. 必須要件は厳格に検証し、不明確な場合は低評価とする
2. 直接経験のみを評価対象とし、類似経験は限定的にのみ認める
3. レジュメに記載された事実・経歴のみを評価（推測・期待・可能性は一切考慮しない）
4. 歓迎要件の充足は明確な加点要素として評価する
5. 求人メモから読み取れる「本当に求める人材像」を重視する
6. 直近の経験を重視し、過去の経験は時期に応じて大幅に減点する
7. キャリアチェンジや異動で直近に異なる業務をしている場合は厳しく減点
8. 具体的な業務内容・成果が不明な経験は評価しない

# 評価基準と配点（目安）
## 必須要件（45%）
- 求人票の「求める経験・スキル」「必須」項目
- 直接的な経験が明確に確認できる場合：満点
- 類似経験での代替（以下の場合のみ認める）：最大50%の得点
  * 同一業界内での隣接領域の経験
  * 使用技術・ツールが70%以上一致
  * 業務プロセスが実質的に同等
- 経験が不明確・推測が必要な場合：最大30%の得点
- 完全に欠如している場合：該当項目は0点

### 必須要件不足のペナルティ（追加減点）
- 必須要件を1つでも完全に欠如：総合スコアから-15点
- 必須要件の50%以上が不明確/欠如：総合スコアから-25点
- 中核的な必須要件（役職・資格等）の欠如：総合スコアから-30点

### 重要：経験の時期による調整（厳格化）
- 直近3年以内の経験：満点（100%）
- 3-5年前の経験：30%減点（70%）
- 5-10年前の経験：50%減点（50%）
- 10年以上前の経験：70%減点（30%）
- キャリアチェンジ/異動により直近で異なる業務の場合は追加で30%減点
- 具体的な業務内容が不明な場合は追加で20%減点

## 実務遂行能力（25%）
- 業務を遂行できる実質的な能力
- 過去の実績・成果から判断
- 具体的な数値や成果があれば加点

## 歓迎要件（15%）
- 求人票の「歓迎する経験・スキル」「尚可」項目
- 1つ充足ごとに加点（最大15%）
- 特に重要な歓迎要件は2倍の加点
- 必須要件を補強する歓迎要件は追加加点

## 組織適合性（10%）
- 過去の所属企業と求人企業の類似性（業界、規模、文化）
- 実際の転職実績（成功した環境変化の経験）
- 企業規模適応性（規模差による減点：2段階差で-5点、3段階以上で-10点）
- ※注意：ポテンシャルや適応可能性ではなく、過去の実績から判断

## 突出した経歴・実績（5%）
- 必須要件の不足を補う「尖った経歴」（ボーナス要素）
- 求人に関連する分野での業界注目度（関連分野の有名企業での実績）
- 求人に活かせる希少経験（関連事業の立ち上げ、類似領域でのターンアラウンド等）
- 求人に貢献できるユニークな経歴（求人に活かせる異業種経験等）
- 求人領域での圧倒的成果（関連分野での売上○億円達成、ユーザー○万人獲得等）
- ※重要：求人との関連性がない経歴は評価しない。求人に活かせる希少な経歴のみ加点

# スコアリング指針（厳格基準）
- 85-100点: 必須要件を100%充足＋歓迎要件3個以上＋直近3年の実績
- 70-84点: 必須要件を90%以上充足＋歓迎要件1個以上
- 60-69点: 必須要件を70%以上充足、または突出した経歴で補完
- 40-59点: 必須要件の充足が70%未満
- 0-39点: 必須要件の半数以上が未充足

※重要：必須要件が不明確・推測が必要な場合は、そのことを理由に10-20点減点

※重要：突出した経歴（5%）は本当に希少な場合のみ加点。通常は必須要件と実務能力で評価

# 厳格な評価実施ルール
1. 禁止事項（これらの表現・考え方は一切使用禁止）：
   - 「可能性がある」「期待できる」「思われる」「推測される」
   - 「面接で確認すれば」「入社後に習得可能」「ポテンシャルがある」
   - 「おそらく」「恐らく」「だろう」「かもしれない」

2. 必須の評価姿勢：
   - レジュメに明記されていないスキル・経験は「ない」と判断
   - 不明確な記載は低評価の根拠とする
   - 類似経験は厳密に判定し、安易に代替として認めない
   - CFO経験≠経理経験、マネジメント経験≠実務経験として厳密に区別

3. 減点の明確化：
   - 必須要件が不明確：-10点以上
   - 直近経験でない：時期に応じて大幅減点
   - 具体的成果が不明：-5点以上

# 出力フォーマット
適合度スコア: [0-100の整数]
確信度: [低/中/高]

主な強み:
- [必須要件との合致点を優先的に記載]
- [歓迎要件の充足があれば明記]
- [突出した経歴・実績があれば強調（「○○での実績は業界でも稀少」等）]
- [「会ってみたい」と思わせる要素を明記]

主な懸念点:
- [必須要件の不足を最優先で記載（「○○の必須要件を満たしていない」と明確に）]
- [必須要件不足による具体的な業務遂行上のリスク]
- [その他の懸念事項を事実ベースで記載]
- [※「面接で確認可能」「改善可能」等の楽観的コメントは一切記載しない]
- [※必須要件を1つでも満たさない場合、それは致命的な問題として扱う]

評価サマリー:
[以下を含む総合評価]
- 必須要件の充足度（○個中○個充足、類似経験での代替○個、完全欠如○個）
- 【重要】必須要件不足の場合、その業務遂行上の具体的影響
- 経験の直近性（直近の経験か、過去の経験かを明記）
- 歓迎要件の充足度（○個中○個充足）
- 突出した経歴（ある場合は「○○の実績は採用市場でも希少」等と明記）
- 企業規模適応性（経歴企業と求人企業の規模差があれば明記）
- 企業が本質的に求める人材像との適合性（過去実績ベース）
- この候補者の実績・経験に基づく価値
- 総合的な推薦判断（必須要件不足がある場合は、その重大性を明記）

# 評価の注意点
- 必須要件と歓迎要件を明確に区別
- 必須要件の不足は致命的な問題として扱う
- 必須要件を1つでも満たさない場合、その影響を懸念点で詳細に説明
- 歓迎要件は加点要素として積極的に評価
- レジュメに記載された事実・経歴のみで判断（ポテンシャルや可能性は評価しない）
- 「面接でカバー可能」「今後の成長に期待」等の楽観的評価は一切含めない
- 最終的に「現時点の経歴でクライアントがこの候補者と面談すべきか」で判断
- 必須要件不足の候補者は原則として推薦しない姿勢で評価"""
        
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
    
    def _format_rag_insights(self, state) -> str:
        """RAG洞察をフォーマット"""
        if not hasattr(state, 'rag_insights') or not state.rag_insights:
            return ""
        
        insights = state.rag_insights
        text = "\n### 類似ケースからの洞察"
        
        # クライアント評価傾向
        if insights.get('client_tendency'):
            tendency = insights['client_tendency']
            text += f"\n- 類似ケースでの最頻出評価: {tendency['most_common_evaluation']} ({tendency['percentage']:.1f}%)"
        
        # リスク要因
        if insights.get('risk_factors'):
            text += "\n- 注意すべきリスク要因:"
            for risk in insights['risk_factors'][:2]:  # 上位2件
                text += f"\n  * {risk['pattern']}: {risk['reason']}"
        
        # 成功パターン
        if insights.get('success_patterns'):
            text += "\n- 成功パターン:"
            for pattern in insights['success_patterns'][:1]:  # 上位1件
                text += f"\n  * {pattern['evaluation']}: {pattern['key_factor']}"
        
        return text
    
    def _format_additional_info(self, search_results: Dict) -> str:
        """検索結果をフォーマット"""
        if not search_results:
            return ""
        
        text = "\n### Web検索による追加情報"
        
        # 企業規模比較を優先的に表示
        if "企業規模比較" in search_results:
            result = search_results["企業規模比較"]
            text += f"\n\n**企業規模比較（重要）**"
            text += f"\n{result.summary}"
            text += f"\n※規模差が大きい場合は適応リスクとして評価に反映すること"
            if result.sources:
                text += f"\n情報源: {', '.join(result.sources[:2])}"
        
        # その他の検索結果
        for key, result in search_results.items():
            if key != "企業規模比較":
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
        interview_points = []
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