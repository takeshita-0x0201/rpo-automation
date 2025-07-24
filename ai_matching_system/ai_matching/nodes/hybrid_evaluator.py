"""
ハイブリッド評価ノード
信頼度に基づいてルールベースとセマンティック評価を使い分ける
"""

import os
import json
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai
from datetime import datetime

from .base import BaseNode, ResearchState, EvaluationResult
from .evaluator import EvaluatorNode
from ..utils.semantic_guards import SemanticGuards
from ..utils.evaluation_logger import get_evaluation_logger
from ..utils.ab_testing import get_ab_testing_framework, TestGroup
from ..utils.feedback_collector import get_feedback_collector, FeedbackType


class HybridEvaluatorNode(EvaluatorNode):
    """ハイブリッド評価アプローチを実装するノード"""
    
    def __init__(self, api_key: str, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        super().__init__(api_key, supabase_url, supabase_key)
        self.evaluation_log = []
        
    async def process(self, state: ResearchState) -> ResearchState:
        """信頼度に基づいて評価アプローチを選択"""
        self.state = "processing"
        
        print(f"  ハイブリッド評価を開始（サイクル{state.current_cycle}）")
        
        # A/Bテストのグループを取得
        ab_testing = get_ab_testing_framework()
        experiment_name = os.getenv("CURRENT_AB_EXPERIMENT", "evaluation_improvement_v1")
        test_group = TestGroup.CONTROL
        
        if hasattr(state, 'candidate_id') and hasattr(state, 'job_id'):
            test_group = ab_testing.get_test_group(
                experiment_name,
                state.candidate_id,
                state.job_id
            )
            print(f"  A/Bテストグループ: {test_group.value}")
        
        # 1. 情報の信頼度を評価
        confidence_analysis = self._analyze_information_confidence(state)
        print(f"  情報信頼度: {confidence_analysis['overall_confidence']:.1%}")
        
        # 2. 評価アプローチの選択（A/Bテストグループも考慮）
        approach = self._select_evaluation_approach_with_ab(confidence_analysis, test_group)
        print(f"  選択されたアプローチ: {approach}")
        
        # 3. 選択されたアプローチで評価実行
        if approach == "rule_based":
            evaluation = await self._rule_based_evaluation(state)
        elif approach == "semantic_heavy":
            evaluation = await self._semantic_evaluation(state)
        else:  # hybrid
            evaluation = await self._hybrid_evaluation(state)
        
        # 4. 評価理由のログ記録
        self._log_evaluation_reasoning(state, confidence_analysis, approach, evaluation)
        
        # 5. A/Bテスト結果の記録
        if hasattr(state, 'candidate_id') and hasattr(state, 'job_id'):
            ab_testing.record_result(
                experiment_name,
                state.candidate_id,
                state.job_id,
                {
                    "confidence": confidence_analysis['overall_confidence'],
                    "approach": approach
                },
                evaluation.score
            )
        
        # 状態を更新
        state.current_evaluation = evaluation
        self.state = "completed"
        
        return state
    
    def _analyze_information_confidence(self, state: ResearchState) -> Dict:
        """レジュメ情報の信頼度を分析"""
        analysis = {
            "resume_detail_level": 0.0,
            "keyword_clarity": 0.0,
            "experience_specificity": 0.0,
            "quantitative_data": 0.0,
            "overall_confidence": 0.0,
            "missing_critical_info": []
        }
        
        resume = state.resume
        
        # 1. レジュメの詳細度を評価
        word_count = len(resume.split())
        if word_count > 1000:
            analysis["resume_detail_level"] = 0.9
        elif word_count > 500:
            analysis["resume_detail_level"] = 0.7
        elif word_count > 300:
            analysis["resume_detail_level"] = 0.5
        else:
            analysis["resume_detail_level"] = 0.3
        
        # 2. キーワードの明確性
        clear_keywords = ["営業", "開発", "管理", "経理", "マーケティング", "エンジニア"]
        keyword_count = sum(1 for kw in clear_keywords if kw in resume)
        analysis["keyword_clarity"] = min(1.0, keyword_count * 0.2)
        
        # 3. 経験の具体性
        specific_indicators = ["年", "ヶ月", "人", "件", "円", "%", "社"]
        specific_count = sum(1 for ind in specific_indicators if ind in resume)
        analysis["experience_specificity"] = min(1.0, specific_count * 0.15)
        
        # 4. 定量的データの有無
        import re
        numbers = re.findall(r'\d+', resume)
        analysis["quantitative_data"] = min(1.0, len(numbers) * 0.05)
        
        # 5. 重要情報の欠落チェック
        if "営業" not in resume and "sales" not in resume.lower():
            if hasattr(state, 'job_description') and '営業' in state.job_description:
                analysis["missing_critical_info"].append("営業経験の明示的な記載なし")
        
        # 総合信頼度
        weights = {
            "resume_detail_level": 0.3,
            "keyword_clarity": 0.3,
            "experience_specificity": 0.2,
            "quantitative_data": 0.2
        }
        
        analysis["overall_confidence"] = sum(
            analysis[key] * weight 
            for key, weight in weights.items()
        )
        
        return analysis
    
    def _select_evaluation_approach(self, confidence_analysis: Dict) -> str:
        """信頼度に基づいて評価アプローチを選択"""
        confidence = confidence_analysis["overall_confidence"]
        
        # セマンティックガードの推奨も考慮
        uncertainty = 1.0 - confidence
        suggested_approach = SemanticGuards.suggest_evaluation_approach(
            job_type="general",  # TODO: 実際の職種を渡す
            uncertainty_level=uncertainty
        )
        
        # 最終決定
        if confidence > 0.8:
            return "rule_based"
        elif confidence < 0.4 or len(confidence_analysis["missing_critical_info"]) > 0:
            return "semantic_heavy"
        else:
            return "hybrid"
    
    def _select_evaluation_approach_with_ab(self, confidence_analysis: Dict, test_group: TestGroup) -> str:
        """A/Bテストグループも考慮して評価アプローチを選択"""
        # A/Bテストグループによる強制的なアプローチ選択
        if test_group == TestGroup.CONTROL:
            # コントロール群は従来のロジック
            return self._select_evaluation_approach(confidence_analysis)
        elif test_group == TestGroup.VARIANT_A:
            # バリアントAは常にセマンティック評価
            return "semantic_heavy"
        elif test_group == TestGroup.VARIANT_B:
            # バリアントBは常にハイブリッド評価
            return "hybrid"
        
        # デフォルト
        return self._select_evaluation_approach(confidence_analysis)
    
    async def _rule_based_evaluation(self, state: ResearchState) -> EvaluationResult:
        """ルールベースの評価（従来の厳格な評価）"""
        print("  ルールベース評価を実行")
        # 従来のプロンプトを使用（一部調整）
        return await self._evaluate_with_approach(state, "rule_based")
    
    async def _semantic_evaluation(self, state: ResearchState) -> EvaluationResult:
        """セマンティック重視の評価"""
        print("  セマンティック評価を実行")
        return await self._evaluate_with_approach(state, "semantic")
    
    async def _hybrid_evaluation(self, state: ResearchState) -> EvaluationResult:
        """ハイブリッド評価"""
        print("  ハイブリッド評価を実行")
        
        # 両方のアプローチで評価
        rule_eval = await self._evaluate_with_approach(state, "rule_based")
        semantic_eval = await self._evaluate_with_approach(state, "semantic")
        
        # スコアの重み付け平均
        rule_weight = 0.4
        semantic_weight = 0.6
        
        hybrid_score = int(
            rule_eval.score * rule_weight + 
            semantic_eval.score * semantic_weight
        )
        
        # 強みと懸念点の統合
        strengths = []
        concerns = []
        
        # ルールベースの強み（確実性の高いもの）
        for strength in rule_eval.strengths[:2]:
            strengths.append(f"[確実] {strength}")
        
        # セマンティックの強み（可能性のあるもの）
        for strength in semantic_eval.strengths[:1]:
            if strength not in rule_eval.strengths:
                strengths.append(f"[推定] {strength}")
        
        # 懸念点も同様に統合
        for concern in rule_eval.concerns[:2]:
            concerns.append(f"[確実] {concern}")
        
        for concern in semantic_eval.concerns[:1]:
            if concern not in rule_eval.concerns:
                concerns.append(f"[要確認] {concern}")
        
        # サマリーの生成
        summary = f"ハイブリッド評価により、確実な要素と推定要素を総合的に判断。"
        summary += f"ルールベース評価: {rule_eval.score}点、セマンティック評価: {semantic_eval.score}点"
        
        return EvaluationResult(
            score=hybrid_score,
            confidence="中",
            strengths=strengths,
            concerns=concerns,
            summary=summary,
            raw_response=f"Rule-based: {rule_eval.raw_response}\n\nSemantic: {semantic_eval.raw_response}"
        )
    
    async def _evaluate_with_approach(self, state: ResearchState, approach: str) -> EvaluationResult:
        """指定されたアプローチで評価を実行"""
        
        # 基本的な情報収集（親クラスのメソッドを活用）
        additional_info = self._format_additional_info(state.search_results)
        history_text = self._format_history(state.evaluation_history)
        rag_insights_text = self._format_rag_insights(state)
        candidate_info = await self._get_candidate_info(state)
        guard_insights = self._apply_semantic_guards(state)
        
        # アプローチ別のプロンプト調整
        if approach == "rule_based":
            evaluation_policy = """
# 評価方針（ルールベース - 厳格基準）
1. レジュメに明記された情報のみで判断
2. 直接的な経験記載を重視
3. 推測や可能性は一切考慮しない
4. 必須要件は100%の充足を求める
"""
        else:  # semantic
            evaluation_policy = """
# 評価方針（セマンティック - 柔軟理解）
1. 業務の本質的な類似性を重視
2. 文脈から合理的に推測できる能力も評価
3. 間接的な経験も適切に価値づけ
4. 候補者の潜在的な適合性を総合的に判断

重要：以下の要素がある場合は営業経験として認識すること：
- 「主担当」「担当案件」+ 顧客関連の文脈
- 「REIT案件」「事業会社」などの外部クライアント業務
- 「統括」「進捗管理」+ チーム/プロジェクトの文脈
"""
        
        # プロンプトの構築
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
以下の評価方針に従って候補者を評価してください。

# 入力データ
## 候補者レジュメ
{state.resume}

## 候補者情報
{candidate_info}

## 求人要件
{state.job_description}

## 追加情報
{state.job_memo}

{additional_info}
{history_text}
{rag_insights_text}
{guard_insights}

{evaluation_policy}

# 評価基準と配点
[親クラスと同じ評価基準を使用]

# 出力フォーマット
適合度スコア: [0-100の整数]
確信度: [低/中/高]

主な強み:
- [評価アプローチに応じた強み]

主な懸念点:
- [評価アプローチに応じた懸念点]

評価サマリー:
[アプローチ名を明記した総合評価]
"""
        
        # LLMで評価
        response = self.model.generate_content(prompt)
        return self._parse_evaluation(response.text)
    
    def _log_evaluation_reasoning(self, state: ResearchState, confidence_analysis: Dict, 
                                approach: str, evaluation: EvaluationResult):
        """評価理由をログに記録"""
        candidate_id = getattr(state, 'candidate_id', 'unknown')
        job_id = getattr(state, 'job_id', 'unknown')
        
        # 評価データ
        evaluation_data = {
            "cycle": state.current_cycle,
            "approach": approach,
            "score": evaluation.score,
            "confidence": evaluation.confidence,
            "information_confidence": confidence_analysis["overall_confidence"],
            "strengths": evaluation.strengths,
            "concerns": evaluation.concerns,
            "confidence_analysis": confidence_analysis,
            "approach_reason": self._get_approach_reason(approach, confidence_analysis)
        }
        
        # 決定事項
        decisions = [
            {
                "type": "approach_selection",
                "key": "selected_approach",
                "value": approach,
                "confidence": confidence_analysis["overall_confidence"],
                "reasoning": self._get_approach_reason(approach, confidence_analysis)
            }
        ]
        
        # セマンティック検出結果
        detections = []
        if hasattr(state, 'semantic_detections'):
            for detection in state.semantic_detections:
                detections.append({
                    "type": detection['type'],
                    "text": detection['text'],
                    "confidence": detection['confidence'],
                    "evidence": detection['evidence']
                })
        
        # ロガーを使用して記録
        logger = get_evaluation_logger()
        log_id = logger.log_evaluation(
            candidate_id=candidate_id,
            job_id=job_id,
            evaluation_data=evaluation_data,
            decisions=decisions,
            detections=detections
        )
        
        print(f"  評価ログID: {log_id}")
    
    def _get_approach_reason(self, approach: str, confidence_analysis: Dict) -> str:
        """アプローチ選択の理由を説明"""
        confidence = confidence_analysis["overall_confidence"]
        
        if approach == "rule_based":
            return f"高い情報信頼度（{confidence:.1%}）により、ルールベース評価を選択"
        elif approach == "semantic_heavy":
            reasons = [f"低い情報信頼度（{confidence:.1%}）"]
            if confidence_analysis["missing_critical_info"]:
                reasons.append(f"重要情報の欠落: {', '.join(confidence_analysis['missing_critical_info'])}")
            return "、".join(reasons) + "により、セマンティック評価を選択"
        else:
            return f"中程度の情報信頼度（{confidence:.1%}）により、ハイブリッド評価を選択"