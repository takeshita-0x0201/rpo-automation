"""
基底クラスとデータ構造の定義
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class NodeState(Enum):
    """ノードの状態"""
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ResearchState:
    """研究プロセス全体の状態"""
    # 入力データ
    resume: str
    job_memo: str
    job_description: Optional[str] = None  # オプショナル（使用しない場合はNone）
    
    # 処理中のデータ
    current_evaluation: Optional['EvaluationResult'] = None
    information_gaps: List['InformationGap'] = field(default_factory=list)
    search_results: Dict[str, 'SearchResult'] = field(default_factory=dict)
    
    # 履歴
    evaluation_history: List['CycleResult'] = field(default_factory=list)
    
    # 制御フラグ
    current_cycle: int = 0
    max_cycles: int = 3
    should_continue: bool = True
    
    # 最終結果
    final_judgment: Optional[Dict] = None
    
    def add_search_result(self, key: str, result: 'SearchResult'):
        """検索結果を追加"""
        self.search_results[key] = result
    
    def complete_cycle(self, cycle_result: 'CycleResult'):
        """サイクルを完了"""
        self.evaluation_history.append(cycle_result)
        self.current_cycle += 1
        
        # 最大サイクル数に達したら終了
        if self.current_cycle >= self.max_cycles:
            self.should_continue = False


@dataclass
class EvaluationResult:
    """評価結果"""
    score: int  # 0-100
    confidence: str  # 低/中/高
    strengths: List[str]
    concerns: List[str]
    summary: str
    interview_points: Optional[List[str]] = None  # 面接確認事項
    raw_response: Optional[str] = None


@dataclass
class InformationGap:
    """情報ギャップ"""
    info_type: str
    description: str
    search_query: str
    importance: str  # 高/中/低
    rationale: str


@dataclass
class SearchResult:
    """検索結果"""
    query: str
    results: List[Dict[str, Any]]
    summary: str
    sources: List[str]
    timestamp: str


@dataclass
class CycleResult:
    """各サイクルの結果"""
    cycle_number: int
    evaluation: EvaluationResult
    gaps: List[InformationGap]
    search_results: Dict[str, SearchResult]
    duration_seconds: float


class BaseNode(ABC):
    """全ノードの基底クラス"""
    
    def __init__(self, name: str):
        self.name = name
        self.state = NodeState.READY
        
    @abstractmethod
    async def process(self, state: ResearchState) -> ResearchState:
        """
        ノードの処理を実行
        
        Args:
            state: 現在の研究状態
            
        Returns:
            更新された研究状態
        """
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', state={self.state})"