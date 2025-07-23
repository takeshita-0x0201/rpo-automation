#!/usr/bin/env python3
"""
新規候補者に対して類似ケースを検索するスクリプト
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import google.generativeai as genai
from pinecone import Pinecone

# プロジェクトのルートパスを追加
sys.path.append(str(Path(__file__).parent.parent))


class SimilarCaseSearcher:
    """類似ケースを検索"""
    
    def __init__(self, gemini_api_key: str, pinecone_api_key: str):
        # Gemini Embedding APIの設定
        genai.configure(api_key=gemini_api_key)
        self.embedding_model = "models/text-embedding-004"
        
        # Pineconeの設定
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index_name = "recruitment-matching"
        self.namespace = "historical-cases"
        self.index = self.pc.Index(self.index_name)
        
    def generate_embedding(self, text: str) -> List[float]:
        """テキストからベクトルを生成"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_query"  # 検索用
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def search_similar_cases(self, query_text: str, vector_type: str = "combined", top_k: int = 5) -> List[Dict]:
        """類似ケースを検索"""
        # クエリのベクトル化
        query_embedding = self.generate_embedding(query_text)
        if not query_embedding:
            return []
        
        # フィルター条件
        filter_dict = {"vector_type": vector_type}
        
        # 検索実行
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=self.namespace,
            filter=filter_dict,
            include_metadata=True
        )
        
        # 結果の整形
        similar_cases = []
        for match in results['matches']:
            case = {
                'score': match['score'],
                'case_id': match['metadata'].get('case_id', ''),
                'position': match['metadata'].get('position', ''),
                'ai_recommendation': match['metadata'].get('ai_recommendation', ''),
                'client_evaluation': match['metadata'].get('client_evaluation', ''),
                'client_comment': match['metadata'].get('client_comment', ''),
                'reasoning': match['metadata'].get('reasoning', ''),
                'evaluation_match': match['metadata'].get('evaluation_match', False)
            }
            similar_cases.append(case)
        
        return similar_cases
    
    def search_for_new_candidate(self, job_desc: str, job_memo: str, resume: str) -> Dict:
        """新規候補者に対する総合的な類似ケース検索"""
        results = {}
        
        # 1. 結合ベクトルでの検索（最も包括的）
        combined_query = f"""
求人情報: {job_desc}
求人詳細: {job_memo}
候補者情報: {resume}
"""
        results['combined_matches'] = self.search_similar_cases(
            combined_query, 
            vector_type="combined", 
            top_k=10
        )
        
        # 2. 求人側ベクトルでの検索（同じような求人）
        job_query = f"""
求人情報: {job_desc}
求人詳細: {job_memo}
"""
        results['job_matches'] = self.search_similar_cases(
            job_query, 
            vector_type="job_side", 
            top_k=5
        )
        
        # 3. 候補者ベクトルでの検索（似た経歴の候補者）
        candidate_query = f"""
候補者情報: {resume}
"""
        results['candidate_matches'] = self.search_similar_cases(
            candidate_query, 
            vector_type="candidate", 
            top_k=5
        )
        
        return results
    
    def analyze_search_results(self, results: Dict) -> Dict:
        """検索結果を分析して洞察を提供"""
        analysis = {
            'similar_case_insights': [],
            'client_evaluation_trends': {},
            'risk_factors': []
        }
        
        # 結合マッチの分析
        combined_matches = results.get('combined_matches', [])
        if combined_matches:
            # クライアント評価の傾向
            client_evals = [m['client_evaluation'] for m in combined_matches if m['client_evaluation']]
            for eval in set(client_evals):
                count = client_evals.count(eval)
                analysis['client_evaluation_trends'][eval] = {
                    'count': count,
                    'percentage': count / len(client_evals) * 100 if client_evals else 0
                }
            
            # リスク要因の抽出
            mismatches = [m for m in combined_matches if not m.get('evaluation_match', False)]
            if mismatches:
                for m in mismatches[:3]:  # 上位3件
                    if m.get('client_comment'):
                        analysis['risk_factors'].append({
                            'ai_evaluation': m['ai_recommendation'],
                            'client_evaluation': m['client_evaluation'],
                            'reason': m['client_comment']
                        })
            
            # 類似ケースからの洞察
            top_matches = combined_matches[:3]
            for match in top_matches:
                insight = {
                    'similarity_score': match['score'],
                    'ai_evaluation': match['ai_recommendation'],
                    'client_evaluation': match['client_evaluation'],
                    'match_status': match['evaluation_match'],
                    'key_point': match.get('client_comment', match.get('reasoning', ''))[:100]
                }
                analysis['similar_case_insights'].append(insight)
        
        return analysis


def print_search_results(results: Dict, analysis: Dict):
    """検索結果を見やすく表示"""
    print("\n" + "="*60)
    print("類似ケース検索結果")
    print("="*60)
    
    # 総合的な類似ケース
    print("\n【最も類似したケース（総合）】")
    for i, case in enumerate(results['combined_matches'][:5], 1):
        print(f"\n{i}. 類似度: {case['score']:.3f}")
        print(f"   AI評価: {case['ai_recommendation']} / クライアント: {case['client_evaluation']}")
        print(f"   一致: {'○' if case['evaluation_match'] else '×'}")
        if case.get('client_comment'):
            print(f"   クライアントコメント: {case['client_comment']}")
    
    # 分析結果
    print("\n\n【分析結果】")
    
    print("\n1. クライアント評価の傾向")
    for eval, stats in analysis['client_evaluation_trends'].items():
        print(f"   {eval}: {stats['count']}件 ({stats['percentage']:.1f}%)")
    
    if analysis['risk_factors']:
        print("\n2. 注意すべきリスク要因")
        for risk in analysis['risk_factors']:
            print(f"   - AI:{risk['ai_evaluation']} → クライアント:{risk['client_evaluation']}")
            print(f"     理由: {risk['reason']}")
    
    print("\n3. 推奨アクション")
    # 傾向に基づく推奨
    trends = analysis['client_evaluation_trends']
    if 'D' in trends and trends['D']['percentage'] > 50:
        print("   ⚠️ 類似ケースの多くがNG判定です。要件の再確認を推奨します。")
    elif 'A' in trends and trends['A']['percentage'] > 30:
        print("   ✅ 類似ケースで高評価が多いです。積極的に推薦可能です。")
    
    # ミスマッチ傾向
    total_cases = len(results['combined_matches'])
    mismatch_count = sum(1 for c in results['combined_matches'] if not c['evaluation_match'])
    if total_cases > 0 and mismatch_count / total_cases > 0.5:
        print("   ⚠️ AI評価とクライアント評価の乖離が多いパターンです。慎重な評価を。")


def main():
    parser = argparse.ArgumentParser(description='新規候補者の類似ケース検索')
    parser.add_argument('resume', help='候補者レジュメファイル')
    parser.add_argument('job_description', help='求人票ファイル')
    parser.add_argument('job_memo', help='求人メモファイル')
    parser.add_argument('--top-k', type=int, default=10, help='取得する類似ケース数')
    args = parser.parse_args()
    
    # APIキーの確認
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    
    if not gemini_api_key or not pinecone_api_key:
        print("エラー: GEMINI_API_KEYとPINECONE_API_KEY環境変数を設定してください")
        return
    
    # ファイル読み込み
    try:
        with open(args.resume, 'r', encoding='utf-8') as f:
            resume_text = f.read()
        with open(args.job_description, 'r', encoding='utf-8') as f:
            job_desc_text = f.read()
        with open(args.job_memo, 'r', encoding='utf-8') as f:
            job_memo_text = f.read()
    except FileNotFoundError as e:
        print(f"エラー: ファイルが見つかりません - {e}")
        return
    
    # 検索実行
    searcher = SimilarCaseSearcher(gemini_api_key, pinecone_api_key)
    
    print("類似ケースを検索中...")
    results = searcher.search_for_new_candidate(
        job_desc_text,
        job_memo_text,
        resume_text
    )
    
    # 結果分析
    analysis = searcher.analyze_search_results(results)
    
    # 結果表示
    print_search_results(results, analysis)
    
    # JSON形式で保存
    output_data = {
        'search_results': results,
        'analysis': analysis
    }
    
    output_file = 'similar_cases_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n詳細な結果を {output_file} に保存しました")


if __name__ == "__main__":
    main()