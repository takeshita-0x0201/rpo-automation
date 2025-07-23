"""
スコアベースの検索戦略
評価スコアに応じて適切な情報収集戦略を決定
"""

from typing import Dict, List, Optional, Tuple
from .base import InformationGap, ResearchState


class ScoreBasedSearchStrategy:
    """スコアに基づいて検索戦略を決定"""
    
    def __init__(self):
        # スコアレンジごとの戦略定義
        self.strategies = {
            "critical_low": {  # 0-30
                "range": (0, 30),
                "should_search": False,  # 明らかに不適合
                "reason": "スコアが極めて低いため、追加情報収集は不要"
            },
            "low": {  # 31-45
                "range": (31, 45),
                "should_search": True,
                "focus_areas": ["必須要件の確認", "重大な懸念事項の詳細"],
                "max_iterations": 1
            },
            "medium_low": {  # 46-60
                "range": (46, 60),
                "should_search": True,
                "focus_areas": ["環境適応性", "実務遂行能力", "必須要件のギャップ"],
                "max_iterations": 2
            },
            "medium": {  # 61-75
                "range": (61, 75),
                "should_search": True,
                "focus_areas": ["環境適応性", "役割期待値", "市場競争力"],
                "max_iterations": 2
            },
            "medium_high": {  # 76-85
                "range": (76, 85),
                "should_search": lambda confidence: confidence != "高",
                "focus_areas": ["細かな懸念事項", "成長ポテンシャル"],
                "max_iterations": 1
            },
            "high": {  # 86-95
                "range": (86, 95),
                "should_search": False,
                "reason": "十分に高いスコアのため、追加情報は不要"
            },
            "excellent": {  # 96-100
                "range": (96, 100),
                "should_search": False,
                "reason": "優秀な候補者として確定"
            }
        }
    
    def get_strategy(self, score: int, confidence: str) -> Dict:
        """スコアと確信度から適切な戦略を取得"""
        for strategy_name, strategy in self.strategies.items():
            min_score, max_score = strategy["range"]
            if min_score <= score <= max_score:
                # should_searchが関数の場合は実行
                if callable(strategy.get("should_search")):
                    should_search = strategy["should_search"](confidence)
                else:
                    should_search = strategy.get("should_search", False)
                
                return {
                    "name": strategy_name,
                    "should_search": should_search,
                    "focus_areas": strategy.get("focus_areas", []),
                    "max_iterations": strategy.get("max_iterations", 1),
                    "reason": strategy.get("reason", "")
                }
        
        # デフォルト戦略
        return {
            "name": "default",
            "should_search": True,
            "focus_areas": ["環境適応性", "実務遂行能力"],
            "max_iterations": 1,
            "reason": "スコアレンジ外のためデフォルト戦略を適用"
        }
    
    def generate_targeted_gaps(
        self, 
        score: int, 
        focus_areas: List[str],
        job_description: str,
        resume: str
    ) -> List[InformationGap]:
        """フォーカスエリアに基づいてターゲット化されたギャップを生成"""
        gaps = []
        
        gap_templates = {
            "環境適応性": InformationGap(
                info_type="環境適応性ギャップ",
                description="候補者の現在の企業と求人企業の規模・文化・働き方の違い",
                search_query=self._extract_company_query(job_description, resume),
                importance="高",
                rationale="組織規模や文化の違いは採用後の定着率に大きく影響"
            ),
            "実務遂行能力": InformationGap(
                info_type="実務遂行能力ギャップ",
                description="必須スキルの実践的な深さと実際のプロジェクト規模での適用経験",
                search_query=self._extract_skill_query(job_description, resume),
                importance="高",
                rationale="レジュメに記載されたスキルの実践的な深さを確認"
            ),
            "役割期待値": InformationGap(
                info_type="役割期待値ギャップ",
                description="現職と求人職の責任範囲・権限レベル・チーム規模の差異",
                search_query=self._extract_role_query(job_description, resume),
                importance="中",
                rationale="役割の変化への適応可能性を評価"
            ),
            "市場競争力": InformationGap(
                info_type="市場競争力ギャップ",
                description="候補者の相対的な市場価値と採用可能性",
                search_query=self._extract_market_query(job_description, resume),
                importance="中",
                rationale="他社との競合状況や採用成功可能性を評価"
            ),
            "必須要件の確認": InformationGap(
                info_type="必須要件充足度",
                description="求人の必須要件に対する候補者の具体的な経験と実績",
                search_query=self._extract_requirement_query(job_description, resume),
                importance="高",
                rationale="必須要件の充足度を詳細に確認"
            ),
            "成長ポテンシャル": InformationGap(
                info_type="成長ポテンシャル評価",
                description="候補者の学習能力と新しい環境への適応実績",
                search_query="キャリア成長 学習能力 新技術習得 環境適応 成功事例",
                importance="中",
                rationale="将来的な成長可能性を評価"
            )
        }
        
        for area in focus_areas:
            if area in gap_templates:
                gaps.append(gap_templates[area])
        
        return gaps[:3]  # 最大3つまで
    
    def _extract_company_query(self, job_desc: str, resume: str) -> str:
        """企業関連の検索クエリを生成"""
        # 簡易的な実装（実際はより高度な抽出ロジックを実装）
        return "企業規模 従業員数 組織文化 働き方 リモートワーク"
    
    def _extract_skill_query(self, job_desc: str, resume: str) -> str:
        """スキル関連の検索クエリを生成"""
        return "実務経験 プロジェクト規模 技術スタック 開発手法"
    
    def _extract_role_query(self, job_desc: str, resume: str) -> str:
        """役割関連の検索クエリを生成"""
        return "マネジメント経験 チーム規模 責任範囲 意思決定権限"
    
    def _extract_market_query(self, job_desc: str, resume: str) -> str:
        """市場関連の検索クエリを生成"""
        return "転職市場 年収相場 人材需要 採用競争率 2024"
    
    def _extract_requirement_query(self, job_desc: str, resume: str) -> str:
        """必須要件関連の検索クエリを生成"""
        return "必須スキル 実務経験 資格要件 業界経験"