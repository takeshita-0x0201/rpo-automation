"""
候補者評価ノード
"""

import os
from typing import Dict, List, Optional
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

from .base import BaseNode, ResearchState, EvaluationResult, ScoreDetail
from ..utils.semantic_guards import SemanticGuards
from ..utils.evaluation_formatters import EvaluationFormatters
from ..utils.evaluation_parser import EvaluationParser
from ..prompts import EvaluationPrompts, ScoringCriteria, RequirementRules


class EvaluatorNode(BaseNode):
    """候補者を評価するノード"""
    
    def __init__(self, api_key: str, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        super().__init__("Evaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Supabaseクライアントの初期化
        self.supabase_client = None
        
        # dotenvから環境変数を読み込む（親ディレクトリの.envも探す）
        from dotenv import load_dotenv
        from pathlib import Path
        
        # 現在のディレクトリから上位に遡って.envを探す
        current_path = Path(__file__).resolve()
        for parent in [current_path.parent, current_path.parent.parent, current_path.parent.parent.parent, current_path.parent.parent.parent.parent]:
            env_path = parent / '.env'
            if env_path.exists():
                print(f"[EvaluatorNode初期化] .envファイルを発見: {env_path}")
                load_dotenv(env_path)
                break
        else:
            # 見つからない場合はデフォルトの動作
            load_dotenv()
        
        # デバッグ: 環境変数の状態を確認
        env_url = os.getenv("SUPABASE_URL")
        env_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        print(f"[EvaluatorNode初期化] SUPABASE_URL from env: {env_url is not None}")
        print(f"[EvaluatorNode初期化] SUPABASE_KEY/ANON_KEY from env: {env_key is not None}")
        
        if supabase_url and supabase_key:
            print(f"[EvaluatorNode初期化] 引数から Supabase設定を使用")
            self.supabase_client = create_client(supabase_url, supabase_key)
        elif env_url and env_key:
            print(f"[EvaluatorNode初期化] 環境変数から Supabase設定を使用")
            self.supabase_client = create_client(env_url, env_key)
        else:
            print(f"[EvaluatorNode初期化] Supabase設定が見つかりません")
    
    async def process(self, state: ResearchState) -> ResearchState:
        """候補者を現在の情報で評価"""
        self.state = "processing"
        
        print(f"  候補者評価を開始（サイクル{state.current_cycle}）")
        
        # 追加情報のフォーマット
        additional_info = EvaluationFormatters.format_additional_info(state.search_results)
        if additional_info:
            print(f"  追加情報を含めて評価: {len(state.search_results)}件の検索結果")
        
        # 評価履歴のフォーマット
        history_text = EvaluationFormatters.format_history(state.evaluation_history)
        if state.evaluation_history:
            print(f"  過去の評価履歴を考慮: {len(state.evaluation_history)}サイクル分")
        
        # RAG洞察のフォーマット
        rag_insights_text = EvaluationFormatters.format_rag_insights(state)
        if hasattr(state, 'rag_insights') and state.rag_insights:
            print(f"  類似ケースの洞察を活用")
        
        # 候補者情報を取得
        candidate_info = await EvaluationFormatters.get_candidate_info(state)
        
        # セマンティックガードによる事前チェック
        guard_insights = self._apply_semantic_guards(state)
        
        # 構造化データの存在チェック
        has_structured_job_data = hasattr(state, 'structured_job_data') and state.structured_job_data
        structured_job_data_text = EvaluationFormatters.format_structured_job_data(state) if has_structured_job_data else ''
        
        has_structured_resume_data = hasattr(state, 'structured_resume_data') and state.structured_resume_data
        structured_resume_data_text = EvaluationFormatters.format_structured_resume_data(state) if has_structured_resume_data else ''
        
        # テンプレートを使用してプロンプトを構築
        input_data_section = EvaluationPrompts.build_input_data_section(
            resume=state.resume,
            candidate_info=candidate_info,
            structured_resume_data=structured_resume_data_text,
            structured_job_data=structured_job_data_text,
            job_description=state.job_description or "",
            job_memo=state.job_memo or "",
            additional_info=additional_info,
            history_text=history_text,
            rag_insights_text=rag_insights_text,
            guard_insights=guard_insights
        )
        
        # プロンプトを組み立て
        prompt = f"""{EvaluationPrompts.ROLE_SETTING}

{EvaluationPrompts.EVALUATION_RULES}

{input_data_section}

{RequirementRules.REQUIREMENT_DISTINCTION}

{EvaluationPrompts.SEMANTIC_UNDERSTANDING}

{ScoringCriteria.get_formatted_categories()}

{ScoringCriteria.SCORING_GUIDELINES}

{EvaluationPrompts.BALANCED_EVALUATION}

{ScoringCriteria.OUTPUT_FORMAT}

{RequirementRules.format_strengths_section()}

{RequirementRules.CONCERN_WRITING_RULES}

{ScoringCriteria.SUMMARY_FORMAT}

{RequirementRules.EVALUATION_NOTES}"""
        
        print(f"  LLMにプロンプト送信中... (文字数: {len(prompt)})")
        response = self.model.generate_content(prompt)
        print(f"  LLMから応答受信")
        
        # デバッグモードの場合、生の応答を表示
        if os.getenv('DEBUG_MODE'):
            print(f"  LLM応答（最初の500文字）:")
            print(f"    {response.text[:500]}")
            print("    ...")
        
        evaluation = EvaluationParser.parse_evaluation(response.text)
        print(f"  評価結果パース完了")
        
        # 状態を更新
        state.current_evaluation = evaluation
        self.state = "completed"
        
        return state
    
    def _apply_semantic_guards(self, state: ResearchState) -> str:
        """セマンティックガードレールを適用して洞察を生成"""
        insights = []
        
        # 営業経験の検出
        if hasattr(state, 'job_description') and '営業' in state.job_description:
            has_sales, confidence, evidence = SemanticGuards.detect_sales_experience(state.resume)
            
            if evidence:
                insights.append("\n### セマンティック分析による営業経験の検出")
                insights.append(f"営業経験の可能性: {'高' if confidence > 0.7 else '中' if confidence > 0.4 else '低'} (確信度: {confidence:.1%})")
                insights.append("検出された要素:")
                for e in evidence[:3]:  # 最大3つまで
                    insights.append(f"- {e}")
                
                if has_sales and confidence < 0.7:
                    insights.append("※ 間接的な指標から営業要素を検出。詳細な評価が必要")
        
        # 職種マッチングの評価（必要に応じて）
        # ここに追加の分析を実装可能
        
        return '\n'.join(insights) if insights else ""