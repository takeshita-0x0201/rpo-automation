"""
評価システムの共通フォーマッター
各評価ノードで使用される共通のフォーマット関数を集約
"""

from typing import Dict, List, Optional, Any
from ..nodes.base import ResearchState


class EvaluationFormatters:
    """評価用の共通フォーマッター"""
    
    @staticmethod
    def format_structured_job_data(state: ResearchState) -> str:
        """構造化された求人データをフォーマット"""
        if not hasattr(state, 'structured_job_data') or not state.structured_job_data:
            return ""
        
        data = state.structured_job_data
        formatted_parts = []
        
        formatted_parts.append("## 求人詳細データ（構造化データ）【優先的に使用】")
        
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
            formatted_parts.append("\n### 必須スキル・経験【最重要：これを基準に評価】")
            for i, skill in enumerate(data['required_skills'], 1):
                formatted_parts.append(f"{i}. {skill}")
        
        # 歓迎スキル
        if data.get('preferred_skills'):
            formatted_parts.append("\n### 歓迎スキル・経験【加点要素：これを基準に加点評価】")
            for i, skill in enumerate(data['preferred_skills'], 1):
                formatted_parts.append(f"{i}. {skill}")
        
        # 最小経験年数
        if data.get('experience_years_min'):
            formatted_parts.append(f"\n最小経験年数: {data['experience_years_min']}年以上")
        
        return '\n'.join(formatted_parts) if formatted_parts else ""
    
    @staticmethod
    def format_structured_resume_data(state: ResearchState) -> str:
        """構造化されたレジュメデータをフォーマット"""
        if not hasattr(state, 'structured_resume_data') or not state.structured_resume_data:
            return ""
        
        data = state.structured_resume_data
        formatted_parts = []
        
        formatted_parts.append("## 候補者詳細データ（構造化データ）【高精度抽出済み】")
        
        # 基本情報
        basic_info = data.get('basic_info', {})
        if basic_info:
            formatted_parts.append("\n### 基本情報")
            if basic_info.get('name'):
                formatted_parts.append(f"氏名: {basic_info['name']}")
            if basic_info.get('age'):
                formatted_parts.append(f"年齢: {basic_info['age']}歳")
            if basic_info.get('current_company'):
                formatted_parts.append(f"現職: {basic_info['current_company']}")
        
        # マッチング用データ
        matching_data = data.get('matching_data', {})
        if matching_data:
            formatted_parts.append("\n### 経験サマリー")
            formatted_parts.append(f"総経験年数: {matching_data.get('total_experience_years', 0)}年")
            if matching_data.get('current_role'):
                formatted_parts.append(f"現在の役職: {matching_data['current_role']}")
            
            # 抽出されたスキル
            if matching_data.get('skills_flat'):
                formatted_parts.append("\n### 保有スキル（構造化抽出）")
                for i, skill in enumerate(matching_data['skills_flat'][:20], 1):
                    formatted_parts.append(f"{i}. {skill}")
                if len(matching_data['skills_flat']) > 20:
                    formatted_parts.append(f"... 他{len(matching_data['skills_flat']) - 20}件")
            
            # 主要な実績
            if matching_data.get('key_achievements'):
                formatted_parts.append("\n### 主要実績（数値含む）")
                for i, achievement in enumerate(matching_data['key_achievements'][:5], 1):
                    formatted_parts.append(f"{i}. {achievement['achievement']} ({achievement['company']})")
        
        # 職歴詳細
        raw_data = data.get('raw_data', {})
        career_history = raw_data.get('career_history', [])
        if career_history:
            formatted_parts.append("\n### 職歴詳細（時系列）")
            for job in career_history[:3]:  # 直近3社まで
                period = f"{job.get('period', {}).get('start', '不明')} - {job.get('period', {}).get('end', '現在')}"
                formatted_parts.append(f"\n**{period}: {job.get('company', '不明')} - {job.get('role', '不明')}**")
                if job.get('responsibilities'):
                    formatted_parts.append("担当業務:")
                    for resp in job['responsibilities'][:3]:
                        formatted_parts.append(f"- {resp}")
                if job.get('achievements'):
                    formatted_parts.append("実績:")
                    for ach in job['achievements'][:2]:
                        formatted_parts.append(f"- {ach}")
        
        return '\n'.join(formatted_parts) if formatted_parts else ""
    
    @staticmethod
    def format_additional_info(search_results: Dict) -> str:
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
    
    @staticmethod
    def format_history(history: List) -> str:
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
    
    @staticmethod
    async def get_candidate_info(state: ResearchState) -> str:
        """候補者基本情報を取得（Supabase連携を含む）"""
        info_parts = []
        
        # デバッグログ
        print(f"    [候補者情報取得] candidate_id: {getattr(state, 'candidate_id', 'None')}")
        
        # 基本情報の組み立て
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
    
    @staticmethod
    def format_rag_insights(state: ResearchState) -> str:
        """RAG洞察をフォーマット"""
        if not hasattr(state, 'rag_insights') or not state.rag_insights:
            return ""
        
        insights = state.rag_insights
        text = "\n### 類似ケースからの洞察"
        
        # 類似候補者
        if insights.get('similar_candidates'):
            text += "\n類似候補者の実績:"
            for candidate in insights['similar_candidates'][:2]:  # 上位2件
                text += f"\n- スコア{candidate['score']}点: {candidate['key_strength']}"
        
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