"""
矛盾解決アルゴリズム
複数の情報源から得られた矛盾する情報を検出し、解決するメカニズム
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import re
from collections import defaultdict


@dataclass
class Contradiction:
    """矛盾情報の構造"""
    topic: str  # 矛盾が発生しているトピック
    source1: Dict[str, Any]  # 情報源1
    source2: Dict[str, Any]  # 情報源2
    contradiction_type: str  # 矛盾の種類
    severity: str  # 重要度（高/中/低）
    resolution_strategy: Optional[str] = None  # 解決戦略
    resolved_value: Optional[Any] = None  # 解決後の値
    confidence: float = 0.0  # 解決の確信度


@dataclass
class ContradictionResolutionReport:
    """矛盾解決レポート"""
    contradictions_found: List[Contradiction]
    resolutions: List[Dict[str, Any]]
    unresolved_count: int
    overall_confidence: float
    recommendations: List[str]


class ContradictionResolver:
    """矛盾解決器"""
    
    def __init__(self):
        # 矛盾の種類定義
        self.contradiction_types = {
            "numerical": "数値の不一致",
            "temporal": "時系列の矛盾",
            "categorical": "カテゴリの不一致",
            "boolean": "真偽値の矛盾",
            "semantic": "意味的な矛盾",
            "scale": "規模の不一致"
        }
        
        # 解決戦略
        self.resolution_strategies = {
            "most_recent": "最新の情報を採用",
            "most_reliable": "最も信頼性の高い情報源を採用",
            "consensus": "多数決による解決",
            "range": "範囲として表現",
            "weighted_average": "重み付き平均",
            "expert_judgment": "専門的判断が必要",
            "manual_verification": "手動確認が必要"
        }
        
        # トピック別の重要度設定
        self.topic_importance = {
            "experience_years": "高",
            "skills": "高",
            "salary": "中",
            "company_size": "中",
            "location": "中",
            "education": "低",
            "hobbies": "低"
        }
    
    def detect_contradictions(self, 
                            resume_data: Dict,
                            search_results: Dict[str, Any],
                            evaluation_text: str) -> List[Contradiction]:
        """矛盾を検出"""
        contradictions = []
        
        # 1. レジュメと検索結果の矛盾を検出
        if search_results:
            contradictions.extend(
                self._detect_resume_search_contradictions(resume_data, search_results)
            )
        
        # 2. 検索結果間の矛盾を検出
        if len(search_results) > 1:
            contradictions.extend(
                self._detect_search_results_contradictions(search_results)
            )
        
        # 3. 評価内の矛盾を検出
        contradictions.extend(
            self._detect_evaluation_contradictions(evaluation_text)
        )
        
        # 4. 時系列の矛盾を検出
        contradictions.extend(
            self._detect_temporal_contradictions(resume_data, search_results)
        )
        
        return contradictions
    
    def resolve_contradictions(self,
                             contradictions: List[Contradiction],
                             reliability_scores: Optional[Dict[str, float]] = None) -> ContradictionResolutionReport:
        """矛盾を解決"""
        resolutions = []
        unresolved_count = 0
        
        for contradiction in contradictions:
            resolution = self._resolve_single_contradiction(
                contradiction, reliability_scores
            )
            
            if resolution['resolved']:
                resolutions.append(resolution)
                contradiction.resolved_value = resolution['value']
                contradiction.confidence = resolution['confidence']
            else:
                unresolved_count += 1
        
        # 全体的な確信度を計算
        overall_confidence = self._calculate_overall_confidence(resolutions)
        
        # 推奨事項を生成
        recommendations = self._generate_recommendations(
            contradictions, resolutions, unresolved_count
        )
        
        return ContradictionResolutionReport(
            contradictions_found=contradictions,
            resolutions=resolutions,
            unresolved_count=unresolved_count,
            overall_confidence=overall_confidence,
            recommendations=recommendations
        )
    
    def _detect_resume_search_contradictions(self,
                                           resume_data: Dict,
                                           search_results: Dict) -> List[Contradiction]:
        """レジュメと検索結果の矛盾を検出"""
        contradictions = []
        
        # 経験年数の矛盾をチェック
        resume_years = self._extract_experience_years(resume_data.get('text', ''))
        
        for source_name, result in search_results.items():
            search_years = self._extract_experience_years(result.summary)
            
            if resume_years and search_years:
                if abs(resume_years - search_years) > 2:  # 2年以上の差がある場合
                    contradictions.append(Contradiction(
                        topic="experience_years",
                        source1={"name": "resume", "value": resume_years, "text": f"{resume_years}年の経験"},
                        source2={"name": source_name, "value": search_years, "text": f"{search_years}年の経験"},
                        contradiction_type="numerical",
                        severity="高"
                    ))
        
        # スキルセットの矛盾をチェック
        resume_skills = self._extract_skills(resume_data.get('text', ''))
        for source_name, result in search_results.items():
            search_skills = self._extract_skills(result.summary)
            
            # 相反するスキル情報をチェック
            contradictory_skills = self._find_contradictory_skills(
                resume_skills, search_skills
            )
            
            for skill_contradiction in contradictory_skills:
                contradictions.append(Contradiction(
                    topic="skills",
                    source1={"name": "resume", "value": skill_contradiction[0]},
                    source2={"name": source_name, "value": skill_contradiction[1]},
                    contradiction_type="semantic",
                    severity="中"
                ))
        
        return contradictions
    
    def _detect_search_results_contradictions(self,
                                            search_results: Dict) -> List[Contradiction]:
        """検索結果間の矛盾を検出"""
        contradictions = []
        sources = list(search_results.items())
        
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                source1_name, result1 = sources[i]
                source2_name, result2 = sources[j]
                
                # 企業規模の矛盾
                size1 = self._extract_company_size(result1.summary)
                size2 = self._extract_company_size(result2.summary)
                
                if size1 and size2 and self._is_size_contradictory(size1, size2):
                    contradictions.append(Contradiction(
                        topic="company_size",
                        source1={"name": source1_name, "value": size1},
                        source2={"name": source2_name, "value": size2},
                        contradiction_type="scale",
                        severity="中"
                    ))
                
                # 役職の矛盾
                role1 = self._extract_role(result1.summary)
                role2 = self._extract_role(result2.summary)
                
                if role1 and role2 and role1 != role2:
                    contradictions.append(Contradiction(
                        topic="job_role",
                        source1={"name": source1_name, "value": role1},
                        source2={"name": source2_name, "value": role2},
                        contradiction_type="categorical",
                        severity="高"
                    ))
        
        return contradictions
    
    def _detect_evaluation_contradictions(self, evaluation_text: str) -> List[Contradiction]:
        """評価内の矛盾を検出"""
        contradictions = []
        
        # 評価スコアと評価文の矛盾
        score_match = re.search(r'適合度スコア[：:]\s*(\d+)', evaluation_text)
        if score_match:
            score = int(score_match.group(1))
            
            # 高スコアなのに否定的な表現が多い場合
            negative_count = len(re.findall(
                r'(不足|欠如|ない|難しい|懸念|リスク|低い|弱い)', 
                evaluation_text
            ))
            positive_count = len(re.findall(
                r'(優秀|豊富|高い|強い|適合|マッチ|期待できる)', 
                evaluation_text
            ))
            
            if score >= 70 and negative_count > positive_count * 2:
                contradictions.append(Contradiction(
                    topic="evaluation_consistency",
                    source1={"name": "score", "value": score},
                    source2={"name": "text_sentiment", "value": "negative"},
                    contradiction_type="semantic",
                    severity="高"
                ))
            elif score <= 30 and positive_count > negative_count * 2:
                contradictions.append(Contradiction(
                    topic="evaluation_consistency",
                    source1={"name": "score", "value": score},
                    source2={"name": "text_sentiment", "value": "positive"},
                    contradiction_type="semantic",
                    severity="高"
                ))
        
        # 確信度と不確実性表現の矛盾
        confidence_match = re.search(r'確信度[：:]\s*([高中低])', evaluation_text)
        if confidence_match:
            confidence = confidence_match.group(1)
            uncertainty_expressions = len(re.findall(
                r'(可能性|思われる|かもしれない|推測|不明|曖昧)',
                evaluation_text
            ))
            
            if confidence == "高" and uncertainty_expressions > 3:
                contradictions.append(Contradiction(
                    topic="confidence_consistency",
                    source1={"name": "stated_confidence", "value": confidence},
                    source2={"name": "uncertainty_expressions", "value": uncertainty_expressions},
                    contradiction_type="semantic",
                    severity="中"
                ))
        
        return contradictions
    
    def _detect_temporal_contradictions(self,
                                      resume_data: Dict,
                                      search_results: Dict) -> List[Contradiction]:
        """時系列の矛盾を検出"""
        contradictions = []
        
        # 職歴の時系列をチェック
        timeline = self._extract_career_timeline(resume_data.get('text', ''))
        
        for i in range(len(timeline) - 1):
            current = timeline[i]
            next_item = timeline[i + 1]
            
            # 時期の重複をチェック
            if current['end_date'] and next_item['start_date']:
                if current['end_date'] > next_item['start_date']:
                    contradictions.append(Contradiction(
                        topic="career_timeline",
                        source1={"name": "position1", "value": current},
                        source2={"name": "position2", "value": next_item},
                        contradiction_type="temporal",
                        severity="高"
                    ))
        
        return contradictions
    
    def _resolve_single_contradiction(self,
                                    contradiction: Contradiction,
                                    reliability_scores: Optional[Dict[str, float]]) -> Dict:
        """単一の矛盾を解決"""
        resolution = {
            'topic': contradiction.topic,
            'resolved': False,
            'value': None,
            'confidence': 0.0,
            'strategy': None,
            'explanation': ''
        }
        
        # 矛盾の種類に応じた解決戦略を選択
        if contradiction.contradiction_type == "numerical":
            resolution = self._resolve_numerical_contradiction(
                contradiction, reliability_scores
            )
        elif contradiction.contradiction_type == "temporal":
            resolution = self._resolve_temporal_contradiction(
                contradiction
            )
        elif contradiction.contradiction_type == "categorical":
            resolution = self._resolve_categorical_contradiction(
                contradiction, reliability_scores
            )
        elif contradiction.contradiction_type == "semantic":
            resolution = self._resolve_semantic_contradiction(
                contradiction, reliability_scores
            )
        elif contradiction.contradiction_type == "scale":
            resolution = self._resolve_scale_contradiction(
                contradiction
            )
        
        # 解決戦略を記録
        contradiction.resolution_strategy = resolution.get('strategy')
        
        return resolution
    
    def _resolve_numerical_contradiction(self,
                                       contradiction: Contradiction,
                                       reliability_scores: Optional[Dict[str, float]]) -> Dict:
        """数値の矛盾を解決"""
        value1 = contradiction.source1['value']
        value2 = contradiction.source2['value']
        
        # 信頼性スコアがある場合は重み付き平均
        if reliability_scores:
            score1 = reliability_scores.get(contradiction.source1['name'], 0.5)
            score2 = reliability_scores.get(contradiction.source2['name'], 0.5)
            
            if score1 + score2 > 0:
                weighted_value = (value1 * score1 + value2 * score2) / (score1 + score2)
                confidence = max(score1, score2)
                
                return {
                    'topic': contradiction.topic,
                    'resolved': True,
                    'value': weighted_value,
                    'confidence': confidence,
                    'strategy': 'weighted_average',
                    'explanation': f'信頼性スコアに基づく重み付き平均（{score1:.2f}:{score2:.2f}）'
                }
        
        # 範囲として表現
        min_val = min(value1, value2)
        max_val = max(value1, value2)
        
        return {
            'topic': contradiction.topic,
            'resolved': True,
            'value': f"{min_val}-{max_val}",
            'confidence': 0.6,
            'strategy': 'range',
            'explanation': f'範囲として表現（{min_val}から{max_val}）'
        }
    
    def _resolve_temporal_contradiction(self, contradiction: Contradiction) -> Dict:
        """時系列の矛盾を解決"""
        # 最新の情報を優先
        date1 = contradiction.source1['value'].get('end_date')
        date2 = contradiction.source2['value'].get('start_date')
        
        return {
            'topic': contradiction.topic,
            'resolved': False,
            'value': None,
            'confidence': 0.3,
            'strategy': 'manual_verification',
            'explanation': '職歴の時系列に重複があり、手動確認が必要'
        }
    
    def _resolve_categorical_contradiction(self,
                                         contradiction: Contradiction,
                                         reliability_scores: Optional[Dict[str, float]]) -> Dict:
        """カテゴリの矛盾を解決"""
        # 信頼性の高い情報源を選択
        if reliability_scores:
            score1 = reliability_scores.get(contradiction.source1['name'], 0.5)
            score2 = reliability_scores.get(contradiction.source2['name'], 0.5)
            
            if score1 > score2:
                return {
                    'topic': contradiction.topic,
                    'resolved': True,
                    'value': contradiction.source1['value'],
                    'confidence': score1,
                    'strategy': 'most_reliable',
                    'explanation': f'{contradiction.source1["name"]}の情報を採用（信頼性: {score1:.2f}）'
                }
            else:
                return {
                    'topic': contradiction.topic,
                    'resolved': True,
                    'value': contradiction.source2['value'],
                    'confidence': score2,
                    'strategy': 'most_reliable',
                    'explanation': f'{contradiction.source2["name"]}の情報を採用（信頼性: {score2:.2f}）'
                }
        
        # レジュメの情報を優先
        if contradiction.source1['name'] == 'resume':
            return {
                'topic': contradiction.topic,
                'resolved': True,
                'value': contradiction.source1['value'],
                'confidence': 0.7,
                'strategy': 'primary_source',
                'explanation': 'レジュメの情報を優先的に採用'
            }
        
        return {
            'topic': contradiction.topic,
            'resolved': False,
            'value': None,
            'confidence': 0.4,
            'strategy': 'expert_judgment',
            'explanation': '専門的な判断が必要'
        }
    
    def _resolve_semantic_contradiction(self,
                                      contradiction: Contradiction,
                                      reliability_scores: Optional[Dict[str, float]]) -> Dict:
        """意味的な矛盾を解決"""
        # 評価の一貫性に関する矛盾の場合
        if contradiction.topic == "evaluation_consistency":
            return {
                'topic': contradiction.topic,
                'resolved': True,
                'value': "要詳細確認",
                'confidence': 0.5,
                'strategy': 'manual_verification',
                'explanation': 'スコアと評価文の整合性を手動で確認する必要あり'
            }
        
        # その他の意味的矛盾
        return {
            'topic': contradiction.topic,
            'resolved': False,
            'value': None,
            'confidence': 0.4,
            'strategy': 'expert_judgment',
            'explanation': '意味的な矛盾のため専門的判断が必要'
        }
    
    def _resolve_scale_contradiction(self, contradiction: Contradiction) -> Dict:
        """規模の矛盾を解決"""
        # 範囲として表現
        return {
            'topic': contradiction.topic,
            'resolved': True,
            'value': f"{contradiction.source1['value']}〜{contradiction.source2['value']}",
            'confidence': 0.6,
            'strategy': 'range',
            'explanation': '情報源により異なるため範囲として表現'
        }
    
    def _calculate_overall_confidence(self, resolutions: List[Dict]) -> float:
        """全体的な確信度を計算"""
        if not resolutions:
            return 1.0  # 矛盾がない場合は高確信度
        
        resolved_confidences = [
            r['confidence'] for r in resolutions if r['resolved']
        ]
        
        if resolved_confidences:
            return sum(resolved_confidences) / len(resolved_confidences)
        
        return 0.3  # 解決できない矛盾が多い場合は低確信度
    
    def _generate_recommendations(self,
                                contradictions: List[Contradiction],
                                resolutions: List[Dict],
                                unresolved_count: int) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        # 未解決の矛盾がある場合
        if unresolved_count > 0:
            recommendations.append(
                f"未解決の矛盾が{unresolved_count}件あります。面接での確認を推奨します。"
            )
        
        # 高重要度の矛盾
        high_severity = [c for c in contradictions if c.severity == "高"]
        if high_severity:
            topics = list(set([c.topic for c in high_severity]))
            recommendations.append(
                f"重要な矛盾が検出されました: {', '.join(topics)}。特に注意が必要です。"
            )
        
        # 時系列の矛盾
        temporal = [c for c in contradictions if c.contradiction_type == "temporal"]
        if temporal:
            recommendations.append(
                "職歴の時系列に矛盾があります。経歴書の再確認を推奨します。"
            )
        
        # 数値の大きな乖離
        numerical = [c for c in contradictions if c.contradiction_type == "numerical"]
        if numerical:
            recommendations.append(
                "経験年数等の数値情報に乖離があります。正確な情報の確認が必要です。"
            )
        
        # 解決戦略別の推奨
        manual_verification_needed = [
            r for r in resolutions 
            if r.get('strategy') == 'manual_verification'
        ]
        if manual_verification_needed:
            recommendations.append(
                f"{len(manual_verification_needed)}件の項目で手動確認が必要です。"
            )
        
        return recommendations
    
    # ヘルパーメソッド
    def _extract_experience_years(self, text: str) -> Optional[int]:
        """テキストから経験年数を抽出"""
        patterns = [
            r'(\d+)年以上の経験',
            r'経験(\d+)年',
            r'(\d+)年間',
            r'(\d+)years?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """テキストからスキルを抽出"""
        # 簡易的なスキル抽出（実際はより高度な処理が必要）
        skills = []
        
        # プログラミング言語
        languages = re.findall(
            r'\b(Python|Java|JavaScript|TypeScript|Go|Ruby|PHP|C\+\+|C#|Swift)\b',
            text, re.IGNORECASE
        )
        skills.extend(languages)
        
        # フレームワーク
        frameworks = re.findall(
            r'\b(React|Vue|Angular|Django|Flask|Spring|Rails|Laravel)\b',
            text, re.IGNORECASE
        )
        skills.extend(frameworks)
        
        return list(set(skills))
    
    def _find_contradictory_skills(self,
                                  skills1: List[str],
                                  skills2: List[str]) -> List[Tuple[str, str]]:
        """矛盾するスキル情報を検出"""
        contradictions = []
        
        # 競合する技術スタック
        competing_stacks = [
            ('React', 'Vue'),
            ('Angular', 'React'),
            ('Django', 'Rails'),
            ('MySQL', 'PostgreSQL')
        ]
        
        for tech1, tech2 in competing_stacks:
            if tech1 in skills1 and tech2 in skills2:
                contradictions.append((tech1, tech2))
            elif tech2 in skills1 and tech1 in skills2:
                contradictions.append((tech2, tech1))
        
        return contradictions
    
    def _extract_company_size(self, text: str) -> Optional[str]:
        """企業規模を抽出"""
        size_patterns = {
            r'大企業|大手': '大企業',
            r'中堅企業|中規模': '中堅企業',
            r'ベンチャー|スタートアップ': 'ベンチャー',
            r'中小企業|小規模': '中小企業'
        }
        
        for pattern, size in size_patterns.items():
            if re.search(pattern, text):
                return size
        
        # 従業員数から推定
        emp_match = re.search(r'(\d+)人?(?:名|人)(?:以上|規模)', text)
        if emp_match:
            employees = int(emp_match.group(1))
            if employees >= 1000:
                return '大企業'
            elif employees >= 300:
                return '中堅企業'
            elif employees >= 50:
                return '中小企業'
            else:
                return 'ベンチャー'
        
        return None
    
    def _is_size_contradictory(self, size1: str, size2: str) -> bool:
        """企業規模が矛盾しているか判定"""
        # 明確に異なるカテゴリの場合のみ矛盾とする
        contradictory_pairs = [
            ('大企業', 'ベンチャー'),
            ('大企業', '中小企業'),
            ('中堅企業', 'ベンチャー')
        ]
        
        return (size1, size2) in contradictory_pairs or (size2, size1) in contradictory_pairs
    
    def _extract_role(self, text: str) -> Optional[str]:
        """役職を抽出"""
        roles = {
            r'CEO|代表取締役|社長': 'CEO',
            r'CTO|技術責任者': 'CTO',
            r'部長|ディレクター': '部長',
            r'課長|マネージャー': '課長',
            r'リーダー|主任': 'リーダー',
            r'エンジニア|開発者': 'エンジニア',
            r'アナリスト|分析': 'アナリスト'
        }
        
        for pattern, role in roles.items():
            if re.search(pattern, text):
                return role
        
        return None
    
    def _extract_career_timeline(self, text: str) -> List[Dict]:
        """職歴のタイムラインを抽出"""
        timeline = []
        
        # 年月のパターン
        date_pattern = r'(\d{4})年?(\d{1,2})?月?'
        
        # 職歴セクションを探す
        career_sections = re.split(r'\n(?=\d{4}年)', text)
        
        for section in career_sections:
            dates = re.findall(date_pattern, section)
            if len(dates) >= 1:
                start_date = self._parse_date(dates[0])
                end_date = self._parse_date(dates[1]) if len(dates) >= 2 else None
                
                timeline.append({
                    'start_date': start_date,
                    'end_date': end_date,
                    'text': section[:100]  # 最初の100文字
                })
        
        # 時系列順にソート
        timeline.sort(key=lambda x: x['start_date'] if x['start_date'] else datetime.min)
        
        return timeline
    
    def _parse_date(self, date_tuple: Tuple[str, str]) -> Optional[datetime]:
        """日付タプルをdatetimeオブジェクトに変換"""
        try:
            year = int(date_tuple[0])
            month = int(date_tuple[1]) if date_tuple[1] else 1
            return datetime(year, month, 1)
        except:
            return None
    
    def format_contradiction_report(self, report: ContradictionResolutionReport) -> str:
        """矛盾解決レポートをフォーマット"""
        output = []
        output.append("# 矛盾検出・解決レポート")
        output.append(f"\n総合確信度: {report.overall_confidence:.0%}")
        
        if report.contradictions_found:
            output.append(f"\n## 検出された矛盾 ({len(report.contradictions_found)}件)")
            
            # 重要度別に整理
            by_severity = defaultdict(list)
            for c in report.contradictions_found:
                by_severity[c.severity].append(c)
            
            for severity in ["高", "中", "低"]:
                if severity in by_severity:
                    output.append(f"\n### {severity}重要度 ({len(by_severity[severity])}件)")
                    for c in by_severity[severity]:
                        output.append(f"\n**{c.topic}** ({c.contradiction_type})")
                        output.append(f"- 情報源1 ({c.source1['name']}): {c.source1.get('value', c.source1.get('text', ''))}")
                        output.append(f"- 情報源2 ({c.source2['name']}): {c.source2.get('value', c.source2.get('text', ''))}")
                        if c.resolved_value is not None:
                            output.append(f"- 解決値: {c.resolved_value}")
                            output.append(f"- 解決戦略: {c.resolution_strategy}")
                            output.append(f"- 確信度: {c.confidence:.0%}")
        
        if report.resolutions:
            output.append(f"\n## 解決結果")
            resolved = [r for r in report.resolutions if r['resolved']]
            output.append(f"- 解決済み: {len(resolved)}件")
            output.append(f"- 未解決: {report.unresolved_count}件")
            
            if resolved:
                output.append("\n### 解決済み項目")
                for r in resolved:
                    output.append(f"- {r['topic']}: {r['value']} (戦略: {r['strategy']}, 確信度: {r['confidence']:.0%})")
        
        if report.recommendations:
            output.append("\n## 推奨事項")
            for rec in report.recommendations:
                output.append(f"- {rec}")
        
        return '\n'.join(output)