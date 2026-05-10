"""
并行任务执行模块
来源: Hermes Agent batch_runner.py
功能: 支持多任务并行执行、结果汇总
"""

import asyncio
import concurrent.futures
from typing import List, Callable, Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import traceback

@dataclass
class TaskResult:
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0

class ParallelTaskRunner:
    """并行任务执行器"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.results: List[TaskResult] = []
    
    def execute(self, tasks: List[Dict[str, Any]]) -> List[TaskResult]:
        """
        执行并行任务
        
        tasks格式: [
            {"id": "task1", "func": func, "args": (), "kwargs": {}},
            ...
        ]
        """
        start_time = datetime.now()
        self.results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {}
            
            for task in tasks:
                task_id = task.get("id", f"task_{len(future_to_task)}")
                func = task.get("func")
                args = task.get("args", ())
                kwargs = task.get("kwargs", {})
                
                future = executor.submit(self._run_task, task_id, func, args, kwargs)
                future_to_task[future] = task_id
            
            for future in concurrent.futures.as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    self.results.append(TaskResult(
                        task_id=task_id,
                        success=False,
                        error=str(e)
                    ))
        
        duration = (datetime.now() - start_time).total_seconds()
        return self.results
    
    def _run_task(self, task_id: str, func: Callable, args: tuple, kwargs: dict) -> TaskResult:
        """执行单个任务"""
        import time
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return TaskResult(
                task_id=task_id,
                success=True,
                result=result,
                duration=time.time() - start
            )
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                success=False,
                error=str(e),
                duration=time.time() - start
            )
    
    def summary(self) -> Dict[str, Any]:
        """生成执行摘要"""
        total = len(self.results)
        success = sum(1 for r in self.results if r.success)
        failed = total - success
        total_duration = sum(r.duration for r in self.results)
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "total_duration": total_duration,
            "avg_duration": total_duration / total if total else 0
        }


# 使用示例
if __name__ == "__main__":
    import time
    
    def sample_task(name: str, delay: float) -> str:
        time.sleep(delay)
        return f"Task {name} completed"
    
    runner = ParallelTaskRunner(max_workers=3)
    tasks = [
        {"id": "A", "func": sample_task, "args": ("A", 0.5)},
        {"id": "B", "func": sample_task, "args": ("B", 1.0)},
        {"id": "C", "func": sample_task, "args": ("C", 0.3)},
    ]
    
    results = runner.execute(tasks)
    summary = runner.summary()
    
    print(f"执行完成: {summary}")
    for r in results:
        status = "✅" if r.success else "❌"
        print(f"  {status} {r.task_id}: {r.result or r.error}")
