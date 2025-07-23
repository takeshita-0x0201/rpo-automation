"""
求人情報構造化サービス
汎用プロンプトテンプレートを使用して求人票と求人メモから構造化データを生成
"""
import os
import json
import google.generativeai as genai
from typing import Dict, Optional

class JobStructuringService:
    """求人情報を構造化するサービス"""
    
    def __init__(self):
        """初期化"""
        # Gemini APIの設定
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # プロンプトテンプレートのパスを設定
        self.prompt_template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'generic_structure_prompt.txt'
        )
        
        # プロンプトテンプレートを読み込み
        self._load_prompt_template()
    
    def _load_prompt_template(self):
        """プロンプトテンプレートを読み込む"""
        try:
            with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found at {self.prompt_template_path}")
    
    async def structure_job_info(self, job_description: str, job_memo: str) -> Dict:
        """
        求人票と求人メモから構造化データを生成
        
        Args:
            job_description: 求人票のテキスト
            job_memo: 求人メモのテキスト
        
        Returns:
            構造化されたJSONデータ
        """
        # プロンプトを作成
        prompt = self.prompt_template.replace("[求人票の内容]", job_description)
        prompt = prompt.replace("[求人メモの内容]", job_memo)
        
        try:
            # Geminiモデルで処理
            response = self.model.generate_content(prompt)
            
            # レスポンスからJSONを抽出
            json_text = response.text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            
            # JSONとして解析
            structured_data = json.loads(json_text)
            
            # デフォルト値の設定とバリデーション
            structured_data = self._validate_and_set_defaults(structured_data)
            
            return structured_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from AI response: {e}")
        except Exception as e:
            raise Exception(f"Failed to structure job information: {e}")
    
    def _validate_and_set_defaults(self, data: Dict) -> Dict:
        """構造化データのバリデーションとデフォルト値の設定"""
        # 基本情報のデフォルト値
        if 'basic_info' not in data:
            data['basic_info'] = {}
        
        basic_defaults = {
            'title': '',
            'company': '',
            'industry': '',
            'job_type': '',
            'employment_type': '',
            'location': ''
        }
        for key, default in basic_defaults.items():
            if key not in data['basic_info']:
                data['basic_info'][key] = default
        
        # 要件のデフォルト値
        if 'requirements' not in data:
            data['requirements'] = {}
        if 'must_have' not in data['requirements']:
            data['requirements']['must_have'] = []
        if 'nice_to_have' not in data['requirements']:
            data['requirements']['nice_to_have'] = []
        
        # 評価ポイントのデフォルト値
        if 'evaluation_points' not in data:
            data['evaluation_points'] = []
        
        # キーワードのデフォルト値
        if 'keywords' not in data:
            data['keywords'] = {}
        keyword_defaults = {
            'technical': [],
            'soft_skills': [],
            'domain': [],
            'company_culture': []
        }
        for key, default in keyword_defaults.items():
            if key not in data['keywords']:
                data['keywords'][key] = default
        
        # 検索テンプレートのデフォルト値
        if 'search_templates' not in data:
            data['search_templates'] = []
        
        # RAGパラメータのデフォルト値
        if 'rag_parameters' not in data:
            data['rag_parameters'] = {}
        if 'filters' not in data['rag_parameters']:
            data['rag_parameters']['filters'] = {
                'industry': [],
                'job_type': [],
                'skills': []
            }
        if 'similarity_threshold' not in data['rag_parameters']:
            data['rag_parameters']['similarity_threshold'] = 0.7
        if 'relevance_boost_fields' not in data['rag_parameters']:
            data['rag_parameters']['relevance_boost_fields'] = []
        
        return data

# シングルトンインスタンス（遅延初期化）
_job_structuring_service_instance = None

def get_job_structuring_service():
    """シングルトンインスタンスを取得"""
    global _job_structuring_service_instance
    if _job_structuring_service_instance is None:
        _job_structuring_service_instance = JobStructuringService()
    return _job_structuring_service_instance

# 後方互換性のため
job_structuring_service = None  # 実際の使用時にget_job_structuring_service()を呼ぶ