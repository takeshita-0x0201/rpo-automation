"""
Gemini Embedding APIのラッパー
"""

import os
import hashlib
from typing import List, Dict, Optional, Tuple
import google.generativeai as genai
import tiktoken
import re


class GeminiEmbedder:
    """Gemini Embedding APIを使用してテキストをベクトル化"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Gemini API key. 指定なしの場合は環境変数から取得
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=self.api_key)
        self.model_name = "models/text-embedding-004"
        self.max_tokens = 2048  # Geminiの推奨トークン数制限
        
        # キャッシュ（開発時の無駄なAPI呼び出しを防ぐ）
        self._cache = {}
        
    def embed_text(self, text: str, task_type: str = "retrieval_document", 
                   text_type: str = "general", auto_truncate: bool = True) -> List[float]:
        """
        単一のテキストをベクトル化
        
        Args:
            text: ベクトル化するテキスト
            task_type: タスクタイプ。"retrieval_document" or "retrieval_query"
            text_type: テキストの種類（job_description, resume, general）
            auto_truncate: 自動的にテキストを切り詰めるか
            
        Returns:
            768次元のベクトル
        """
        # 前処理
        if auto_truncate:
            text = self._truncate_text(text)
            
        # キャッシュチェック
        cache_key = self._get_cache_key(text, task_type)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type=task_type
            )
            
            embedding = result['embedding']
            
            # キャッシュに保存
            self._cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            print(f"Embedding error: {e}")
            # テキストが長すぎる場合は、重要情報のみ抽出して再試行
            if "token" in str(e).lower() and auto_truncate:
                print(f"Retrying with extracted key information...")
                extracted_text = self._extract_key_information(text, text_type)
                return self.embed_text(extracted_text, task_type, text_type, False)
            raise
    
    def embed_batch(self, texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
        """
        複数のテキストを一括でベクトル化
        
        Args:
            texts: ベクトル化するテキストのリスト
            task_type: タスクタイプ
            
        Returns:
            ベクトルのリスト
        """
        embeddings = []
        
        # 現在のGemini APIはバッチ処理に制限があるため、個別に処理
        # 将来的にバッチAPIが改善されたら最適化可能
        for text in texts:
            embedding = self.embed_text(text, task_type)
            embeddings.append(embedding)
            
        return embeddings
    
    def embed_case_components(self, case_data: Dict) -> Dict[str, List[float]]:
        """
        評価ケースの各コンポーネントをベクトル化
        
        Args:
            case_data: 評価ケースデータ
            
        Returns:
            各コンポーネントのベクトル
        """
        vectors = {}
        
        # 1. 統合ベクトル（4要素結合）
        combined_text = f"""
ポジション: {case_data.get('position', '')}
求人内容:
{case_data.get('job_description', '')}
求人メモ:
{case_data.get('job_memo', '')}
候補者情報:
{case_data.get('resume', '')}
"""
        vectors['combined'] = self.embed_text(combined_text)
        
        # 2. 求人側ベクトル（ポジション＋求人票＋メモ）
        job_text = f"""
{case_data.get('position', '')}
{case_data.get('job_description', '')}
{case_data.get('job_memo', '')}
"""
        vectors['job_side'] = self.embed_text(job_text)
        
        # 3. 候補者ベクトル
        vectors['candidate'] = self.embed_text(case_data.get('resume', ''))
        
        # 4. 要約ベクトル（存在する場合）
        if 'job_summary' in case_data:
            vectors['job_summary'] = self.embed_text(case_data['job_summary'])
            
        if 'candidate_summary' in case_data:
            vectors['candidate_summary'] = self.embed_text(case_data['candidate_summary'])
            
        if 'evaluation_summary' in case_data:
            summary_text = f"{case_data['position']} → {case_data['evaluation_summary']}"
            vectors['case_summary'] = self.embed_text(summary_text)
        
        return vectors
    
    def embed_search_query(self, query: str) -> List[float]:
        """
        検索クエリ用のベクトル化（retrieval_query タスクタイプを使用）
        
        Args:
            query: 検索クエリ
            
        Returns:
            検索用ベクトル
        """
        return self.embed_text(query, task_type="retrieval_query")
    
    def _get_cache_key(self, text: str, task_type: str) -> str:
        """キャッシュキーの生成"""
        content = f"{task_type}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._cache.clear()
        print("Embedding cache cleared")
    
    def _truncate_text(self, text: str, max_tokens: int = None) -> str:
        """
        テキストを最大トークン数に切り詰める
        
        Args:
            text: 切り詰めるテキスト
            max_tokens: 最大トークン数（デフォルトはself.max_tokens）
            
        Returns:
            切り詰められたテキスト
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
            
        # 簡易的なトークン数推定（日本語を考慮）
        # より正確にはtiktokenを使用することも可能
        estimated_tokens = len(text) // 2  # 日本語は概ね2文字で1トークン
        
        if estimated_tokens <= max_tokens:
            return text
            
        # テキストを段落に分割
        paragraphs = text.split('\n\n')
        
        # 重要な情報を優先的に保持
        priority_sections = []
        normal_sections = []
        
        for para in paragraphs:
            # 重要なセクション（タイトルや必須要件など）を識別
            if any(keyword in para for keyword in ['必須', '【', 'ポジション', '経験', 'スキル']):
                priority_sections.append(para)
            else:
                normal_sections.append(para)
        
        # 優先セクションから構築
        result = '\n\n'.join(priority_sections)
        
        # 残りのトークン数で通常セクションを追加
        for section in normal_sections:
            test_text = result + '\n\n' + section
            if len(test_text) // 2 <= max_tokens:
                result = test_text
            else:
                break
                
        return result
    
    def _extract_key_information(self, text: str, text_type: str = "general") -> str:
        """
        テキストから重要情報を抽出
        
        Args:
            text: 抽出元のテキスト
            text_type: テキストの種類（job_description, resume, etc）
            
        Returns:
            抽出された重要情報
        """
        if text_type == "job_description":
            # 求人票から重要情報を抽出
            patterns = {
                "position": r"【ポジション】([^\n【]+)",
                "requirements": r"【必須[要件経験スキル]*】([^\n【]+)",
                "responsibilities": r"【[職務業務内容]+】([^\n【]+)",
                "qualifications": r"【[歓迎望ましい]+】([^\n【]+)"
            }
            
            extracted = []
            for key, pattern in patterns.items():
                matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
                if matches:
                    extracted.append(f"{key}: {' '.join(matches)}")
                    
            return '\n'.join(extracted) if extracted else text[:1000]
            
        elif text_type == "resume":
            # レジュメから重要情報を抽出
            # 職歴、スキル、資格などを優先
            lines = text.split('\n')
            important_lines = []
            
            for line in lines:
                if any(keyword in line for keyword in ['経験', '実績', 'スキル', '資格', '職歴', '学歴']):
                    important_lines.append(line)
                    
            return '\n'.join(important_lines) if important_lines else text[:1000]
            
        else:
            # 一般的なテキストの場合は先頭部分を返す
            return text[:1500]