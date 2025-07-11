"""WebApp Integration for RAG Agent"""

import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from .vector_db import RecruitmentVectorDB
from .agent import RAGRecruitmentAgent
from .feedback_loop import FeedbackLoop
from ..db.supabase_client import get_supabase_client


class RAGIntegration:
    """WebAppとRAGシステムを統合するクラス"""
    
    def __init__(self):
        self.vector_db = RecruitmentVectorDB()
        self.agent = RAGRecruitmentAgent(self.vector_db)
        self.feedback_loop = FeedbackLoop(self.vector_db)
        self.supabase = get_supabase_client()
    
    async def evaluate_candidates_batch(
        self,
        job_id: str,
        candidate_ids: List[str]
    ) -> Dict[str, Dict]:
        """複数の候補者を一括評価"""
        
        # ジョブ情報を取得
        job_info = await self._fetch_job_info(job_id)
        if not job_info:
            return {"error": "Job not found"}
        
        results = {}
        
        for candidate_id in candidate_ids:
            try:
                # 候補者情報を取得
                candidate_info = await self._fetch_candidate_info(candidate_id)
                if not candidate_info:
                    results[candidate_id] = {"error": "Candidate not found"}
                    continue
                
                # RAG評価を実行
                evaluation = self.agent.evaluate_candidate(
                    job_info["requirement"],
                    candidate_info["resume"]
                )
                
                # AI評価をSupabaseに保存
                await self._save_ai_evaluation(
                    candidate_id,
                    job_info["requirement"]["id"],
                    job_id,
                    evaluation
                )
                
                results[candidate_id] = evaluation
                
            except Exception as e:
                results[candidate_id] = {"error": str(e)}
        
        return results
    
    async def process_human_feedback(
        self,
        submission_id: str
    ) -> Dict:
        """candidate_submissionsからフィードバックを処理"""
        
        # submissionデータを取得
        submission = await self._fetch_submission(submission_id)
        if not submission:
            return {"success": False, "error": "Submission not found"}
        
        # フィードバックループで処理
        result = self.feedback_loop.process_candidate_submission(
            candidate_id=submission["candidate_id"],
            job_id=submission["job_id"],
            human_score=submission.get("final_score", 80),
            human_grade=submission.get("final_grade", "B"),
            reviewer_comments=submission.get("reviewer_comments", ""),
            reviewer_name=submission.get("submitted_by", "Unknown")
        )
        
        return result
    
    async def _fetch_job_info(self, job_id: str) -> Optional[Dict]:
        """ジョブ情報と要件を取得"""
        response = self.supabase.table("jobs").select(
            "*, job_requirements!inner(*, clients!inner(name))"
        ).eq("id", job_id).single().execute()
        
        if not response.data:
            return None
        
        job = response.data
        requirement = job.get("job_requirements", {})
        client = requirement.get("clients", {})
        structured = requirement.get("structured_data", {})
        
        return {
            "job_id": job["id"],
            "requirement": {
                "id": requirement.get("id"),
                "title": requirement.get("title", ""),
                "company": client.get("name", ""),
                "required_skills": structured.get("required_skills", []),
                "preferred_skills": structured.get("preferred_skills", []),
                "experience_years": structured.get("experience_years", ""),
                "team_size": structured.get("team_size", ""),
                "salary_range": structured.get("salary_range", ""),
                "description": requirement.get("description", "")
            }
        }
    
    async def _fetch_candidate_info(self, candidate_id: str) -> Optional[Dict]:
        """候補者情報を取得"""
        response = self.supabase.table("candidates").select("*").eq(
            "id", candidate_id
        ).single().execute()
        
        if not response.data:
            return None
        
        candidate = response.data
        
        # レジュメから情報を抽出
        resume_text = candidate.get("candidate_resume", "")
        
        return {
            "candidate_id": candidate["id"],
            "resume": {
                "id": candidate["candidate_id"],
                "name": f"候補者{candidate['candidate_id']}",
                "experience": self._extract_experience(resume_text),
                "current_position": candidate.get("candidate_company", ""),
                "skills": self._extract_skills(resume_text),
                "work_history": resume_text[:1000],
                "achievements": self._extract_achievements(resume_text)
            }
        }
    
    async def _save_ai_evaluation(
        self,
        candidate_id: str,
        requirement_id: str,
        search_id: str,
        evaluation: Dict
    ):
        """AI評価結果をSupabaseに保存"""
        
        evaluation_data = {
            "candidate_id": candidate_id,
            "requirement_id": requirement_id,
            "search_id": search_id,
            "ai_score": evaluation.get("score", 0) / 100.0,
            "match_reasons": evaluation.get("positive_reasons", []),
            "concerns": evaluation.get("concerns", []),
            "recommendation": evaluation.get("recommendation", "medium"),
            "detailed_evaluation": {
                "grade": evaluation.get("grade", "C"),
                "salary_estimate": evaluation.get("salary_estimate"),
                "additional_insights": evaluation.get("additional_insights"),
                "execution_stats": evaluation.get("execution_stats", {})
            },
            "model_version": "gpt-4-rag",
            "prompt_version": "v3.0-rag",
            "evaluated_at": datetime.now().isoformat()
        }
        
        self.supabase.table("ai_evaluations").insert(evaluation_data).execute()
    
    async def _fetch_submission(self, submission_id: str) -> Optional[Dict]:
        """送客データを取得"""
        response = self.supabase.table("candidate_submissions").select(
            "*, candidates!inner(*), jobs!inner(*)"
        ).eq("id", submission_id).single().execute()
        
        return response.data if response.data else None
    
    def _extract_experience(self, resume_text: str) -> str:
        """経験年数を抽出（feedback_loopから流用）"""
        import re
        patterns = [r'(\d+)年', r'経験.*?(\d+)', r'(\d+)\s*years?']
        for pattern in patterns:
            match = re.search(pattern, resume_text)
            if match:
                return f"{match.group(1)}年"
        return "不明"
    
    def _extract_skills(self, resume_text: str) -> List[str]:
        """スキルを抽出（feedback_loopから流用）"""
        common_skills = [
            "Python", "Java", "JavaScript", "TypeScript", "React", "Vue",
            "Node.js", "Spring", "Django", "FastAPI", "AWS", "Docker"
        ]
        found_skills = []
        for skill in common_skills:
            if skill.lower() in resume_text.lower():
                found_skills.append(skill)
        return found_skills[:10]
    
    def _extract_achievements(self, resume_text: str) -> str:
        """実績を抽出（feedback_loopから流用）"""
        achievement_keywords = ["実績", "成果", "達成", "改善", "リード"]
        lines = resume_text.split('\n')
        achievements = []
        for line in lines:
            for keyword in achievement_keywords:
                if keyword in line:
                    achievements.append(line.strip())
                    break
        return " / ".join(achievements[:3]) if achievements else ""


# FastAPI用のエンドポイント例
def create_rag_endpoints(app):
    """FastAPIアプリケーションにRAGエンドポイントを追加"""
    from fastapi import HTTPException
    from pydantic import BaseModel
    
    rag = RAGIntegration()
    
    class BatchEvaluationRequest(BaseModel):
        job_id: str
        candidate_ids: List[str]
    
    class FeedbackRequest(BaseModel):
        submission_id: str
    
    @app.post("/api/rag/evaluate-batch")
    async def evaluate_batch(request: BatchEvaluationRequest):
        """候補者を一括でRAG評価"""
        try:
            results = await rag.evaluate_candidates_batch(
                request.job_id,
                request.candidate_ids
            )
            return {"success": True, "results": results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/rag/process-feedback")
    async def process_feedback(request: FeedbackRequest):
        """人間のフィードバックを処理"""
        try:
            result = await rag.process_human_feedback(request.submission_id)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/rag/statistics")
    async def get_statistics():
        """RAGシステムの統計情報"""
        try:
            stats = rag.feedback_loop.get_learning_statistics()
            return {"success": True, "statistics": stats}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 統合テスト
    async def test_integration():
        rag = RAGIntegration()
        
        # テスト用のジョブIDと候補者ID（実際のデータに合わせて変更）
        test_job_id = "33333333-3333-3333-3333-333333333333"
        test_candidate_ids = [
            "44444444-4444-4444-4444-444444444444",
            "55555555-5555-5555-5555-555555555555"
        ]
        
        print("🚀 RAG評価を実行中...")
        results = await rag.evaluate_candidates_batch(
            test_job_id,
            test_candidate_ids
        )
        
        print("\n📊 評価結果:")
        for candidate_id, result in results.items():
            print(f"\n候補者 {candidate_id}:")
            if "error" in result:
                print(f"  エラー: {result['error']}")
            else:
                print(f"  スコア: {result.get('score', 0)}")
                print(f"  グレード: {result.get('grade', 'N/A')}")
                print(f"  推奨度: {result.get('recommendation', 'N/A')}")
    
    # 非同期実行
    asyncio.run(test_integration())