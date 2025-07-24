"""
セマンティックガードレール
重要な区別を維持しながら柔軟な評価を可能にする
"""

from typing import Dict, List, Tuple, Optional
import re


class SemanticGuards:
    """評価の際の最小限のガードレールを提供"""
    
    # 営業関連の用語マッピング
    SALES_TERMS = {
        "direct": ["法人営業", "B2B営業", "企業向け営業", "アカウント営業", "直接営業", "外勤営業"],
        "indirect": ["担当", "主担当", "クライアント", "顧客対応", "提案", "受注", "商談"],
        "activities": ["新規開拓", "既存顧客", "フォロー", "アフターフォロー", "ルート営業"],
        "results": ["売上", "受注", "成約", "契約", "販売実績", "営業成績"]
    }
    
    # 職種の本質的な違いを定義
    ROLE_BOUNDARIES = {
        "営業": {
            "must_have_any": ["売上責任", "顧客開拓", "商談", "提案活動"],
            "cannot_be": ["純粋な事務作業", "開発のみ", "内部管理のみ"]
        },
        "エンジニア": {
            "must_have_any": ["プログラミング", "システム開発", "技術的実装"],
            "cannot_be": ["営業のみ", "事務のみ", "企画のみ"]
        },
        "経理": {
            "must_have_any": ["仕訳", "決算", "会計処理", "財務諸表"],
            "cannot_be": ["営業のみ", "開発のみ", "純粋な事務"]
        }
    }
    
    # 経験年数の解釈ルール
    EXPERIENCE_INTERPRETATION = {
        "direct_match": 1.0,  # 完全一致
        "same_domain": 0.8,   # 同一領域
        "related_domain": 0.6,  # 関連領域
        "transferable_skills": 0.4,  # 転用可能スキル
        "unrelated": 0.2  # 無関係
    }
    
    @classmethod
    def detect_sales_experience(cls, resume_text: str) -> Tuple[bool, float, List[str]]:
        """
        営業経験を検出し、確信度と根拠を返す
        
        Returns:
            (has_experience, confidence, evidence_list)
        """
        evidence = []
        confidence = 0.0
        
        # 直接的な営業用語をチェック
        for term in cls.SALES_TERMS["direct"]:
            if term in resume_text:
                evidence.append(f"直接的な営業用語: {term}")
                confidence = max(confidence, 0.9)
        
        # 間接的な指標をチェック
        indirect_count = 0
        for category in ["indirect", "activities", "results"]:
            for term in cls.SALES_TERMS[category]:
                if term in resume_text:
                    evidence.append(f"{category}: {term}")
                    indirect_count += 1
        
        # 間接的な指標が複数ある場合
        if indirect_count >= 3:
            confidence = max(confidence, 0.7)
        elif indirect_count >= 2:
            confidence = max(confidence, 0.5)
        elif indirect_count >= 1:
            confidence = max(confidence, 0.3)
        
        # コンテキストチェック（例：会計事務所での「担当」は営業要素が低い）
        if "会計事務所" in resume_text or "税理士" in resume_text:
            if confidence < 0.9:  # 直接的な営業用語がない場合
                confidence *= 0.5
                evidence.append("コンテキスト: 会計事務所での業務")
        
        has_experience = confidence >= 0.3
        return has_experience, confidence, evidence
    
    @classmethod
    def evaluate_role_match(cls, required_role: str, candidate_experience: str) -> Dict[str, any]:
        """
        要求される役職と候補者の経験のマッチ度を評価
        """
        result = {
            "match_type": "unrelated",
            "score_multiplier": 0.2,
            "reasoning": []
        }
        
        # 正規化
        required_role = required_role.lower()
        candidate_exp = candidate_experience.lower()
        
        # 完全一致
        if required_role in candidate_exp:
            result["match_type"] = "direct_match"
            result["score_multiplier"] = 1.0
            result["reasoning"].append(f"直接的な経験: {required_role}")
            return result
        
        # ドメイン知識に基づく評価
        role_mappings = {
            "営業": {
                "same": ["セールス", "販売", "ビジネス開発", "bd"],
                "related": ["マーケティング", "企画営業", "コンサルタント"],
                "transferable": ["接客", "カスタマーサクセス", "アカウント管理"]
            },
            "エンジニア": {
                "same": ["開発者", "プログラマー", "デベロッパー", "開発"],
                "related": ["インフラ", "システム管理", "テクニカルサポート"],
                "transferable": ["データ分析", "業務改善", "it管理"]
            },
            "経理": {
                "same": ["会計", "財務", "経理財務", "管理会計"],
                "related": ["財務会計", "税務", "監査"],
                "transferable": ["経営企画", "管理部門", "バックオフィス"]
            }
        }
        
        # マッピングチェック
        if required_role in role_mappings:
            mappings = role_mappings[required_role]
            
            for same_role in mappings.get("same", []):
                if same_role in candidate_exp:
                    result["match_type"] = "same_domain"
                    result["score_multiplier"] = 0.8
                    result["reasoning"].append(f"同一領域: {same_role}")
                    return result
            
            for related_role in mappings.get("related", []):
                if related_role in candidate_exp:
                    result["match_type"] = "related_domain"
                    result["score_multiplier"] = 0.6
                    result["reasoning"].append(f"関連領域: {related_role}")
                    return result
            
            for transferable in mappings.get("transferable", []):
                if transferable in candidate_exp:
                    result["match_type"] = "transferable_skills"
                    result["score_multiplier"] = 0.4
                    result["reasoning"].append(f"転用可能: {transferable}")
                    return result
        
        return result
    
    @classmethod
    def check_critical_distinctions(cls, job_requirements: Dict, candidate_profile: Dict) -> List[Dict]:
        """
        クリティカルな区別をチェックし、警告を生成
        """
        warnings = []
        
        # 管理職と実務担当者の区別
        if "役員" in job_requirements.get("position", "") or "cxo" in job_requirements.get("position", "").lower():
            if "スタッフ" in candidate_profile.get("current_position", "") or \
               "担当" in candidate_profile.get("current_position", ""):
                warnings.append({
                    "type": "level_mismatch",
                    "severity": "high",
                    "message": "役員級ポジションに対して実務レベルの候補者",
                    "score_impact": -30
                })
        
        # 業界特有の資格要件
        if "必須資格" in job_requirements:
            for cert in job_requirements["必須資格"]:
                if cert not in candidate_profile.get("certifications", []):
                    warnings.append({
                        "type": "missing_certification",
                        "severity": "critical",
                        "message": f"必須資格なし: {cert}",
                        "score_impact": -40
                    })
        
        return warnings
    
    @classmethod
    def suggest_evaluation_approach(cls, job_type: str, uncertainty_level: float) -> str:
        """
        職種と不確実性レベルに基づいて評価アプローチを提案
        """
        if uncertainty_level > 0.7:
            return "semantic_heavy"  # セマンティック理解を重視
        elif uncertainty_level > 0.3:
            return "hybrid"  # ハイブリッドアプローチ
        else:
            return "rule_based"  # ルールベースで十分