"""Human Feedback Loop for RAG System"""

import os
from typing import Dict, List, Optional
from datetime import datetime
import json
from uuid import uuid4

from .vector_db import RecruitmentVectorDB
from .agent import RAGRecruitmentAgent
from ..db.supabase_client import get_supabase_client


class FeedbackLoop:
    """人間のフィードバックを取り込んでRAGシステムを改善"""
    
    def __init__(self, vector_db: RecruitmentVectorDB):
        self.vector_db = vector_db
        self.supabase = get_supabase_client()
    
    def add_human_reviewed_data(self, evaluation_data: Dict) -> str:
        """人間がレビューした評価データをベクトルDBに追加"""
        
        # 必須フィールドの検証
        required_fields = ["job_requirement", "candidate_resume", "ai_evaluation", "human_review"]
        for field in required_fields:
            if field not in evaluation_data:
                raise ValueError(f"必須フィールド '{field}' が見つかりません")
        
        # IDとタイムスタンプの追加
        if "id" not in evaluation_data:
            evaluation_data["id"] = f"eval_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:8]}"
        if "timestamp" not in evaluation_data:
            evaluation_data["timestamp"] = datetime.now().isoformat()
        
        # ベクトルDBに追加
        doc_id = self.vector_db.add_evaluation(evaluation_data)
        
        # Supabaseのai_evaluationsテーブルも更新（feedback_dataカラムに保存）
        if "ai_evaluation_id" in evaluation_data:
            self._update_supabase_evaluation(
                evaluation_data["ai_evaluation_id"],
                evaluation_data["human_review"]
            )
        
        print(f"✅ 評価データ {doc_id} をベクトルDBに追加しました")
        return doc_id
    
    def process_candidate_submission(
        self,
        candidate_id: str,
        job_id: str,
        human_score: int,
        human_grade: str,
        reviewer_comments: str,
        reviewer_name: str
    ) -> Dict:
        """candidate_submissionsからのデータを処理してベクトルDBに追加"""
        
        try:
            # Supabaseから関連データを取得
            candidate_data = self._fetch_candidate_data(candidate_id)
            job_data = self._fetch_job_data(job_id)
            ai_evaluation = self._fetch_ai_evaluation(candidate_id)
            
            if not all([candidate_data, job_data, ai_evaluation]):
                return {
                    "success": False,
                    "error": "必要なデータの取得に失敗しました"
                }
            
            # 評価データの構造化
            evaluation_data = {
                "job_requirement": {
                    "id": job_data["requirement_id"],
                    "title": job_data["title"],
                    "company": job_data["company_name"],
                    "required_skills": job_data.get("required_skills", []),
                    "preferred_skills": job_data.get("preferred_skills", []),
                    "experience_years": job_data.get("experience_years", ""),
                    "team_size": job_data.get("team_size", ""),
                    "salary_range": job_data.get("salary_range", ""),
                    "description": job_data.get("description", "")
                },
                "candidate_resume": {
                    "id": candidate_data["candidate_id"],
                    "name": f"候補者{candidate_data['candidate_id']}",
                    "experience": self._extract_experience(candidate_data.get("candidate_resume", "")),
                    "current_position": candidate_data.get("candidate_company", ""),
                    "skills": self._extract_skills(candidate_data.get("candidate_resume", "")),
                    "work_history": candidate_data.get("candidate_resume", "")[:1000],
                    "achievements": self._extract_achievements(candidate_data.get("candidate_resume", ""))
                },
                "ai_evaluation": {
                    "score": int(ai_evaluation.get("ai_score", 0) * 100),
                    "grade": self._score_to_grade(ai_evaluation.get("ai_score", 0)),
                    "positive_reasons": ai_evaluation.get("match_reasons", []),
                    "concerns": ai_evaluation.get("concerns", [])
                },
                "human_review": {
                    "final_score": human_score,
                    "final_grade": human_grade,
                    "reviewer": reviewer_name,
                    "comments": reviewer_comments,
                    "decision": "選考進行" if human_grade in ["A", "B"] else "要検討"
                },
                "ai_evaluation_id": ai_evaluation.get("id")
            }
            
            # ベクトルDBに追加
            doc_id = self.add_human_reviewed_data(evaluation_data)
            
            return {
                "success": True,
                "doc_id": doc_id,
                "message": "フィードバックデータを正常に追加しました"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fetch_candidate_data(self, candidate_id: str) -> Optional[Dict]:
        """候補者データを取得"""
        response = self.supabase.table("candidates").select("*").eq("id", candidate_id).single().execute()
        return response.data if response.data else None
    
    def _fetch_job_data(self, job_id: str) -> Optional[Dict]:
        """ジョブデータと要件を取得"""
        response = self.supabase.table("jobs").select(
            "*, job_requirements!inner(*, clients!inner(name))"
        ).eq("id", job_id).single().execute()
        
        if response.data:
            job = response.data
            requirement = job.get("job_requirements", {})
            client = requirement.get("clients", {})
            
            return {
                "job_id": job["id"],
                "requirement_id": requirement.get("id"),
                "title": requirement.get("title", ""),
                "company_name": client.get("name", ""),
                "description": requirement.get("description", ""),
                "required_skills": self._parse_skills_from_structured_data(
                    requirement.get("structured_data", {}).get("required_skills", [])
                ),
                "preferred_skills": self._parse_skills_from_structured_data(
                    requirement.get("structured_data", {}).get("preferred_skills", [])
                ),
                "experience_years": requirement.get("structured_data", {}).get("experience_years", ""),
                "team_size": requirement.get("structured_data", {}).get("team_size", ""),
                "salary_range": requirement.get("structured_data", {}).get("salary_range", "")
            }
        return None
    
    def _fetch_ai_evaluation(self, candidate_id: str) -> Optional[Dict]:
        """AI評価データを取得"""
        response = self.supabase.table("ai_evaluations").select("*").eq(
            "candidate_id", candidate_id
        ).order("evaluated_at", desc=True).limit(1).execute()
        
        return response.data[0] if response.data else None
    
    def _update_supabase_evaluation(self, evaluation_id: str, human_review: Dict):
        """SupabaseのAI評価にフィードバックを追加"""
        feedback_data = {
            "human_score": human_review["final_score"],
            "human_grade": human_review["final_grade"],
            "human_comments": human_review["comments"],
            "reviewer": human_review["reviewer"],
            "reviewed_at": datetime.now().isoformat()
        }
        
        self.supabase.table("ai_evaluations").update({
            "feedback_data": feedback_data
        }).eq("id", evaluation_id).execute()
    
    def _extract_experience(self, resume_text: str) -> str:
        """レジュメテキストから経験年数を抽出"""
        import re
        
        patterns = [
            r'(\d+)年',
            r'経験.*?(\d+)',
            r'(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, resume_text)
            if match:
                return f"{match.group(1)}年"
        
        return "不明"
    
    def _extract_skills(self, resume_text: str) -> List[str]:
        """レジュメテキストからスキルを抽出"""
        # 簡易的な実装（実際はより高度な抽出ロジックが必要）
        common_skills = [
            "Python", "Java", "JavaScript", "TypeScript", "React", "Vue", "Angular",
            "Node.js", "Spring", "Django", "FastAPI", "AWS", "GCP", "Azure",
            "Docker", "Kubernetes", "MySQL", "PostgreSQL", "MongoDB", "Redis"
        ]
        
        found_skills = []
        for skill in common_skills:
            if skill.lower() in resume_text.lower():
                found_skills.append(skill)
        
        return found_skills[:10]  # 最大10個まで
    
    def _extract_achievements(self, resume_text: str) -> str:
        """レジュメテキストから実績を抽出"""
        # 実績に関連するキーワードを探す
        achievement_keywords = ["実績", "成果", "達成", "改善", "リード", "主導"]
        
        lines = resume_text.split('\n')
        achievements = []
        
        for line in lines:
            for keyword in achievement_keywords:
                if keyword in line:
                    achievements.append(line.strip())
                    break
        
        return " / ".join(achievements[:3]) if achievements else ""
    
    def _parse_skills_from_structured_data(self, skills: List) -> List[str]:
        """構造化データからスキルリストを解析"""
        if isinstance(skills, list):
            return skills
        elif isinstance(skills, str):
            return [s.strip() for s in skills.split(',')]
        return []
    
    def _score_to_grade(self, score: float) -> str:
        """スコアをグレードに変換"""
        if score >= 0.8:
            return "A"
        elif score >= 0.6:
            return "B"
        elif score >= 0.4:
            return "C"
        else:
            return "D"
    
    def get_learning_statistics(self) -> Dict:
        """学習統計を取得"""
        db_stats = self.vector_db.get_statistics()
        
        # AI評価と人間評価の乖離度を計算
        recent_feedbacks = self._get_recent_feedbacks(limit=100)
        
        score_differences = []
        grade_matches = 0
        
        for fb in recent_feedbacks:
            ai_score = fb.get("ai_evaluation", {}).get("score", 0)
            human_score = fb.get("human_review", {}).get("final_score", 0)
            score_differences.append(abs(ai_score - human_score))
            
            ai_grade = fb.get("ai_evaluation", {}).get("grade", "")
            human_grade = fb.get("human_review", {}).get("final_grade", "")
            if ai_grade == human_grade:
                grade_matches += 1
        
        avg_score_diff = sum(score_differences) / len(score_differences) if score_differences else 0
        grade_match_rate = (grade_matches / len(recent_feedbacks)) * 100 if recent_feedbacks else 0
        
        return {
            **db_stats,
            "feedback_metrics": {
                "total_feedbacks": len(recent_feedbacks),
                "avg_score_difference": round(avg_score_diff, 1),
                "grade_match_rate": round(grade_match_rate, 1),
                "learning_quality": "良好" if grade_match_rate > 70 else "要改善"
            }
        }
    
    def _get_recent_feedbacks(self, limit: int = 100) -> List[Dict]:
        """最近のフィードバックデータを取得"""
        # 実際の実装では、ベクトルDBから最近のデータを取得
        # ここでは簡易実装
        return []


# 統合ヘルパー関数
def create_feedback_from_submission(
    submission_id: str,
    vector_db: RecruitmentVectorDB
) -> Dict:
    """candidate_submissionsのレコードからフィードバックを作成"""
    
    feedback_loop = FeedbackLoop(vector_db)
    supabase = get_supabase_client()
    
    # submissionデータを取得
    submission = supabase.table("candidate_submissions").select(
        "*, candidates!inner(*), jobs!inner(*)"
    ).eq("id", submission_id).single().execute()
    
    if not submission.data:
        return {"success": False, "error": "Submission not found"}
    
    data = submission.data
    
    # フィードバックループに追加
    result = feedback_loop.process_candidate_submission(
        candidate_id=data["candidate_id"],
        job_id=data["job_id"],
        human_score=data.get("final_score", 80),
        human_grade=data.get("final_grade", "B"),
        reviewer_comments=data.get("reviewer_comments", ""),
        reviewer_name=data.get("submitted_by", "Unknown")
    )
    
    return result


if __name__ == "__main__":
    # テスト実行
    db = RecruitmentVectorDB()
    feedback_loop = FeedbackLoop(db)
    
    # 統計情報の表示
    stats = feedback_loop.get_learning_statistics()
    print("📊 学習統計:")
    print(json.dumps(stats, ensure_ascii=False, indent=2))