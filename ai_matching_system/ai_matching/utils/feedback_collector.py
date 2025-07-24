"""
フィードバック収集システム
クライアントや内部ユーザーからの評価フィードバックを収集・分析
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager
from enum import Enum


class FeedbackType(Enum):
    """フィードバックタイプ"""
    CLIENT_EVALUATION = "client_evaluation"  # クライアント評価
    RECRUITER_REVIEW = "recruiter_review"    # リクルーター評価
    SYSTEM_CORRECTION = "system_correction"  # システム評価の修正
    INTERVIEW_RESULT = "interview_result"    # 面接結果


class FeedbackSentiment(Enum):
    """フィードバックの感情"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class FeedbackCollector:
    """フィードバックを収集・管理するシステム"""
    
    def __init__(self, db_path: str = "evaluation_logs/feedback.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """フィードバックデータベースを初期化"""
        with self._get_db() as conn:
            # フィードバックテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    sentiment TEXT,
                    original_score INTEGER,
                    suggested_score INTEGER,
                    feedback_text TEXT,
                    tags TEXT,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 評価修正履歴テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS score_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feedback_id INTEGER,
                    original_evaluation_id INTEGER,
                    reason_category TEXT,
                    correction_details TEXT,
                    impact_analysis TEXT,
                    FOREIGN KEY (feedback_id) REFERENCES feedback(id)
                )
            """)
            
            # 学習データテーブル（将来の改善用）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_description TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    suggested_action TEXT
                )
            """)
            
            # タグマスターテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag_name TEXT UNIQUE NOT NULL,
                    tag_category TEXT,
                    usage_count INTEGER DEFAULT 0
                )
            """)
            
            # デフォルトタグを挿入
            default_tags = [
                ("営業経験の見落とし", "evaluation_error"),
                ("過大評価", "evaluation_error"),
                ("過小評価", "evaluation_error"),
                ("文脈理解不足", "evaluation_error"),
                ("優秀な候補者", "positive_feedback"),
                ("期待以上", "positive_feedback"),
                ("ミスマッチ", "negative_feedback"),
                ("スキル不足", "negative_feedback")
            ]
            
            for tag_name, tag_category in default_tags:
                conn.execute("""
                    INSERT OR IGNORE INTO feedback_tags (tag_name, tag_category)
                    VALUES (?, ?)
                """, (tag_name, tag_category))
            
            # インデックス
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_candidate_job ON feedback(candidate_id, job_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type)")
    
    @contextmanager
    def _get_db(self):
        """データベース接続のコンテキストマネージャー"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def collect_feedback(self,
                        candidate_id: str,
                        job_id: str,
                        feedback_type: FeedbackType,
                        feedback_text: str,
                        original_score: int,
                        suggested_score: Optional[int] = None,
                        tags: Optional[List[str]] = None,
                        user_id: Optional[str] = None) -> int:
        """
        フィードバックを収集
        
        Args:
            candidate_id: 候補者ID
            job_id: ジョブID
            feedback_type: フィードバックタイプ
            feedback_text: フィードバックテキスト
            original_score: 元のスコア
            suggested_score: 提案スコア
            tags: タグリスト
            user_id: ユーザーID
        
        Returns:
            フィードバックID
        """
        # センチメント分析（簡易版）
        sentiment = self._analyze_sentiment(feedback_text, original_score, suggested_score)
        
        with self._get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO feedback
                (candidate_id, job_id, feedback_type, sentiment, original_score,
                 suggested_score, feedback_text, tags, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate_id,
                job_id,
                feedback_type.value,
                sentiment.value,
                original_score,
                suggested_score,
                feedback_text,
                json.dumps(tags or []),
                user_id
            ))
            
            feedback_id = cursor.lastrowid
            
            # タグの使用回数を更新
            if tags:
                for tag in tags:
                    conn.execute("""
                        UPDATE feedback_tags 
                        SET usage_count = usage_count + 1
                        WHERE tag_name = ?
                    """, (tag,))
            
            # パターン学習（重要なフィードバックの場合）
            if suggested_score and abs(original_score - suggested_score) > 20:
                self._learn_from_feedback(conn, feedback_id, feedback_text, tags)
            
            return feedback_id
    
    def _analyze_sentiment(self, text: str, original_score: int, 
                          suggested_score: Optional[int]) -> FeedbackSentiment:
        """フィードバックのセンチメントを分析"""
        # スコア差による判定
        if suggested_score:
            score_diff = suggested_score - original_score
            if score_diff > 10:
                return FeedbackSentiment.POSITIVE
            elif score_diff < -10:
                return FeedbackSentiment.NEGATIVE
        
        # テキストによる簡易判定
        positive_words = ["良い", "優秀", "期待", "素晴らしい", "マッチ"]
        negative_words = ["悪い", "不足", "懸念", "ミスマッチ", "違う"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return FeedbackSentiment.POSITIVE
        elif negative_count > positive_count:
            return FeedbackSentiment.NEGATIVE
        
        return FeedbackSentiment.NEUTRAL
    
    def _learn_from_feedback(self, conn: sqlite3.Connection, feedback_id: int,
                           feedback_text: str, tags: Optional[List[str]]):
        """フィードバックからパターンを学習"""
        # 営業経験の見落としパターン
        if tags and "営業経験の見落とし" in tags:
            pattern_type = "sales_experience_miss"
            pattern_desc = "営業経験の認識ミス"
            suggested_action = "セマンティック理解の強化"
            
            # パターンの頻度を更新
            cursor = conn.execute("""
                SELECT id, frequency FROM learning_data
                WHERE pattern_type = ?
            """, (pattern_type,))
            
            row = cursor.fetchone()
            if row:
                conn.execute("""
                    UPDATE learning_data
                    SET frequency = frequency + 1, last_seen = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), row['id']))
            else:
                conn.execute("""
                    INSERT INTO learning_data
                    (pattern_type, pattern_description, suggested_action)
                    VALUES (?, ?, ?)
                """, (pattern_type, pattern_desc, suggested_action))
    
    def add_score_correction(self, feedback_id: int, original_evaluation_id: int,
                           reason_category: str, correction_details: str,
                           impact_analysis: Optional[str] = None):
        """スコア修正の詳細を追加"""
        with self._get_db() as conn:
            conn.execute("""
                INSERT INTO score_corrections
                (feedback_id, original_evaluation_id, reason_category,
                 correction_details, impact_analysis)
                VALUES (?, ?, ?, ?, ?)
            """, (
                feedback_id,
                original_evaluation_id,
                reason_category,
                correction_details,
                impact_analysis
            ))
    
    def get_feedback_summary(self, days: int = 30) -> Dict[str, Any]:
        """フィードバックのサマリーを取得"""
        since_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        with self._get_db() as conn:
            # 全体統計
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(suggested_score - original_score) as avg_score_diff,
                    COUNT(DISTINCT candidate_id) as unique_candidates,
                    COUNT(DISTINCT job_id) as unique_jobs
                FROM feedback
                WHERE datetime(created_at) > datetime(?, 'unixepoch')
            """, (since_date,))
            
            overall_stats = dict(cursor.fetchone())
            
            # センチメント分布
            cursor = conn.execute("""
                SELECT sentiment, COUNT(*) as count
                FROM feedback
                WHERE datetime(created_at) > datetime(?, 'unixepoch')
                GROUP BY sentiment
            """, (since_date,))
            
            sentiment_dist = {row['sentiment']: row['count'] for row in cursor}
            
            # よく使われるタグ
            cursor = conn.execute("""
                SELECT tag_name, usage_count
                FROM feedback_tags
                ORDER BY usage_count DESC
                LIMIT 10
            """)
            
            top_tags = [dict(row) for row in cursor]
            
            # 学習パターン
            cursor = conn.execute("""
                SELECT pattern_type, pattern_description, frequency, suggested_action
                FROM learning_data
                WHERE frequency > 3
                ORDER BY frequency DESC
            """)
            
            patterns = [dict(row) for row in cursor]
            
            return {
                "overall_statistics": overall_stats,
                "sentiment_distribution": sentiment_dist,
                "top_tags": top_tags,
                "recurring_patterns": patterns
            }
    
    def get_candidate_feedback(self, candidate_id: str, job_id: str) -> List[Dict]:
        """特定の候補者のフィードバックを取得"""
        with self._get_db() as conn:
            cursor = conn.execute("""
                SELECT * FROM feedback
                WHERE candidate_id = ? AND job_id = ?
                ORDER BY created_at DESC
            """, (candidate_id, job_id))
            
            feedback_list = []
            for row in cursor:
                feedback_dict = dict(row)
                feedback_dict['tags'] = json.loads(feedback_dict['tags'])
                feedback_list.append(feedback_dict)
            
            return feedback_list
    
    def export_improvement_insights(self) -> Dict[str, Any]:
        """改善のための洞察をエクスポート"""
        insights = {
            "timestamp": datetime.now().isoformat(),
            "score_correction_patterns": [],
            "common_mistakes": [],
            "improvement_recommendations": []
        }
        
        with self._get_db() as conn:
            # スコア修正パターン
            cursor = conn.execute("""
                SELECT 
                    sc.reason_category,
                    COUNT(*) as frequency,
                    AVG(f.suggested_score - f.original_score) as avg_correction
                FROM score_corrections sc
                JOIN feedback f ON sc.feedback_id = f.id
                GROUP BY sc.reason_category
                ORDER BY frequency DESC
            """)
            
            insights["score_correction_patterns"] = [dict(row) for row in cursor]
            
            # よくある間違い
            cursor = conn.execute("""
                SELECT 
                    tags,
                    COUNT(*) as frequency,
                    AVG(ABS(suggested_score - original_score)) as avg_error
                FROM feedback
                WHERE suggested_score IS NOT NULL
                GROUP BY tags
                HAVING frequency > 2
                ORDER BY avg_error DESC
            """)
            
            for row in cursor:
                tags = json.loads(row['tags'])
                if tags:
                    insights["common_mistakes"].append({
                        "tags": tags,
                        "frequency": row['frequency'],
                        "avg_error": row['avg_error']
                    })
            
            # 改善推奨事項
            cursor = conn.execute("""
                SELECT DISTINCT suggested_action
                FROM learning_data
                WHERE frequency > 5
            """)
            
            insights["improvement_recommendations"] = [
                row['suggested_action'] for row in cursor
            ]
        
        return insights


# グローバルインスタンス
_feedback_collector_instance = None

def get_feedback_collector() -> FeedbackCollector:
    """シングルトンインスタンスを取得"""
    global _feedback_collector_instance
    if _feedback_collector_instance is None:
        _feedback_collector_instance = FeedbackCollector()
    return _feedback_collector_instance