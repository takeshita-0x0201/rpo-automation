"""
検索クエリテンプレートモジュール
構造化された検索クエリの生成を支援
"""

from typing import Dict, List, Optional
from datetime import datetime
import re


class QueryTemplates:
    """検索クエリテンプレートの定義と生成"""
    
    # 基本テンプレート
    TEMPLATES = {
        "company_info": {
            "template": "{company_name} {aspect} {year}",
            "aspects": ["企業規模", "従業員数", "売上高", "事業内容", "企業文化", "成長性", "離職率"],
            "example": "株式会社メルカリ 従業員数 2024"
        },
        
        "skill_market": {
            "template": "{skill} {industry} 需要 市場価値 {year}",
            "variations": ["エンジニア", "求人", "年収", "転職", "将来性"],
            "example": "Python フィンテック 需要 市場価値 2024"
        },
        
        "industry_trend": {
            "template": "{industry} 業界動向 {trend_type} {timeframe}",
            "trend_types": ["成長予測", "技術トレンド", "人材需要", "課題", "規制動向"],
            "example": "SaaS 業界動向 成長予測 2024-2025"
        },
        
        "role_requirements": {
            "template": "{role} {company_size} 必要スキル 求められる経験",
            "company_sizes": ["スタートアップ", "中小企業", "大企業", "外資系"],
            "example": "プロダクトマネージャー スタートアップ 必要スキル 求められる経験"
        },
        
        "career_transition": {
            "template": "{from_role} から {to_role} キャリアチェンジ 成功事例",
            "example": "エンジニア から プロダクトマネージャー キャリアチェンジ 成功事例"
        },
        
        "technology_stack": {
            "template": "{technology} {context} 採用事例 導入企業",
            "contexts": ["実装", "運用", "メリット", "デメリット", "代替技術"],
            "example": "Kubernetes マイクロサービス 採用事例 導入企業"
        }
    }
    
    # 業界別の専門用語マッピング
    INDUSTRY_TERMS = {
        "IT": ["DX", "AI", "機械学習", "クラウド", "DevOps", "アジャイル"],
        "金融": ["フィンテック", "ブロックチェーン", "規制対応", "リスク管理", "コンプライアンス"],
        "製造": ["IoT", "スマートファクトリー", "品質管理", "サプライチェーン", "カーボンニュートラル"],
        "医療": ["デジタルヘルス", "遠隔医療", "創薬", "医療機器", "臨床試験"],
        "小売": ["EC", "オムニチャネル", "D2C", "顧客体験", "在庫管理"]
    }
    
    @classmethod
    def generate_company_query(cls, company_name: str, aspect: str, year: Optional[int] = None) -> str:
        """企業情報検索クエリを生成"""
        if not year:
            year = datetime.now().year
        
        # 企業名の正規化（株式会社などを除去）
        normalized_name = re.sub(r'(株式会社|有限会社|合同会社)', '', company_name).strip()
        
        return cls.TEMPLATES["company_info"]["template"].format(
            company_name=normalized_name,
            aspect=aspect,
            year=year
        )
    
    @classmethod
    def generate_skill_query(cls, skill: str, industry: str = "", year: Optional[int] = None) -> str:
        """スキル市場価値検索クエリを生成"""
        if not year:
            year = datetime.now().year
        
        # スキルの同義語展開
        skill_variations = cls._expand_skill_synonyms(skill)
        
        return cls.TEMPLATES["skill_market"]["template"].format(
            skill=skill_variations,
            industry=industry,
            year=year
        )
    
    @classmethod
    def generate_industry_query(cls, industry: str, trend_type: str, timeframe: str = "") -> str:
        """業界動向検索クエリを生成"""
        if not timeframe:
            current_year = datetime.now().year
            timeframe = f"{current_year}-{current_year + 1}"
        
        # 業界固有の用語を追加
        industry_terms = cls.INDUSTRY_TERMS.get(industry, [])
        enhanced_industry = f"{industry} {' '.join(industry_terms[:2])}" if industry_terms else industry
        
        return cls.TEMPLATES["industry_trend"]["template"].format(
            industry=enhanced_industry,
            trend_type=trend_type,
            timeframe=timeframe
        )
    
    @classmethod
    def expand_query_with_synonyms(cls, base_query: str, context: Dict[str, any]) -> List[str]:
        """クエリを同義語で拡張"""
        queries = [base_query]
        
        # 役職の同義語
        role_synonyms = {
            "エンジニア": ["開発者", "プログラマー", "ソフトウェアエンジニア"],
            "PM": ["プロダクトマネージャー", "プロジェクトマネージャー", "プロダクトオーナー"],
            "営業": ["セールス", "アカウントエグゼクティブ", "ビジネスデベロップメント"],
            "マーケティング": ["マーケター", "グロースハッカー", "デジタルマーケティング"]
        }
        
        # 技術の同義語
        tech_synonyms = {
            "AI": ["人工知能", "機械学習", "ディープラーニング"],
            "クラウド": ["AWS", "Azure", "GCP", "クラウドコンピューティング"],
            "データ分析": ["データサイエンス", "ビッグデータ", "アナリティクス"]
        }
        
        # クエリ内の用語を同義語で置換
        for original, synonyms in {**role_synonyms, **tech_synonyms}.items():
            if original in base_query:
                for synonym in synonyms[:2]:  # 最大2つの同義語
                    queries.append(base_query.replace(original, synonym))
        
        return queries[:3]  # 最大3つのクエリ
    
    @classmethod
    def _expand_skill_synonyms(cls, skill: str) -> str:
        """スキルの同義語を展開"""
        skill_map = {
            "Python": "Python プログラミング",
            "JavaScript": "JavaScript JS TypeScript",
            "マネジメント": "マネジメント 管理 リーダーシップ",
            "営業": "営業 セールス ビジネス開発"
        }
        
        return skill_map.get(skill, skill)
    
    @classmethod
    def create_contextual_queries(cls, gap_type: str, context: Dict[str, any]) -> List[str]:
        """情報ギャップのタイプに応じた文脈的クエリを生成"""
        queries = []
        
        if gap_type == "company_culture":
            company = context.get("company_name", "")
            queries.extend([
                f"{company} 企業文化 働き方 社風",
                f"{company} 従業員 評判 口コミ",
                f"{company} ワークライフバランス 福利厚生"
            ])
        
        elif gap_type == "skill_relevance":
            skill = context.get("skill", "")
            industry = context.get("industry", "")
            queries.extend([
                f"{skill} {industry} 重要性 将来性",
                f"{skill} 習得方法 学習期間 難易度",
                f"{skill} 代替技術 トレンド 2024"
            ])
        
        elif gap_type == "career_path":
            current_role = context.get("current_role", "")
            target_role = context.get("target_role", "")
            queries.extend([
                f"{current_role} {target_role} キャリアパス 転職",
                f"{target_role} 必要経験 スキルセット",
                f"{current_role} キャリアアップ 可能性"
            ])
        
        return queries