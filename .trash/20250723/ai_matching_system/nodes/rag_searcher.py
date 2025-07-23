"""
RAG検索ノード - 過去の類似ケースを検索して評価に活用
"""

import os
from typing import Dict, List, Optional
import google.generativeai as genai
try:
    from pinecone import Pinecone  # 新しいバージョン
except ImportError:
    import pinecone  # 古いバージョン
    Pinecone = None

from .base import BaseNode, ResearchState


class RAGSearcherNode(BaseNode):
    """過去の類似ケースを検索するノード"""
    
    def __init__(self, gemini_api_key: str, pinecone_api_key: str = None):
        super().__init__("RAGSearcher")
        
        # Gemini Embedding APIの設定
        genai.configure(api_key=gemini_api_key)
        self.embedding_model = "models/text-embedding-004"
        
        # Pineconeの設定（オプション）
        self.pinecone_enabled = False
        if pinecone_api_key:
            try:
                if Pinecone:  # 新しいバージョン
                    self.pc = Pinecone(api_key=pinecone_api_key)
                    self.index_name = "recruitment-matching"
                    self.namespace = "historical-cases"
                    self.index = self.pc.Index(self.index_name)
                else:  # 古いバージョン
                    pinecone.init(api_key=pinecone_api_key)
                    self.index_name = "recruitment-matching"
                    self.namespace = "historical-cases"
                    self.index = pinecone.Index(self.index_name)
                self.pinecone_enabled = True
                print("  RAGSearcher: Pinecone接続成功")
            except Exception as e:
                print(f"  RAGSearcher: Pinecone接続失敗 - {e}")
                print("  類似ケース検索は無効化されます")
    
    async def process(self, state: ResearchState) -> ResearchState:
        """類似ケースを検索して状態を更新"""
        self.state = "processing"
        
        if not self.pinecone_enabled:
            print("  RAGSearcher: Pineconeが設定されていないためスキップ")
            self.state = "completed"
            return state
        
        print(f"  過去の類似ケースを検索中...")
        
        # クエリテキストの生成
        query_text = self._create_query_text(state)
        
        # 類似ケース検索
        similar_cases = self._search_similar_cases(query_text)
        
        if similar_cases:
            print(f"  {len(similar_cases)}件の類似ケースを発見")
            
            # 分析結果を生成
            insights = self._analyze_similar_cases(similar_cases)
            
            # 状態に追加
            state.similar_cases = similar_cases
            state.rag_insights = insights
            
            # 評価への補足情報として追加
            if insights.get('risk_factors'):
                print(f"  リスク要因: {len(insights['risk_factors'])}件")
            if insights.get('client_tendency'):
                print(f"  クライアント評価傾向: {insights['client_tendency']}")
        else:
            print("  類似ケースが見つかりませんでした")
        
        self.state = "completed"
        return state
    
    def _create_query_text(self, state: ResearchState) -> str:
        """検索用のクエリテキストを生成"""
        # 現在の評価情報を含めたクエリ
        eval_text = ""
        if state.current_evaluation:
            eval_text = f"""
現在の評価:
スコア: {state.current_evaluation.score}
主な強み: {', '.join(state.current_evaluation.strengths[:2])}
主な懸念: {', '.join(state.current_evaluation.concerns[:2])}
"""
        
        query = f"""
求人情報: {state.job_description}
求人詳細: {state.job_memo}
候補者情報: {state.resume}
{eval_text}
"""
        return query
    
    def _search_similar_cases(self, query_text: str, top_k: int = 10) -> List[Dict]:
        """Pineconeから類似ケースを検索"""
        try:
            # ベクトル生成
            result = genai.embed_content(
                model=self.embedding_model,
                content=query_text,
                task_type="retrieval_query"
            )
            query_embedding = result['embedding']
            
            # 検索実行
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=self.namespace,
                filter={"vector_type": "combined"},
                include_metadata=True
            )
            
            # 結果の整形
            similar_cases = []
            for match in results['matches']:
                if match['score'] > 0.7:  # 類似度閾値
                    case = {
                        'score': match['score'],
                        'case_id': match['metadata'].get('case_id', ''),
                        'ai_recommendation': match['metadata'].get('ai_recommendation', ''),
                        'client_evaluation': match['metadata'].get('client_evaluation', ''),
                        'client_comment': match['metadata'].get('client_comment', ''),
                        'reasoning': match['metadata'].get('reasoning', ''),
                        'evaluation_match': match['metadata'].get('evaluation_match', False)
                    }
                    similar_cases.append(case)
            
            return similar_cases
            
        except Exception as e:
            print(f"  類似ケース検索エラー: {e}")
            return []
    
    def _analyze_similar_cases(self, similar_cases: List[Dict]) -> Dict:
        """類似ケースを分析して洞察を生成"""
        insights = {
            'total_cases': len(similar_cases),
            'client_tendency': None,
            'risk_factors': [],
            'success_patterns': []
        }
        
        if not similar_cases:
            return insights
        
        # クライアント評価の傾向分析
        client_evals = [c['client_evaluation'] for c in similar_cases if c.get('client_evaluation')]
        if client_evals:
            eval_counts = {}
            for eval in client_evals:
                eval_counts[eval] = eval_counts.get(eval, 0) + 1
            
            # 最も多い評価
            most_common = max(eval_counts.items(), key=lambda x: x[1])
            insights['client_tendency'] = {
                'most_common_evaluation': most_common[0],
                'percentage': most_common[1] / len(client_evals) * 100
            }
        
        # リスク要因の抽出（評価が不一致のケース）
        mismatches = [c for c in similar_cases if not c.get('evaluation_match', False)]
        for mismatch in mismatches[:3]:  # 上位3件
            if mismatch.get('client_comment'):
                insights['risk_factors'].append({
                    'pattern': f"AI:{mismatch['ai_recommendation']} → Client:{mismatch['client_evaluation']}",
                    'reason': mismatch['client_comment'],
                    'similarity': mismatch['score']
                })
        
        # 成功パターンの抽出（高評価で一致）
        successes = [c for c in similar_cases 
                    if c.get('evaluation_match', False) 
                    and c.get('client_evaluation') in ['A', 'B']]
        for success in successes[:2]:  # 上位2件
            insights['success_patterns'].append({
                'evaluation': success['client_evaluation'],
                'key_factor': success.get('reasoning', '')[:100],
                'similarity': success['score']
            })
        
        return insights