"""Vector Database for Recruitment RAG System"""

import os
from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
import json
from datetime import datetime


class RecruitmentVectorDB:
    """過去の採用評価データを管理するベクトルデータベース"""
    
    def __init__(self, persist_directory: str = "./recruitment_vectors"):
        """
        Args:
            persist_directory: ベクトルデータの保存先ディレクトリ
        """
        # Embeddingモデルの初期化
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",  # 高精度な3072次元
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # ChromaDBクライアントの初期化
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # コレクション（テーブル）の作成
        try:
            self.collection = self.client.get_collection(
                name="recruitment_evaluations"
            )
        except:
            self.collection = self.client.create_collection(
                name="recruitment_evaluations",
                metadata={"hnsw:space": "cosine"}  # コサイン類似度を使用
            )
        
        # LangChain用のベクトルストア
        self.vectorstore = Chroma(
            client=self.client,
            collection_name="recruitment_evaluations",
            embedding_function=self.embeddings
        )
    
    def add_evaluation(self, evaluation_data: Dict) -> str:
        """評価データをベクトルDBに追加"""
        # テキストの作成
        text = self._create_searchable_text(
            evaluation_data["job_requirement"],
            evaluation_data["candidate_resume"]
        )
        
        # メタデータの準備
        metadata = {
            "id": evaluation_data["id"],
            "final_grade": evaluation_data["human_review"]["final_grade"],
            "final_score": evaluation_data["human_review"]["final_score"],
            "positive_summary": self._summarize_reasons(
                evaluation_data["ai_evaluation"]["positive_reasons"]
            ),
            "concern_summary": self._summarize_reasons(
                evaluation_data["ai_evaluation"]["concerns"]
            ),
            "decision": evaluation_data["human_review"]["decision"],
            "job_id": evaluation_data["job_requirement"].get("id"),
            "candidate_id": evaluation_data["candidate_resume"].get("id"),
            "reviewer": evaluation_data["human_review"]["reviewer"],
            "timestamp": evaluation_data["timestamp"],
            "job_title": evaluation_data["job_requirement"]["title"],
            "company": evaluation_data["job_requirement"]["company"]
        }
        
        # ベクトルDBに追加
        self.vectorstore.add_texts(
            texts=[text],
            metadatas=[metadata],
            ids=[evaluation_data["id"]]
        )
        
        return evaluation_data["id"]
    
    def search_similar_cases(
        self, 
        query: str, 
        k: int = 3,
        score_threshold: float = 0.7
    ) -> List[Tuple[Document, float]]:
        """類似する過去の評価事例を検索"""
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=k
        )
        
        # スコアしきい値でフィルタリング
        filtered_results = [
            (doc, score) for doc, score in results 
            if (1 - score) >= score_threshold
        ]
        
        return filtered_results
    
    def _create_searchable_text(self, job_req: Dict, resume: Dict) -> str:
        """検索用のテキストを生成"""
        return f"""
【採用要件】
職種: {job_req.get('title', '')}
会社: {job_req.get('company', '')}
必須スキル: {', '.join(job_req.get('required_skills', []))}
歓迎スキル: {', '.join(job_req.get('preferred_skills', []))}
経験年数: {job_req.get('experience_years', '')}
チーム規模: {job_req.get('team_size', '')}
年収レンジ: {job_req.get('salary_range', '')}
業務内容: {job_req.get('description', '')[:500]}

【候補者情報】
名前: {resume.get('name', '')}
経験年数: {resume.get('experience', '')}
現在の役職: {resume.get('current_position', '')}
スキル: {', '.join(resume.get('skills', []))}
職歴: {resume.get('work_history', '')[:500]}
実績: {resume.get('achievements', '')[:500]}
        """
    
    def _summarize_reasons(self, reasons: List[str]) -> str:
        """理由のリストを要約"""
        if not reasons:
            return ""
        return " / ".join(reasons[:3])  # 最初の3つまで
    
    def get_statistics(self) -> Dict:
        """ベクトルDBの統計情報を取得"""
        total_count = self.collection.count()
        
        # グレード別の集計（簡易版）
        all_data = self.collection.get()
        grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        
        if all_data and "metadatas" in all_data:
            for metadata in all_data["metadatas"]:
                grade = metadata.get("final_grade")
                if grade in grade_counts:
                    grade_counts[grade] += 1
        
        return {
            "total_evaluations": total_count,
            "grade_distribution": grade_counts,
            "last_updated": datetime.now().isoformat()
        }
    
    def reset_database(self):
        """データベースをリセット（開発用）"""
        self.client.delete_collection("recruitment_evaluations")
        self.collection = self.client.create_collection(
            name="recruitment_evaluations",
            metadata={"hnsw:space": "cosine"}
        )
        print("✅ ベクトルデータベースをリセットしました")


# 初期化スクリプト
if __name__ == "__main__":
    # 環境変数の確認
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEYが設定されていません")
        exit(1)
    
    # ベクトルDBの初期化
    db = RecruitmentVectorDB()
    
    # サンプルデータの追加（テスト用）
    sample_evaluation = {
        "id": "eval_sample_001",
        "timestamp": datetime.now().isoformat(),
        "job_requirement": {
            "id": "job_001",
            "title": "バックエンドエンジニア",
            "company": "株式会社サンプル",
            "required_skills": ["Python", "FastAPI", "AWS"],
            "preferred_skills": ["Docker", "Kubernetes"],
            "experience_years": "3年以上",
            "team_size": "5名",
            "salary_range": "600-800万円",
            "description": "ECサイトのバックエンド開発"
        },
        "candidate_resume": {
            "id": "cand_001",
            "name": "テスト候補者",
            "experience": "5年",
            "current_position": "シニアエンジニア",
            "skills": ["Python", "Django", "AWS", "Docker"],
            "work_history": "Web系企業でバックエンド開発に従事",
            "achievements": "マイクロサービス化プロジェクトをリード"
        },
        "ai_evaluation": {
            "score": 85,
            "grade": "A",
            "positive_reasons": [
                "必須スキルを全て満たしている",
                "経験年数が要件を上回る"
            ],
            "concerns": ["FastAPI経験が明記されていない"]
        },
        "human_review": {
            "final_score": 88,
            "final_grade": "A",
            "reviewer": "採用マネージャー",
            "comments": "技術力は申し分なし",
            "decision": "次選考へ進む"
        }
    }
    
    # サンプルデータを追加
    doc_id = db.add_evaluation(sample_evaluation)
    print(f"✅ サンプルデータを追加しました: {doc_id}")
    
    # 統計情報の表示
    stats = db.get_statistics()
    print(f"\n📊 ベクトルDB統計情報:")
    print(f"  - 総評価数: {stats['total_evaluations']}")
    print(f"  - グレード分布: {stats['grade_distribution']}")