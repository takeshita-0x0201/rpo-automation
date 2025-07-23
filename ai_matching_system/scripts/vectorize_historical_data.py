#!/usr/bin/env python3
"""
過去の評価データをベクトル化してPineconeに保存するスクリプト
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

# プロジェクトのルートパスを追加
sys.path.append(str(Path(__file__).parent.parent))


class HistoricalDataVectorizer:
    """過去の評価データをベクトル化"""
    
    def __init__(self, gemini_api_key: str, pinecone_api_key: str):
        # Gemini Embedding APIの設定
        genai.configure(api_key=gemini_api_key)
        self.embedding_model = "models/text-embedding-004"
        
        # Pineconeの設定
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index_name = "recruitment-matching"
        self.namespace = "historical-cases"
        self.dimension = 768
        
        # インデックスの初期化
        self._initialize_index()
        
    def _initialize_index(self):
        """Pineconeインデックスの初期化"""
        # 既存のインデックスを確認
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            print(f"Creating index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # インデックスが準備できるまで待機
            time.sleep(10)
        
        self.index = self.pc.Index(self.index_name)
        print(f"Connected to index: {self.index_name}")
        
    def generate_embedding(self, text: str) -> List[float]:
        """テキストからベクトルを生成"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
            
    def prepare_vectors_from_case(self, case_data: Dict, job_info: Dict) -> List[Tuple[str, List[float], Dict]]:
        """1つのケースから3つのベクトルを準備"""
        vectors = []
        
        # case_idの生成
        base_case_id = f"{case_data['case_id']}_{case_data.get('management_number', 'unknown')}"
        
        # AI評価情報の整形
        ai_eval_text = ""
        if case_data.get('ai_evaluation'):
            ai_eval = case_data['ai_evaluation']
            ai_eval_text = f"""
推奨度: {ai_eval.get('recommendation', '')}
スコア: {ai_eval.get('score', '')}
評価理由: {ai_eval.get('reasoning', '')}
"""
        
        # 1. combined_vector（結合ベクトル）
        combined_text = f"""
求人情報: {job_info.get('job_description', '')}
求人詳細: {job_info.get('job_memo', '')}
候補者情報: {case_data.get('resume_text', '')}
評価結果: {ai_eval_text}
"""
        combined_embedding = self.generate_embedding(combined_text)
        if combined_embedding:
            metadata = self._create_metadata(case_data, "combined", job_info.get('position', ''))
            vectors.append((f"{base_case_id}_combined", combined_embedding, metadata))
        
        # 2. job_side_vector（求人側ベクトル）
        job_text = f"""
求人情報: {job_info.get('job_description', '')}
求人詳細: {job_info.get('job_memo', '')}
"""
        job_embedding = self.generate_embedding(job_text)
        if job_embedding:
            metadata = self._create_metadata(case_data, "job_side", job_info.get('position', ''))
            vectors.append((f"{base_case_id}_job_side", job_embedding, metadata))
        
        # 3. candidate_vector（候補者ベクトル）
        candidate_text = f"""
候補者情報: {case_data.get('resume_text', '')}
評価結果: {ai_eval_text}
"""
        candidate_embedding = self.generate_embedding(candidate_text)
        if candidate_embedding:
            metadata = self._create_metadata(case_data, "candidate", job_info.get('position', ''))
            vectors.append((f"{base_case_id}_candidate", candidate_embedding, metadata))
        
        return vectors
    
    def _create_metadata(self, case_data: Dict, vector_type: str, position: str) -> Dict:
        """メタデータの作成"""
        metadata = {
            "case_id": f"{case_data['case_id']}_{case_data.get('management_number', 'unknown')}",
            "position": position,
            "vector_type": vector_type,
            "created_at": datetime.now().isoformat()
        }
        
        # AI評価情報
        if case_data.get('ai_evaluation'):
            ai_eval = case_data['ai_evaluation']
            metadata.update({
                "ai_recommendation": ai_eval.get('recommendation', ''),
                "score": ai_eval.get('score', 0),
                "reasoning": ai_eval.get('reasoning', '')[:500]  # Pineconeのメタデータサイズ制限のため
            })
        
        # クライアント評価情報
        if case_data.get('client_evaluation'):
            metadata['client_evaluation'] = case_data['client_evaluation']
        
        if case_data.get('client_comment'):
            metadata['client_comment'] = case_data['client_comment'][:500]  # サイズ制限
            
        # 評価の一致/不一致
        if case_data.get('comparison'):
            metadata['evaluation_match'] = case_data['comparison'].get('match', False)
        
        return metadata
    
    def vectorize_and_store(self, evaluation_data: Dict, batch_size: int = 100):
        """評価データをベクトル化してPineconeに保存"""
        evaluations = evaluation_data.get('evaluations', [])
        job_info = {
            'position': evaluation_data.get('position', ''),
            'job_description': evaluation_data.get('job_description', ''),
            'job_memo': evaluation_data.get('job_memo', '')
        }
        
        print(f"\n=== ベクトル化開始 ===")
        print(f"総ケース数: {len(evaluations)}")
        
        all_vectors = []
        
        # 各ケースをベクトル化
        for eval_data in tqdm(evaluations, desc="ベクトル生成"):
            if eval_data.get('ai_evaluation'):
                # レジュメテキストを追加（実際のデータ構造に合わせて調整が必要）
                eval_data['resume_text'] = eval_data.get('resume_text', '')
                
                vectors = self.prepare_vectors_from_case(eval_data, job_info)
                all_vectors.extend(vectors)
                
                # API制限対策
                time.sleep(0.1)
        
        print(f"\n生成されたベクトル数: {len(all_vectors)}")
        
        # バッチでPineconeに保存
        print("\nPineconeへの保存開始...")
        for i in range(0, len(all_vectors), batch_size):
            batch = all_vectors[i:i + batch_size]
            
            # Pinecone用のフォーマットに変換
            upsert_data = []
            for vector_id, embedding, metadata in batch:
                upsert_data.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })
            
            # アップサート
            self.index.upsert(
                vectors=upsert_data,
                namespace=self.namespace
            )
            
            print(f"  {min(i + batch_size, len(all_vectors))}/{len(all_vectors)} ベクトルを保存")
        
        print("\n=== ベクトル化完了 ===")
        
        # 統計情報を表示
        stats = self.index.describe_index_stats()
        print(f"\nインデックス統計:")
        print(f"  総ベクトル数: {stats['total_vector_count']}")
        print(f"  名前空間: {self.namespace}")
        
        return len(all_vectors)


def load_evaluation_data(json_path: str) -> Dict:
    """評価結果JSONを読み込み"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_job_info(job_desc_path: str, job_memo_path: str) -> Dict:
    """求人情報を読み込み"""
    job_info = {}
    
    if os.path.exists(job_desc_path):
        with open(job_desc_path, 'r', encoding='utf-8') as f:
            job_info['job_description'] = f.read()
    
    if os.path.exists(job_memo_path):
        with open(job_memo_path, 'r', encoding='utf-8') as f:
            job_info['job_memo'] = f.read()
    
    return job_info


def main():
    parser = argparse.ArgumentParser(description='過去の評価データをベクトル化')
    parser.add_argument('evaluation_json', help='評価結果のJSONファイル')
    parser.add_argument('--job-desc', help='求人票ファイル', default='sample_data/job_description.txt')
    parser.add_argument('--job-memo', help='求人メモファイル', default='sample_data/job_memo.txt')
    parser.add_argument('--batch-size', type=int, default=100, help='バッチサイズ')
    args = parser.parse_args()
    
    # APIキーの確認
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    
    if not gemini_api_key:
        print("エラー: GEMINI_API_KEY環境変数が設定されていません")
        return
    
    if not pinecone_api_key:
        print("エラー: PINECONE_API_KEY環境変数が設定されていません")
        return
    
    # データの読み込み
    print("評価データを読み込み中...")
    evaluation_data = load_evaluation_data(args.evaluation_json)
    
    # 求人情報の読み込み
    job_info = load_job_info(args.job_desc, args.job_memo)
    evaluation_data.update(job_info)
    
    # ベクトル化実行
    vectorizer = HistoricalDataVectorizer(gemini_api_key, pinecone_api_key)
    
    try:
        vector_count = vectorizer.vectorize_and_store(
            evaluation_data,
            batch_size=args.batch_size
        )
        print(f"\n✅ {vector_count}個のベクトルを正常に保存しました")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()