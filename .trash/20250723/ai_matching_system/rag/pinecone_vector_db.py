"""
統一されたPineconeベクトルデータベースインターフェース
ChromaDBからの移行をサポート
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib
from pinecone import Pinecone, ServerlessSpec
import time

from ..embeddings.gemini_embedder import GeminiEmbedder


class UnifiedPineconeDB:
    """統一されたPineconeベクトルデータベース"""
    
    def __init__(self, index_name: str = "recruitment-matching", namespace: str = "historical-cases"):
        """
        初期化
        
        Args:
            index_name: Pineconeインデックス名
            namespace: 名前空間（用途別に分離）
        """
        # Pinecone初期化
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")
            
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.namespace = namespace
        
        # 埋め込みモデル（統一されたGeminiモデル）
        self.embedder = GeminiEmbedder()
        self.dimension = 768
        
        # インデックスの初期化
        self._initialize_index()
        
    def _initialize_index(self):
        """Pineconeインデックスの初期化"""
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
        print(f"Connected to index: {self.index_name} (namespace: {self.namespace})")
        
    def add_evaluation(self, evaluation_data: Dict) -> str:
        """
        評価データを追加（ChromaDB互換インターフェース）
        
        Args:
            evaluation_data: 評価データ
            
        Returns:
            追加されたドキュメントID
        """
        # IDの生成
        if "id" not in evaluation_data:
            evaluation_data["id"] = f"eval_{datetime.now().strftime('%Y%m%d')}_{self._generate_id()}"
            
        doc_id = evaluation_data["id"]
        
        # 3種類のベクトルを生成
        vectors = self._prepare_vectors(evaluation_data)
        
        # Pineconeにアップサート
        self.index.upsert(
            vectors=vectors,
            namespace=self.namespace
        )
        
        print(f"Added evaluation {doc_id} with {len(vectors)} vectors")
        return doc_id
        
    def _prepare_vectors(self, evaluation_data: Dict) -> List[Dict]:
        """評価データから3種類のベクトルを準備"""
        vectors = []
        case_id = evaluation_data.get("id", self._generate_id())
        
        # メタデータの準備（拡張版）
        metadata_base = self._create_enhanced_metadata(evaluation_data)
        
        # 1. Combined vector (統合ベクトル)
        combined_text = self._create_combined_text(evaluation_data)
        combined_embedding = self.embedder.embed_text(
            combined_text, 
            text_type="general",
            auto_truncate=True
        )
        
        vectors.append({
            "id": f"{case_id}_combined",
            "values": combined_embedding,
            "metadata": {
                **metadata_base,
                "vector_type": "combined",
                "text_preview": combined_text[:500]  # デバッグ用
            }
        })
        
        # 2. Job side vector (求人側ベクトル)
        job_text = self._create_job_text(evaluation_data)
        job_embedding = self.embedder.embed_text(
            job_text,
            text_type="job_description",
            auto_truncate=True
        )
        
        vectors.append({
            "id": f"{case_id}_job_side",
            "values": job_embedding,
            "metadata": {
                **metadata_base,
                "vector_type": "job_side"
            }
        })
        
        # 3. Candidate vector (候補者側ベクトル)
        candidate_text = self._create_candidate_text(evaluation_data)
        candidate_embedding = self.embedder.embed_text(
            candidate_text,
            text_type="resume",
            auto_truncate=True
        )
        
        vectors.append({
            "id": f"{case_id}_candidate",
            "values": candidate_embedding,
            "metadata": {
                **metadata_base,
                "vector_type": "candidate"
            }
        })
        
        return vectors
        
    def _create_enhanced_metadata(self, evaluation_data: Dict) -> Dict:
        """拡張されたメタデータ構造"""
        job_req = evaluation_data.get("job_requirement", {})
        candidate = evaluation_data.get("candidate_resume", {})
        ai_eval = evaluation_data.get("ai_evaluation", {})
        human_review = evaluation_data.get("human_review", {})
        
        # 基本メタデータ
        metadata = {
            "case_id": evaluation_data.get("id"),
            "created_at": evaluation_data.get("timestamp", datetime.now().isoformat()),
            
            # ジョブ情報
            "position": job_req.get("title", ""),
            "company": job_req.get("company", ""),
            "job_id": job_req.get("id", ""),
            
            # 候補者情報
            "candidate_id": candidate.get("id", ""),
            "candidate_experience": self._extract_years_from_text(candidate.get("experience", "")),
            
            # AI評価
            "ai_score": ai_eval.get("score", 0),
            "ai_grade": ai_eval.get("grade", ""),
            "ai_recommendation": ai_eval.get("grade", ""),  # グレードを推奨度として使用
            
            # 人間評価
            "human_score": human_review.get("final_score", 0),
            "human_grade": human_review.get("final_grade", ""),
            "reviewer": human_review.get("reviewer", ""),
            
            # 評価の一致度
            "evaluation_match": ai_eval.get("grade", "") == human_review.get("final_grade", ""),
            "score_difference": abs(ai_eval.get("score", 0) - human_review.get("final_score", 0)),
            
            # 検索用フィールド
            "has_human_review": bool(human_review),
            "is_high_quality": human_review.get("final_grade", "") in ["A", "B"],
            "review_decision": human_review.get("decision", ""),
            
            # データ品質フラグ
            "data_completeness": self._calculate_completeness(evaluation_data),
            "data_source": "feedback_loop"  # データの出所
        }
        
        # スキル情報の追加（検索用）
        required_skills = job_req.get("required_skills", [])
        candidate_skills = candidate.get("skills", [])
        if required_skills:
            metadata["required_skills_count"] = len(required_skills)
            metadata["matched_skills_count"] = len(set(required_skills) & set(candidate_skills))
            
        return metadata
        
    def _create_combined_text(self, evaluation_data: Dict) -> str:
        """統合テキストの生成"""
        job_req = evaluation_data.get("job_requirement", {})
        candidate = evaluation_data.get("candidate_resume", {})
        ai_eval = evaluation_data.get("ai_evaluation", {})
        human_review = evaluation_data.get("human_review", {})
        
        sections = []
        
        # ジョブ情報
        sections.append(f"【ポジション】{job_req.get('title', '')}")
        sections.append(f"【企業】{job_req.get('company', '')}")
        if job_req.get("description"):
            sections.append(f"【職務内容】\n{job_req['description']}")
        if job_req.get("required_skills"):
            sections.append(f"【必須スキル】{', '.join(job_req['required_skills'])}")
            
        # 候補者情報
        sections.append(f"\n【候補者ID】{candidate.get('id', '')}")
        if candidate.get("experience"):
            sections.append(f"【経験年数】{candidate['experience']}")
        if candidate.get("skills"):
            sections.append(f"【保有スキル】{', '.join(candidate['skills'])}")
        if candidate.get("work_history"):
            sections.append(f"【職歴】\n{candidate['work_history']}")
            
        # 評価情報
        sections.append(f"\n【AI評価】")
        sections.append(f"スコア: {ai_eval.get('score', 0)}/100")
        sections.append(f"グレード: {ai_eval.get('grade', '')}")
        if ai_eval.get("positive_reasons"):
            sections.append(f"強み: {', '.join(ai_eval['positive_reasons'])}")
        if ai_eval.get("concerns"):
            sections.append(f"懸念: {', '.join(ai_eval['concerns'])}")
            
        # 人間評価
        if human_review:
            sections.append(f"\n【人間評価】")
            sections.append(f"最終スコア: {human_review.get('final_score', 0)}/100")
            sections.append(f"最終グレード: {human_review.get('final_grade', '')}")
            sections.append(f"レビュアー: {human_review.get('reviewer', '')}")
            if human_review.get("comments"):
                sections.append(f"コメント: {human_review['comments']}")
                
        return "\n".join(sections)
        
    def _create_job_text(self, evaluation_data: Dict) -> str:
        """求人側テキストの生成"""
        job_req = evaluation_data.get("job_requirement", {})
        
        sections = []
        sections.append(f"【ポジション】{job_req.get('title', '')}")
        sections.append(f"【企業】{job_req.get('company', '')}")
        
        if job_req.get("description"):
            sections.append(f"【職務内容】\n{job_req['description']}")
        if job_req.get("required_skills"):
            sections.append(f"【必須スキル】{', '.join(job_req['required_skills'])}")
        if job_req.get("preferred_skills"):
            sections.append(f"【歓迎スキル】{', '.join(job_req['preferred_skills'])}")
        if job_req.get("experience_years"):
            sections.append(f"【必要経験年数】{job_req['experience_years']}")
        if job_req.get("team_size"):
            sections.append(f"【チーム規模】{job_req['team_size']}")
        if job_req.get("salary_range"):
            sections.append(f"【想定年収】{job_req['salary_range']}")
            
        return "\n".join(sections)
        
    def _create_candidate_text(self, evaluation_data: Dict) -> str:
        """候補者側テキストの生成"""
        candidate = evaluation_data.get("candidate_resume", {})
        ai_eval = evaluation_data.get("ai_evaluation", {})
        human_review = evaluation_data.get("human_review", {})
        
        sections = []
        
        # 候補者情報
        sections.append(f"【候補者ID】{candidate.get('id', '')}")
        if candidate.get("experience"):
            sections.append(f"【経験年数】{candidate['experience']}")
        if candidate.get("current_position"):
            sections.append(f"【現職】{candidate['current_position']}")
        if candidate.get("skills"):
            sections.append(f"【保有スキル】{', '.join(candidate['skills'])}")
        if candidate.get("work_history"):
            sections.append(f"【職歴】\n{candidate['work_history']}")
        if candidate.get("achievements"):
            sections.append(f"【実績】{candidate['achievements']}")
            
        # 評価結果
        sections.append(f"\n【評価結果】")
        sections.append(f"AIスコア: {ai_eval.get('score', 0)}/100 (グレード: {ai_eval.get('grade', '')})")
        if human_review:
            sections.append(f"人間評価: {human_review.get('final_score', 0)}/100 (グレード: {human_review.get('final_grade', '')})")
            sections.append(f"最終判定: {human_review.get('decision', '')}")
            
        return "\n".join(sections)
        
    def search_similar_cases(
        self, 
        query_text: str,
        filters: Optional[Dict] = None,
        top_k: int = 10,
        vector_type: str = "combined"
    ) -> List[Dict]:
        """
        類似ケースを検索
        
        Args:
            query_text: 検索クエリ
            filters: メタデータフィルタ
            top_k: 返す結果数
            vector_type: 検索対象のベクトルタイプ
            
        Returns:
            検索結果のリスト
        """
        # クエリをベクトル化
        query_vector = self.embedder.embed_text(
            query_text,
            task_type="retrieval_query",
            auto_truncate=True
        )
        
        # フィルタの準備
        if filters is None:
            filters = {}
        filters["vector_type"] = vector_type
        
        # Pineconeで検索
        results = self.index.query(
            vector=query_vector,
            filter=filters,
            top_k=top_k,
            include_metadata=True,
            namespace=self.namespace
        )
        
        # 結果の整形
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            })
            
        return formatted_results
        
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        stats = self.index.describe_index_stats()
        
        namespace_stats = stats.namespaces.get(self.namespace, {})
        
        return {
            "total_vectors": namespace_stats.get("vector_count", 0),
            "index_fullness": stats.get("index_fullness", 0),
            "dimension": stats.get("dimension", self.dimension),
            "namespace": self.namespace,
            "vector_distribution": self._get_vector_distribution()
        }
        
    def _get_vector_distribution(self) -> Dict:
        """ベクトルタイプ別の分布を取得"""
        # 実装は簡略化（実際にはメタデータから集計）
        return {
            "combined": "33%",
            "job_side": "33%",
            "candidate": "33%"
        }
        
    def _extract_years_from_text(self, text: str) -> int:
        """テキストから年数を抽出"""
        import re
        match = re.search(r'(\d+)[年歳]', text)
        return int(match.group(1)) if match else 0
        
    def _calculate_completeness(self, data: Dict) -> float:
        """データの完全性を計算（0-1）"""
        required_fields = [
            "job_requirement", "candidate_resume", 
            "ai_evaluation", "human_review"
        ]
        
        present_fields = sum(1 for field in required_fields if data.get(field))
        return present_fields / len(required_fields)
        
    def _generate_id(self) -> str:
        """ユニークIDを生成"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
        
    # ChromaDB互換メソッド
    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """ChromaDB互換のドキュメント追加メソッド"""
        for doc, metadata, doc_id in zip(documents, metadatas, ids):
            # 評価データ形式に変換
            evaluation_data = {
                "id": doc_id,
                **metadata,
                "combined_text": doc
            }
            self.add_evaluation(evaluation_data)
            
    def query(self, query_texts: List[str], n_results: int = 10, where: Optional[Dict] = None):
        """ChromaDB互換の検索メソッド"""
        all_results = []
        
        for query_text in query_texts:
            results = self.search_similar_cases(
                query_text=query_text,
                filters=where,
                top_k=n_results
            )
            all_results.append(results)
            
        return {
            "documents": [[r.get("metadata", {}).get("text_preview", "") for r in results] for results in all_results],
            "metadatas": [[r.get("metadata", {}) for r in results] for results in all_results],
            "ids": [[r.get("id", "") for r in results] for results in all_results],
            "distances": [[1 - r.get("score", 0) for r in results] for results in all_results]  # cosine距離に変換
        }


# 移行用のエイリアス
RecruitmentVectorDB = UnifiedPineconeDB