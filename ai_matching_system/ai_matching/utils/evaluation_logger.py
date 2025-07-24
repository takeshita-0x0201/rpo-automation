"""
評価理由ロガー
評価プロセスの透明性を確保し、改善のためのデータを収集
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import sqlite3
from contextlib import contextmanager


class EvaluationLogger:
    """評価プロセスと結果を記録するロガー"""
    
    def __init__(self, log_dir: str = "evaluation_logs", use_db: bool = True):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.use_db = use_db
        
        if self.use_db:
            self.db_path = self.log_dir / "evaluation_history.db"
            self._init_database()
    
    def _init_database(self):
        """評価履歴データベースを初期化"""
        with self._get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    evaluation_cycle INTEGER,
                    approach TEXT,
                    score INTEGER,
                    confidence TEXT,
                    information_confidence REAL,
                    decision_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evaluation_id INTEGER,
                    decision_type TEXT,
                    decision_key TEXT,
                    decision_value TEXT,
                    confidence REAL,
                    reasoning TEXT,
                    FOREIGN KEY (evaluation_id) REFERENCES evaluation_logs (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evaluation_id INTEGER,
                    detection_type TEXT,
                    detected_text TEXT,
                    confidence REAL,
                    evidence TEXT,
                    FOREIGN KEY (evaluation_id) REFERENCES evaluation_logs (id)
                )
            """)
            
            # インデックス作成
            conn.execute("CREATE INDEX IF NOT EXISTS idx_candidate_job ON evaluation_logs(candidate_id, job_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON evaluation_logs(timestamp)")
    
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
    
    def log_evaluation(self, 
                      candidate_id: str,
                      job_id: str,
                      evaluation_data: Dict[str, Any],
                      decisions: List[Dict[str, Any]] = None,
                      detections: List[Dict[str, Any]] = None) -> int:
        """
        評価を記録
        
        Args:
            candidate_id: 候補者ID
            job_id: 求人ID
            evaluation_data: 評価データ
            decisions: 評価決定の詳細
            detections: セマンティック検出の詳細
            
        Returns:
            ログID
        """
        timestamp = datetime.now().isoformat()
        
        # JSONファイルに保存
        if os.getenv('SAVE_EVALUATION_JSON', 'true').lower() == 'true':
            json_file = self.log_dir / f"{candidate_id}_{timestamp.replace(':', '-')}.json"
            full_data = {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "timestamp": timestamp,
                "evaluation": evaluation_data,
                "decisions": decisions or [],
                "detections": detections or []
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, ensure_ascii=False, indent=2)
        
        # データベースに保存
        if self.use_db:
            with self._get_db() as conn:
                cursor = conn.execute("""
                    INSERT INTO evaluation_logs 
                    (timestamp, candidate_id, job_id, evaluation_cycle, approach, 
                     score, confidence, information_confidence, decision_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    candidate_id,
                    job_id,
                    evaluation_data.get('cycle', 1),
                    evaluation_data.get('approach', 'unknown'),
                    evaluation_data.get('score', 0),
                    evaluation_data.get('confidence', 'low'),
                    evaluation_data.get('information_confidence', 0.0),
                    json.dumps(evaluation_data, ensure_ascii=False)
                ))
                
                evaluation_id = cursor.lastrowid
                
                # 決定事項を記録
                if decisions:
                    for decision in decisions:
                        conn.execute("""
                            INSERT INTO evaluation_decisions
                            (evaluation_id, decision_type, decision_key, 
                             decision_value, confidence, reasoning)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            evaluation_id,
                            decision.get('type', ''),
                            decision.get('key', ''),
                            decision.get('value', ''),
                            decision.get('confidence', 0.0),
                            decision.get('reasoning', '')
                        ))
                
                # セマンティック検出を記録
                if detections:
                    for detection in detections:
                        conn.execute("""
                            INSERT INTO semantic_detections
                            (evaluation_id, detection_type, detected_text,
                             confidence, evidence)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            evaluation_id,
                            detection.get('type', ''),
                            detection.get('text', ''),
                            detection.get('confidence', 0.0),
                            json.dumps(detection.get('evidence', []))
                        ))
                
                return evaluation_id
        
        return 0
    
    def get_evaluation_history(self, candidate_id: str, job_id: str) -> List[Dict]:
        """特定の候補者と求人の評価履歴を取得"""
        if not self.use_db:
            return []
        
        with self._get_db() as conn:
            cursor = conn.execute("""
                SELECT * FROM evaluation_logs
                WHERE candidate_id = ? AND job_id = ?
                ORDER BY timestamp DESC
            """, (candidate_id, job_id))
            
            results = []
            for row in cursor:
                eval_dict = dict(row)
                eval_dict['decision_data'] = json.loads(eval_dict['decision_data'])
                
                # 関連する決定事項を取得
                decisions = conn.execute("""
                    SELECT * FROM evaluation_decisions
                    WHERE evaluation_id = ?
                """, (row['id'],)).fetchall()
                
                eval_dict['decisions'] = [dict(d) for d in decisions]
                
                # 関連するセマンティック検出を取得
                detections = conn.execute("""
                    SELECT * FROM semantic_detections
                    WHERE evaluation_id = ?
                """, (row['id'],)).fetchall()
                
                eval_dict['detections'] = [
                    {**dict(d), 'evidence': json.loads(d['evidence'])}
                    for d in detections
                ]
                
                results.append(eval_dict)
            
            return results
    
    def analyze_evaluation_patterns(self, limit: int = 100) -> Dict[str, Any]:
        """評価パターンを分析"""
        if not self.use_db:
            return {}
        
        with self._get_db() as conn:
            # アプローチ別の統計
            approach_stats = conn.execute("""
                SELECT approach, 
                       COUNT(*) as count,
                       AVG(score) as avg_score,
                       AVG(information_confidence) as avg_confidence
                FROM evaluation_logs
                GROUP BY approach
                ORDER BY count DESC
            """).fetchall()
            
            # セマンティック検出の成功率
            detection_stats = conn.execute("""
                SELECT detection_type,
                       COUNT(*) as count,
                       AVG(confidence) as avg_confidence
                FROM semantic_detections
                GROUP BY detection_type
                ORDER BY count DESC
            """).fetchall()
            
            # 決定タイプ別の統計
            decision_stats = conn.execute("""
                SELECT decision_type,
                       COUNT(*) as count,
                       AVG(confidence) as avg_confidence
                FROM evaluation_decisions
                GROUP BY decision_type
                ORDER BY count DESC
            """).fetchall()
            
            return {
                "approach_statistics": [dict(row) for row in approach_stats],
                "semantic_detection_stats": [dict(row) for row in detection_stats],
                "decision_type_stats": [dict(row) for row in decision_stats],
                "total_evaluations": conn.execute("SELECT COUNT(*) FROM evaluation_logs").fetchone()[0]
            }
    
    def export_for_analysis(self, output_file: str = "evaluation_analysis.json"):
        """分析用にデータをエクスポート"""
        if not self.use_db:
            return
        
        with self._get_db() as conn:
            # 全評価ログを取得
            evaluations = conn.execute("""
                SELECT * FROM evaluation_logs
                ORDER BY timestamp DESC
                LIMIT 1000
            """).fetchall()
            
            export_data = []
            for eval_row in evaluations:
                eval_data = dict(eval_row)
                eval_data['decision_data'] = json.loads(eval_data['decision_data'])
                
                # 関連データも含める
                eval_data['decisions'] = [
                    dict(d) for d in conn.execute(
                        "SELECT * FROM evaluation_decisions WHERE evaluation_id = ?",
                        (eval_row['id'],)
                    ).fetchall()
                ]
                
                eval_data['detections'] = [
                    {**dict(d), 'evidence': json.loads(d['evidence'])}
                    for d in conn.execute(
                        "SELECT * FROM semantic_detections WHERE evaluation_id = ?",
                        (eval_row['id'],)
                    ).fetchall()
                ]
                
                export_data.append(eval_data)
            
            # 統計情報も含める
            analysis = self.analyze_evaluation_patterns()
            
            full_export = {
                "export_timestamp": datetime.now().isoformat(),
                "evaluations": export_data,
                "statistics": analysis
            }
            
            output_path = self.log_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(full_export, f, ensure_ascii=False, indent=2)
            
            print(f"データをエクスポート: {output_path}")


# グローバルロガーインスタンス
_logger_instance = None

def get_evaluation_logger() -> EvaluationLogger:
    """シングルトンロガーインスタンスを取得"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = EvaluationLogger()
    return _logger_instance