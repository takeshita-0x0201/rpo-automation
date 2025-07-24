"""
並列処理最適化ユーティリティ
複数のタスクを効率的に並列実行するための機能を提供
"""

import asyncio
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging


@dataclass
class TaskResult:
    """タスク実行結果"""
    task_id: str
    result: Any
    duration: float
    success: bool
    error: Optional[str] = None


@dataclass
class ParallelExecutionReport:
    """並列実行レポート"""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_duration: float
    parallel_efficiency: float  # 並列化による時間短縮率
    task_results: List[TaskResult]


class ParallelExecutor:
    """並列処理実行器"""
    
    def __init__(self, max_workers: int = 4, executor_type: str = "thread"):
        """
        Args:
            max_workers: 最大ワーカー数
            executor_type: "thread" または "process"
        """
        self.max_workers = max_workers
        self.executor_type = executor_type
        self.logger = logging.getLogger(__name__)
        
    async def execute_parallel_async(self, 
                                   tasks: List[Tuple[str, Callable, Dict]],
                                   timeout: Optional[float] = None) -> ParallelExecutionReport:
        """
        非同期タスクを並列実行
        
        Args:
            tasks: [(task_id, async_function, kwargs), ...]
            timeout: タイムアウト秒数
            
        Returns:
            ParallelExecutionReport
        """
        start_time = time.time()
        task_results = []
        
        # タスクを作成
        async_tasks = []
        for task_id, func, kwargs in tasks:
            task = self._create_async_task(task_id, func, kwargs, timeout)
            async_tasks.append(task)
        
        # 並列実行
        self.logger.info(f"並列実行開始: {len(tasks)}タスク")
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        # 結果を処理
        successful = 0
        failed = 0
        
        for i, (task_id, _, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, TaskResult):
                task_results.append(result)
                if result.success:
                    successful += 1
                else:
                    failed += 1
            else:
                # 例外の場合
                task_results.append(TaskResult(
                    task_id=task_id,
                    result=None,
                    duration=0,
                    success=False,
                    error=str(result)
                ))
                failed += 1
        
        total_duration = time.time() - start_time
        
        # 並列効率を計算（逐次実行との比較）
        sequential_duration = sum(r.duration for r in task_results if r.success)
        parallel_efficiency = sequential_duration / total_duration if total_duration > 0 else 1.0
        
        return ParallelExecutionReport(
            total_tasks=len(tasks),
            successful_tasks=successful,
            failed_tasks=failed,
            total_duration=total_duration,
            parallel_efficiency=parallel_efficiency,
            task_results=task_results
        )
    
    async def _create_async_task(self, 
                               task_id: str,
                               func: Callable,
                               kwargs: Dict,
                               timeout: Optional[float]) -> TaskResult:
        """非同期タスクを作成して実行"""
        start_time = time.time()
        
        try:
            if timeout:
                result = await asyncio.wait_for(func(**kwargs), timeout=timeout)
            else:
                result = await func(**kwargs)
            
            duration = time.time() - start_time
            return TaskResult(
                task_id=task_id,
                result=result,
                duration=duration,
                success=True
            )
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self.logger.warning(f"タスク {task_id} がタイムアウト")
            return TaskResult(
                task_id=task_id,
                result=None,
                duration=duration,
                success=False,
                error=f"Timeout after {timeout} seconds"
            )
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"タスク {task_id} でエラー: {str(e)}")
            return TaskResult(
                task_id=task_id,
                result=None,
                duration=duration,
                success=False,
                error=str(e)
            )
    
    def execute_parallel_sync(self,
                            tasks: List[Tuple[str, Callable, Dict]],
                            timeout: Optional[float] = None) -> ParallelExecutionReport:
        """
        同期タスクを並列実行
        
        Args:
            tasks: [(task_id, function, kwargs), ...]
            timeout: タイムアウト秒数
            
        Returns:
            ParallelExecutionReport
        """
        start_time = time.time()
        task_results = []
        
        # エグゼキューターを選択
        if self.executor_type == "thread":
            executor = ThreadPoolExecutor(max_workers=self.max_workers)
        else:
            executor = ProcessPoolExecutor(max_workers=self.max_workers)
        
        try:
            # タスクを投入
            futures = {}
            for task_id, func, kwargs in tasks:
                future = executor.submit(self._execute_sync_task, task_id, func, kwargs)
                futures[future] = (task_id, time.time())
            
            # 結果を収集
            successful = 0
            failed = 0
            
            for future in asyncio.as_completed(futures, timeout=timeout):
                task_id, task_start = futures[future]
                try:
                    result = future.result()
                    task_results.append(result)
                    if result.success:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    duration = time.time() - task_start
                    task_results.append(TaskResult(
                        task_id=task_id,
                        result=None,
                        duration=duration,
                        success=False,
                        error=str(e)
                    ))
                    failed += 1
        finally:
            executor.shutdown(wait=True)
        
        total_duration = time.time() - start_time
        
        # 並列効率を計算
        sequential_duration = sum(r.duration for r in task_results if r.success)
        parallel_efficiency = sequential_duration / total_duration if total_duration > 0 else 1.0
        
        return ParallelExecutionReport(
            total_tasks=len(tasks),
            successful_tasks=successful,
            failed_tasks=failed,
            total_duration=total_duration,
            parallel_efficiency=parallel_efficiency,
            task_results=task_results
        )
    
    def _execute_sync_task(self, task_id: str, func: Callable, kwargs: Dict) -> TaskResult:
        """同期タスクを実行"""
        start_time = time.time()
        
        try:
            result = func(**kwargs)
            duration = time.time() - start_time
            
            return TaskResult(
                task_id=task_id,
                result=result,
                duration=duration,
                success=True
            )
        except Exception as e:
            duration = time.time() - start_time
            return TaskResult(
                task_id=task_id,
                result=None,
                duration=duration,
                success=False,
                error=str(e)
            )
    
    async def batch_process_with_rate_limit(self,
                                          items: List[Any],
                                          process_func: Callable,
                                          batch_size: int = 10,
                                          delay_between_batches: float = 1.0) -> List[Any]:
        """
        レート制限付きバッチ処理
        
        Args:
            items: 処理対象アイテムリスト
            process_func: 各アイテムを処理する関数
            batch_size: バッチサイズ
            delay_between_batches: バッチ間の遅延（秒）
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # バッチを並列処理
            batch_tasks = [
                (f"item_{i+j}", process_func, {"item": item})
                for j, item in enumerate(batch)
            ]
            
            report = await self.execute_parallel_async(batch_tasks)
            
            # 成功した結果を収集
            for task_result in report.task_results:
                if task_result.success:
                    results.append(task_result.result)
            
            # 次のバッチまで待機（最後のバッチ以外）
            if i + batch_size < len(items):
                await asyncio.sleep(delay_between_batches)
        
        return results
    
    def get_optimal_worker_count(self, task_count: int) -> int:
        """
        タスク数に基づいて最適なワーカー数を決定
        
        Args:
            task_count: タスク数
            
        Returns:
            最適なワーカー数
        """
        # CPU数を考慮
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        
        # タスク数とCPU数から最適値を計算
        if task_count <= 4:
            return min(task_count, self.max_workers)
        elif task_count <= 10:
            return min(4, self.max_workers, cpu_count)
        else:
            return min(self.max_workers, cpu_count)
    
    def format_execution_report(self, report: ParallelExecutionReport) -> str:
        """実行レポートをフォーマット"""
        lines = []
        lines.append("# 並列実行レポート")
        lines.append(f"\n総タスク数: {report.total_tasks}")
        lines.append(f"成功: {report.successful_tasks}")
        lines.append(f"失敗: {report.failed_tasks}")
        lines.append(f"総実行時間: {report.total_duration:.2f}秒")
        lines.append(f"並列効率: {report.parallel_efficiency:.2f}x")
        
        if report.failed_tasks > 0:
            lines.append("\n## 失敗したタスク")
            for result in report.task_results:
                if not result.success:
                    lines.append(f"- {result.task_id}: {result.error}")
        
        lines.append("\n## タスク実行時間")
        sorted_results = sorted(
            [r for r in report.task_results if r.success],
            key=lambda x: x.duration,
            reverse=True
        )
        for result in sorted_results[:5]:  # 上位5件
            lines.append(f"- {result.task_id}: {result.duration:.2f}秒")
        
        return '\n'.join(lines)


class ParallelSearchExecutor:
    """検索タスク専用の並列実行器"""
    
    def __init__(self, max_concurrent_searches: int = 3):
        self.executor = ParallelExecutor(
            max_workers=max_concurrent_searches,
            executor_type="thread"
        )
        self.logger = logging.getLogger(__name__)
    
    async def search_parallel(self,
                            search_queries: Dict[str, str],
                            search_func: Callable,
                            **search_kwargs) -> Dict[str, Any]:
        """
        複数の検索クエリを並列実行
        
        Args:
            search_queries: {search_id: query}
            search_func: 検索関数
            search_kwargs: 検索関数への追加引数
            
        Returns:
            {search_id: search_result}
        """
        # タスクリストを作成
        tasks = [
            (search_id, search_func, {"query": query, **search_kwargs})
            for search_id, query in search_queries.items()
        ]
        
        # 並列実行
        report = await self.executor.execute_parallel_async(tasks, timeout=30)
        
        # 結果をマッピング
        results = {}
        for task_result in report.task_results:
            if task_result.success:
                results[task_result.task_id] = task_result.result
            else:
                self.logger.warning(
                    f"検索失敗 {task_result.task_id}: {task_result.error}"
                )
        
        self.logger.info(
            f"並列検索完了: {report.successful_tasks}/{report.total_tasks}成功, "
            f"効率: {report.parallel_efficiency:.1f}x"
        )
        
        return results