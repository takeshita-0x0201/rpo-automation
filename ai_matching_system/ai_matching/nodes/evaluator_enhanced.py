"""
強化された評価ノード（説明可能性を向上）
"""

import os
import re
from typing import Dict, List, Optional
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

from .base import BaseNode, ResearchState, EvaluationResult, ScoreDetail
from ..utils.dynamic_weight_adjuster import DynamicWeightAdjuster, WeightProfile
from ..utils.uncertainty_quantifier import UncertaintyQuantifier
from ..utils.contradiction_resolver import ContradictionResolver
from ..utils.meta_learner import MetaLearner
from ..utils.career_continuity_analyzer_v2 import CareerContinuityAnalyzerV2
from ..utils.age_experience_analyzer import AgeExperienceAnalyzer


class EnhancedEvaluatorNode(BaseNode):
    """説明可能性を強化した評価ノード"""
    
    def __init__(self, api_key: str, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        super().__init__("EnhancedEvaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Supabaseクライアントの初期化
        self.supabase_client = None
        if supabase_url and supabase_key:
            self.supabase_client = create_client(supabase_url, supabase_key)
        
        # 動的重み付け調整器の初期化
        self.weight_adjuster = DynamicWeightAdjuster()
        
        # 不確実性定量化器の初期化
        self.uncertainty_quantifier = UncertaintyQuantifier()
        
        # 矛盾解決器の初期化
        self.contradiction_resolver = ContradictionResolver()
        
        # メタ学習器の初期化
        self.meta_learner = MetaLearner()
        
        # キャリア継続性分析器の初期化（LLMモードを有効化）
        self.career_analyzer = CareerContinuityAnalyzerV2(use_llm=True, gemini_api_key=api_key)
        
        # 年齢・経験社数分析器の初期化
        self.age_experience_analyzer = AgeExperienceAnalyzer()
    
    def _parse_evaluation_enhanced(self, text: str, weight_profile: Optional[WeightProfile] = None) -> EvaluationResult:
        """LLMの出力を詳細な評価結果にパース"""
        lines = text.strip().split('\n')
        
        score = 0
        confidence = "低"
        strengths = []
        concerns = []
        summary = ""
        score_breakdown = {}
        evidence_map = {}
        
        current_section = None
        current_category = None
        
        for line in lines:
            line = line.strip()
            
            # スコアを探す
            if "適合度スコア" in line and ":" in line:
                try:
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        score = int(numbers[0])
                except Exception:
                    pass
            
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
            
            # スコア内訳のセクション
            elif "必須要件" in line and "点満点" in line:
                current_category = "required_skills"
                score_breakdown[current_category] = self._init_score_detail("必須要件", 45)
            elif "実務遂行能力" in line and "点満点" in line:
                current_category = "practical_ability"
                score_breakdown[current_category] = self._init_score_detail("実務遂行能力", 25)
            elif "歓迎要件" in line and "点満点" in line:
                current_category = "preferred_skills"
                score_breakdown[current_category] = self._init_score_detail("歓迎要件", 15)
            elif "組織適合性" in line and "点満点" in line:
                current_category = "organizational_fit"
                score_breakdown[current_category] = self._init_score_detail("組織適合性", 10)
            elif "突出した経歴" in line and "点満点" in line:
                current_category = "outstanding_career"
                score_breakdown[current_category] = self._init_score_detail("突出した経歴", 5)
            
            # スコア内訳の項目をパース
            elif current_category and ":" in line and "/" in line and "-" in line:
                self._parse_score_item(line, score_breakdown[current_category], evidence_map)
            
            # 小計を探す
            elif current_category and "小計:" in line:
                match = re.search(r'(\d+(?:\.\d+)?)/(\d+)', line)
                if match:
                    score_breakdown[current_category].actual_score = float(match.group(1))
            
            # セクションの開始を検出
            elif "主な強み" in line:
                current_section = "strengths"
                current_category = None
            elif "主な懸念" in line:
                current_section = "concerns"
                current_category = None
            elif "評価サマリー" in line:
                current_section = "summary"
                current_category = None
            
            # 箇条書き項目を収集
            elif current_section and (line.startswith("- ") or line.startswith("・ ") or line.startswith("* ")):
                item = line[2:].strip()
                if current_section == "strengths" and len(strengths) < 5:
                    strengths.append(item)
                elif current_section == "concerns" and len(concerns) < 5:
                    concerns.append(item)
            
            # サマリーの続きを収集
            elif current_section == "summary" and line and not line.startswith('-'):
                if summary:
                    summary += ' ' + line
                else:
                    summary = line
        
        # デフォルト値の設定
        if not strengths:
            strengths = ["候補者の具体的な強みを評価中"]
        if not concerns:
            concerns = ["特筆すべき懸念点なし"]
        if not summary:
            summary = "総合的な評価を実施中"
        
        return EvaluationResult(
            score=score,
            confidence=confidence,
            strengths=strengths,
            concerns=concerns,
            summary=summary,
            raw_response=text,
            score_breakdown=score_breakdown if score_breakdown else None,
            evidence_map=evidence_map if evidence_map else None
        )
    
    def _init_score_detail(self, category: str, max_score: float) -> ScoreDetail:
        """ScoreDetailの初期化"""
        return ScoreDetail(
            category=category,
            max_score=max_score,
            actual_score=0,
            items=[],
            reasoning=""
        )
    
    def _parse_score_item(self, line: str, score_detail: ScoreDetail, evidence_map: Dict):
        """スコア項目のパース"""
        try:
            # 形式: "- 項目名: 点数/配点 - 根拠"
            parts = line.split(":", 1)
            if len(parts) >= 2:
                item_name = parts[0].strip("- ").strip()
                rest = parts[1].strip()
                
                # 点数と根拠を分離
                score_parts = rest.split(" - ", 1)
                if len(score_parts) >= 1:
                    # 点数をパース
                    score_match = re.search(r'(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)', score_parts[0])
                    if score_match:
                        actual = float(score_match.group(1))
                        max_val = float(score_match.group(2))
                        
                        evidence = score_parts[1] if len(score_parts) > 1 else ""
                        
                        # itemsに追加
                        score_detail.items.append({
                            "name": item_name,
                            "score": actual,
                            "max_score": max_val,
                            "evidence": evidence
                        })
                        
                        # evidence_mapに追加
                        if item_name not in evidence_map:
                            evidence_map[item_name] = []
                        if evidence:
                            evidence_map[item_name].append(evidence)
        except Exception as e:
            print(f"    スコア項目パースエラー: {e}")
    
    def generate_evaluation_report(self, evaluation: EvaluationResult) -> str:
        """評価結果の詳細レポートを生成"""
        report = []
        report.append("# 候補者評価レポート")
        report.append(f"\n## 総合評価")
        report.append(f"- **スコア**: {evaluation.score}/100点")
        report.append(f"- **確信度**: {evaluation.confidence}")
        
        if evaluation.score_breakdown:
            report.append(f"\n## スコア詳細内訳")
            for category_key, detail in evaluation.score_breakdown.items():
                report.append(f"\n### {detail.category} ({detail.actual_score:.1f}/{detail.max_score}点)")
                if detail.items:
                    for item in detail.items:
                        report.append(f"- **{item['name']}**: {item['score']:.1f}/{item['max_score']:.1f}点")
                        if item.get('evidence'):
                            report.append(f"  - 根拠: {item['evidence']}")
        
        report.append(f"\n## 主な強み")
        for strength in evaluation.strengths:
            report.append(f"- {strength}")
        
        report.append(f"\n## 主な懸念点")
        for concern in evaluation.concerns:
            report.append(f"- {concern}")
        
        if evaluation.evidence_map:
            report.append(f"\n## 評価根拠の詳細")
            for key, evidences in evaluation.evidence_map.items():
                report.append(f"\n### {key}")
                for evidence in evidences:
                    report.append(f"- {evidence}")
        
        report.append(f"\n## 評価サマリー")
        report.append(evaluation.summary)
        
        # 不確実性レポートを追加
        if hasattr(evaluation, 'uncertainty_report') and evaluation.uncertainty_report:
            report.append(f"\n## 評価の不確実性分析")
            uncertainty_summary = self.uncertainty_quantifier.format_uncertainty_summary(evaluation.uncertainty_report)
            report.append(uncertainty_summary)
        
        # 矛盾解決レポートを追加
        if hasattr(evaluation, 'contradiction_report') and evaluation.contradiction_report:
            report.append(f"\n## 情報の矛盾と解決")
            contradiction_summary = self.contradiction_resolver.format_contradiction_report(evaluation.contradiction_report)
            report.append(contradiction_summary)
        
        # キャリア継続性レポートを追加
        if hasattr(evaluation, 'career_assessment') and evaluation.career_assessment:
            report.append(f"\n## キャリア継続性分析")
            career_summary = self.career_analyzer.format_continuity_report(evaluation.career_assessment)
            report.append(career_summary)
        
        # 年齢・経験社数レポートを追加
        if hasattr(evaluation, 'age_experience_assessment') and evaluation.age_experience_assessment:
            report.append(f"\n## 年齢・経験社数適合性")
            age_exp_summary = self.age_experience_analyzer.format_assessment_report(evaluation.age_experience_assessment)
            report.append(age_exp_summary)
        
        return '\n'.join(report)
    
    async def process(self, state: ResearchState) -> ResearchState:
        """候補者を現在の情報で評価（強化版）"""
        self.state = "processing"
        
        print(f"  候補者評価を開始（強化版・サイクル{state.current_cycle}）")
        
        # 追加情報のフォーマット
        additional_info = self._format_additional_info(state.search_results)
        if additional_info:
            print(f"  追加情報を含めて評価: {len(state.search_results)}件の検索結果")
        
        # 評価履歴のフォーマット
        history_text = self._format_history(state.evaluation_history)
        if state.evaluation_history:
            print(f"  過去の評価履歴を考慮: {len(state.evaluation_history)}サイクル分")
        
        # 候補者情報を取得
        candidate_info = await self._get_candidate_info(state)
        
        # 動的重み付けを計算
        job_data = {
            'title': state.job_description[:100] if state.job_description else '',
            'job_description': state.job_description,
            'memo': state.job_memo
        }
        weight_profile = self.weight_adjuster.adjust_weights(job_data, state.structured_job_data)
        
        # メタ学習による重み調整
        job_category = self._extract_job_category(job_data, state.structured_job_data)
        if job_category:
            meta_weights = self.meta_learner.get_adjusted_weights(job_category)
            # メタ学習の重みを反映（50%の影響度）
            for feature in ['required_skills', 'practical_ability', 'preferred_skills', 'organizational_fit', 'outstanding_career']:
                if feature in meta_weights:
                    original = getattr(weight_profile, feature)
                    adjusted = original * 0.5 + meta_weights.get(feature, original) * 0.5
                    setattr(weight_profile, feature, adjusted)
            weight_profile.normalize()
            print(f"  メタ学習による重み調整を適用")
        
        weight_explanation = self.weight_adjuster.get_weight_explanation(weight_profile)
        print(f"  動的重み付け適用: {weight_explanation}")
        
        # キャリア継続性分析
        required_skills = self._extract_required_skills(state)
        required_experience = state.job_description if state.job_description else state.job_memo
        
        career_assessment = await self.career_analyzer.analyze_career_continuity(
            resume_text=state.resume,
            required_skills=required_skills,
            required_experience=required_experience
        )
        
        print(f"  キャリア継続性分析完了:")
        print(f"    直近の関連経験: {'あり' if career_assessment.has_recent_relevant_experience else 'なし'}")
        if career_assessment.months_since_relevant_experience is not None:
            print(f"    経験ブランク: {career_assessment.months_since_relevant_experience}ヶ月")
        print(f"    減点率: {career_assessment.penalty_score:.0%}")
        
        if career_assessment.career_change_detected:
            print(f"    ⚠️ キャリアチェンジが検出されました")
        if career_assessment.department_change_detected:
            print(f"    ⚠️ 部署異動が検出されました")
        
        # 年齢・経験社数分析
        age_experience_assessment = self.age_experience_analyzer.analyze_age_experience_fit(
            candidate_age=state.candidate_age,
            total_companies=state.enrolled_company_count or 1,
            resume_text=state.resume
        )
        
        print(f"  年齢・経験社数分析完了:")
        if age_experience_assessment.candidate_age:
            print(f"    年齢: {age_experience_assessment.candidate_age}歳")
        print(f"    経験社数: {age_experience_assessment.total_companies}社")
        if age_experience_assessment.average_tenure:
            print(f"    平均在籍年数: {age_experience_assessment.average_tenure:.1f}年")
        print(f"    転職頻度評価: {age_experience_assessment.job_change_frequency}")
        print(f"    安定性スコア: {age_experience_assessment.stability_score:.0%}")
        print(f"    評価調整係数: {age_experience_assessment.adjustment_factor:.2f}")
        
        if age_experience_assessment.risk_factors:
            print(f"    ⚠️ リスク要因: {', '.join(age_experience_assessment.risk_factors[:2])}")
        
        # 強化されたプロンプト（詳細なスコア内訳を要求）
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
クライアント企業の採用成功のため、候補者を適切に評価してください。

# 入力データ
## 候補者レジュメ
{state.resume}

## 候補者情報
{candidate_info}

## 求人要件
{state.job_description}

## 追加情報
{state.job_memo}

{self._format_structured_job_data(state) if hasattr(state, 'structured_job_data') and state.structured_job_data else ''}
{additional_info}
{history_text}

# 評価方針（厳格基準）
1. 必須要件は厳格に検証し、不明確な場合は低評価とする
2. 直接経験のみを評価対象とし、類似経験は限定的にのみ認める
3. レジュメに記載された事実・経歴のみを評価（推測・期待・可能性は一切考慮しない）
4. 歓迎要件の充足は明確な加点要素として評価する
5. 求人メモから読み取れる「本当に求める人材像」を重視する

# 評価基準と配点（動的調整済み）
## 必須要件（{weight_profile.required_skills:.0%}）
- 求人票の「求める経験・スキル」「必須」項目
- 直接的な経験が明確に確認できる場合：満点
- 類似経験での代替：最大50%の得点
- 経験が不明確・推測が必要な場合：最大30%の得点
- 完全に欠如している場合：0点

## 実務遂行能力（{weight_profile.practical_ability:.0%}）
- 業務を遂行できる実質的な能力
- 過去の実績・成果から判断
- 具体的な数値や成果があれば加点

## 歓迎要件（{weight_profile.preferred_skills:.0%}）
- 求人票の「歓迎する経験・スキル」「尚可」項目
- 1つ充足ごとに加点

## 組織適合性（{weight_profile.organizational_fit:.0%}）
- 過去の所属企業と求人企業の類似性
- 実際の転職実績

## 突出した経歴・実績（{weight_profile.outstanding_career:.0%}）
- 必須要件の不足を補う「尖った経歴」
- 求人に関連する分野での業界注目度

# 重み付けの理由
{weight_explanation}

# キャリア継続性分析結果
## 経験の継続性
- 直近の関連経験: {'あり' if career_assessment.has_recent_relevant_experience else 'なし'}
- 経験ブランク: {career_assessment.months_since_relevant_experience or '計測不可'}ヶ月
- キャリアチェンジ: {'検出' if career_assessment.career_change_detected else 'なし'}
- 部署異動: {'検出' if career_assessment.department_change_detected else 'なし'}
- スキル保持率: {career_assessment.skill_retention_score:.0%}
- 推奨減点率: {career_assessment.penalty_score:.0%}

## キャリア継続性の評価指針（転職市場の実態に基づく）
1. 直近3ヶ月以内のブランク：正常な転職活動期間（減点なし）
2. 4-6ヶ月のブランク：許容範囲内（5%減点）
3. 7-12ヶ月のブランク：説明が必要（10%減点）
4. 13-24ヶ月のブランク：要確認（15%減点）
5. 25ヶ月以上のブランク：詳細な確認必要（20%減点）
6. キャリアチェンジ：転用可能スキルに応じて0-15%減点（スキル保持率が高ければ軽減）
7. 部署異動：3%減点（軽微な影響）

※転用可能スキル（コミュニケーション、問題解決、リーダーシップ等）が高い場合は減点を軽減

# 年齢・経験社数分析結果
## 基本情報
- 年齢: {age_experience_assessment.candidate_age or '不明'}歳
- 経験社数: {age_experience_assessment.total_companies}社
- 推定キャリア年数: {age_experience_assessment.career_years or '不明'}年
- 平均在籍年数: {age_experience_assessment.average_tenure or '不明'}年

## 適合性評価
- 転職頻度: {age_experience_assessment.job_change_frequency}
- 安定性スコア: {age_experience_assessment.stability_score:.0%}
- 評価調整係数: {age_experience_assessment.adjustment_factor:.2f}

## 年齢・経験社数の評価指針
1. 転職頻度が「適切」の場合：標準評価
2. 転職頻度が「やや多い」の場合：軽微な減点（5%）
3. 転職頻度が「多すぎる」の場合：大幅減点（20%）、定着性への懸念を明記
4. 転職頻度が「少なすぎる」の場合：軽微な減点（10%）、適応力への懸念を明記
5. 平均在籍年数が2年未満の場合：短期離職リスクとして追加減点
6. 安定性スコアが50%未満の場合：人事リスクとして慎重評価を推奨

## リスク要因
{', '.join(age_experience_assessment.risk_factors) if age_experience_assessment.risk_factors else 'なし'}

# 出力フォーマット（詳細版）
適合度スコア: [0-100の整数]
確信度: [低/中/高]

## スコア内訳
### 必須要件（45点満点）
- [各必須要件項目]: [点数]/[配点] - [根拠となるレジュメの記載]
- 小計: [実際の点数]/45点

### 実務遂行能力（25点満点）
- [評価項目]: [点数]/[配点] - [根拠となる実績・経験]
- 小計: [実際の点数]/25点

### 歓迎要件（15点満点）
- [各歓迎要件項目]: [点数]/[配点] - [該当する経験]
- 小計: [実際の点数]/15点

### 組織適合性（10点満点）
- 企業規模適応: [点数]/5点 - [過去の所属企業と求人企業の比較]
- 文化適合: [点数]/5点 - [根拠]
- 小計: [実際の点数]/10点

### 突出した経歴（5点満点）
- [特筆すべき実績]: [点数]/5点
- 小計: [実際の点数]/5点

主な強み:
- [必須要件との合致点を優先的に記載]
- [歓迎要件の充足があれば明記]
- [突出した経歴・実績があれば強調]

主な懸念点:
- [必須要件の不足を最優先で記載]
- [必須要件不足による具体的な業務遂行上のリスク]
- [その他の懸念事項を事実ベースで記載]

評価サマリー:
[総合評価と推薦判断を含む詳細な評価結果]"""
        
        print(f"  LLMにプロンプト送信中... (文字数: {len(prompt)})")
        response = self.model.generate_content(prompt)
        print(f"  LLMから応答受信")
        
        # デバッグモードの場合、生の応答を表示
        if os.getenv('DEBUG_MODE'):
            print(f"  LLM応答（最初の500文字）:")
            print(f"    {response.text[:500]}")
            print("    ...")
        
        evaluation = self._parse_evaluation_enhanced(response.text, weight_profile)
        
        # キャリア継続性の減点を適用
        original_score = evaluation.score
        career_penalty = 0
        if career_assessment.penalty_score > 0:
            # 業界経験の評価配分を最大30%とし、異業種転職の成功率を考慮
            MAX_CAREER_PENALTY_RATIO = 0.30
            adjusted_penalty = min(career_assessment.penalty_score, MAX_CAREER_PENALTY_RATIO)
            # さらに異業種転職の成功率（約60%）を考慮し、リスクの半分を最大減点とする
            final_penalty = adjusted_penalty * 0.67  # 最大20%の減点
            career_penalty = int(original_score * final_penalty)
            evaluation.score = max(0, original_score - career_penalty)
            print(f"  キャリア継続性による減点: -{career_penalty}点 ({original_score}→{evaluation.score}) [元のペナルティ: {int(career_assessment.penalty_score*100)}%]")
        
        # 年齢・経験社数による調整を適用
        age_exp_adjusted_score = evaluation.score
        age_exp_adjustment = 0
        if age_experience_assessment.adjustment_factor != 1.0:
            age_exp_adjusted_score = int(evaluation.score * age_experience_assessment.adjustment_factor)
            age_exp_adjustment = age_exp_adjusted_score - evaluation.score
            evaluation.score = max(0, min(100, age_exp_adjusted_score))
            
            adjustment_type = "ボーナス" if age_exp_adjustment > 0 else "減点"
            print(f"  年齢・経験社数による{adjustment_type}: {age_exp_adjustment:+d}点 ({age_exp_adjusted_score-age_exp_adjustment}→{evaluation.score})")
        
        # 分析結果を評価結果に追加
        evaluation.career_assessment = career_assessment
        evaluation.age_experience_assessment = age_experience_assessment
        
        print(f"  評価結果パース完了（強化版）")
        
        # 詳細レポートを生成
        if evaluation.score_breakdown:
            detailed_report = self.generate_evaluation_report(evaluation)
            print(f"  詳細評価レポート生成完了")
            # デバッグモードの場合、レポートの一部を表示
            if os.getenv('DEBUG_MODE'):
                print(f"  レポート冒頭:")
                lines = detailed_report.split('\n')[:10]
                for line in lines:
                    print(f"    {line}")
        
        # 不確実性を定量化
        uncertainty_report = self.uncertainty_quantifier.quantify_uncertainty(
            evaluation_text=response.text,
            resume_text=state.resume,
            job_requirements=state.job_description if state.job_description else "",
            search_results=state.search_results
        )
        evaluation.uncertainty_report = uncertainty_report
        
        # 矛盾検出と解決
        if state.search_results:
            print(f"  矛盾検出・解決を開始...")
            contradictions = self.contradiction_resolver.detect_contradictions(
                resume_data={'text': state.resume},
                search_results=state.search_results,
                evaluation_text=response.text
            )
            
            if contradictions:
                print(f"  {len(contradictions)}件の矛盾を検出")
                # 信頼性スコアを取得（利用可能な場合）
                reliability_scores = {}
                if hasattr(self, 'reliability_scorer') and self.reliability_scorer:
                    for source_name, result in state.search_results.items():
                        if result.sources:
                            score = self.reliability_scorer.score_source(result.sources[0])
                            reliability_scores[source_name] = score.total_score
                
                # 矛盾を解決
                contradiction_report = self.contradiction_resolver.resolve_contradictions(
                    contradictions, reliability_scores
                )
                evaluation.contradiction_report = contradiction_report
                
                # 矛盾レポートのサマリーを出力
                print(f"    解決済み: {len(contradiction_report.resolutions) - contradiction_report.unresolved_count}件")
                print(f"    未解決: {contradiction_report.unresolved_count}件")
                print(f"    総合確信度: {contradiction_report.overall_confidence:.0%}")
        
        # 不確実性サマリーを出力
        uncertainty_summary = self.uncertainty_quantifier.format_uncertainty_summary(uncertainty_report)
        print(f"  不確実性分析完了:")
        print(f"    確信度: {uncertainty_report.confidence_level:.0%}")
        print(f"    不確実性レベル: {uncertainty_report.uncertainty_level}")
        if uncertainty_report.key_uncertainties:
            print(f"    主要因: {', '.join(uncertainty_report.key_uncertainties[:2])}")
        
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
    
    async def _get_candidate_info(self, state: ResearchState) -> str:
        """候補者基本情報を取得（stateから直接取得）"""
        print("    [候補者情報取得] 開始")
        
        # stateから直接候補者情報を取得
        info_parts = []
        
        if hasattr(state, 'candidate_age') and state.candidate_age is not None:
            info_parts.append(f"年齢: {state.candidate_age}歳")
            print(f"    [候補者情報取得] 年齢: {state.candidate_age}歳")
        
        if hasattr(state, 'candidate_gender') and state.candidate_gender:
            info_parts.append(f"性別: {state.candidate_gender}")
            print(f"    [候補者情報取得] 性別: {state.candidate_gender}")
        
        if hasattr(state, 'candidate_company') and state.candidate_company:
            info_parts.append(f"現在の所属: {state.candidate_company}")
            print(f"    [候補者情報取得] 現在の所属: {state.candidate_company}")
        
        if hasattr(state, 'enrolled_company_count') and state.enrolled_company_count is not None:
            info_parts.append(f"在籍企業数: {state.enrolled_company_count}社")
            print(f"    [候補者情報取得] 在籍企業数: {state.enrolled_company_count}社")
        
        if info_parts:
            return '\n'.join(info_parts)
        else:
            print("    [候補者情報取得] 候補者基本情報が提供されていません")
            return "年齢: 不明（候補者情報が提供されていません）"
    
    def _format_structured_job_data(self, state: ResearchState) -> str:
        """構造化された求人データをフォーマット"""
        if not hasattr(state, 'structured_job_data') or not state.structured_job_data:
            return ""
        
        data = state.structured_job_data
        formatted_parts = []
        
        formatted_parts.append("## 求人詳細データ")
        
        # 基本情報
        if data.get('position'):
            formatted_parts.append(f"職種: {data['position']}")
        if data.get('employment_type'):
            formatted_parts.append(f"雇用形態: {data['employment_type']}")
        if data.get('work_location'):
            formatted_parts.append(f"勤務地: {data['work_location']}")
        
        # 給与情報
        if data.get('salary_min') or data.get('salary_max'):
            salary_min = data.get('salary_min', '未設定')
            salary_max = data.get('salary_max', '未設定')
            formatted_parts.append(f"給与レンジ: {salary_min:,}円 〜 {salary_max:,}円" if isinstance(salary_min, (int, float)) else f"給与レンジ: {salary_min} 〜 {salary_max}")
        
        # 必須スキル
        if data.get('required_skills'):
            formatted_parts.append("\n### 必須スキル・経験")
            for skill in data['required_skills']:
                formatted_parts.append(f"- {skill}")
        
        # 歓迎スキル
        if data.get('preferred_skills'):
            formatted_parts.append("\n### 歓迎スキル・経験")
            for skill in data['preferred_skills']:
                formatted_parts.append(f"- {skill}")
        
        # 最小経験年数
        if data.get('experience_years_min'):
            formatted_parts.append(f"\n最小経験年数: {data['experience_years_min']}年以上")
        
        return '\n'.join(formatted_parts) if formatted_parts else ""
    
    def _extract_job_category(self, job_data: Dict, structured_data: Optional[Dict]) -> Optional[str]:
        """求人カテゴリを抽出"""
        # 構造化データから
        if structured_data and structured_data.get('basic_info', {}).get('industry'):
            return structured_data['basic_info']['industry']
        
        # job_descriptionから推測
        text = job_data.get('job_description', '') + ' ' + job_data.get('title', '')
        
        categories = {
            "IT": ["エンジニア", "開発", "プログラマ", "システム", "IT", "ソフトウェア"],
            "営業": ["営業", "セールス", "Sales", "アカウント"],
            "マーケティング": ["マーケティング", "マーケ", "PR", "広報"],
            "人事": ["人事", "HR", "採用", "労務"],
            "経理": ["経理", "財務", "会計", "経理"],
            "製造": ["製造", "生産", "品質管理", "工場"]
        }
        
        for category, keywords in categories.items():
            if any(kw in text for kw in keywords):
                return category
        
        return None
    
    def _extract_required_skills(self, state: ResearchState) -> List[str]:
        """求人から必須スキルを抽出"""
        skills = []
        
        # 構造化データから
        if hasattr(state, 'structured_job_data') and state.structured_job_data:
            if state.structured_job_data.get('required_skills'):
                skills.extend(state.structured_job_data['required_skills'])
        
        # 求人記述から抽出
        text = ""
        if state.job_description:
            text += state.job_description
        text += " " + state.job_memo
        
        # 技術スキル
        tech_skills = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Ruby', 'PHP', 'C++', 'C#', 'Swift',
            'React', 'Vue', 'Angular', 'Django', 'Flask', 'Spring', 'Rails', 'Laravel',
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes'
        ]
        
        for skill in tech_skills:
            if skill.lower() in text.lower():
                skills.append(skill)
        
        # ビジネススキル
        business_skills = ['マネジメント', 'リーダーシップ', 'プロジェクト管理', '営業', 'マーケティング', '企画']
        
        for skill in business_skills:
            if skill in text:
                skills.append(skill)
        
        return list(set(skills))