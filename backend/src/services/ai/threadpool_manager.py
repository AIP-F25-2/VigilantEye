"""ThreadPool manager for parallel AI processing."""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List
from functools import partial

from src.config.ai_config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class AIThreadPoolManager:
    """Manage thread pool for AI processing tasks."""

    def __init__(self, max_workers: int = None):
        """
        Initialize thread pool manager.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers or ai_config.ai_max_workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        logger.info(f"AI ThreadPool initialized with {self.max_workers} workers")

    def submit_task(self, func: Callable, *args, **kwargs) -> Any:
        """
        Submit a single task to the thread pool.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Future object
        """
        return self.executor.submit(func, *args, **kwargs)

    def submit_batch(self, func: Callable, items: List[Any], **kwargs) -> List[Any]:
        """
        Submit batch of tasks and wait for all to complete.
        
        Args:
            func: Function to execute for each item
            items: List of items to process
            **kwargs: Additional keyword arguments for function
            
        Returns:
            List of results in same order as input
        """
        logger.info(f"Submitting batch of {len(items)} tasks")
        
        # Create futures for all items
        futures = []
        for item in items:
            future = self.executor.submit(func, item, **kwargs)
            futures.append((item, future))
        
        # Collect results in order
        results = []
        for item, future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Task failed for item {item}: {e}")
                results.append(None)
        
        logger.info(f"Batch completed: {len(results)} results")
        return results

    async def submit_batch_async(
        self,
        func: Callable,
        items: List[Any],
        **kwargs
    ) -> List[Any]:
        """
        Submit batch of tasks asynchronously.
        
        Args:
            func: Function to execute for each item
            items: List of items to process
            **kwargs: Additional keyword arguments
            
        Returns:
            List of results
        """
        loop = asyncio.get_event_loop()
        
        # Run batch processing in thread pool
        result = await loop.run_in_executor(
            None,
            partial(self.submit_batch, func, items, **kwargs)
        )
        
        return result

    def parallel_process(
        self,
        tasks: List[Dict[str, Any]],
        max_concurrent: int = None
    ) -> List[Any]:
        """
        Process multiple different tasks in parallel.
        
        Args:
            tasks: List of task dictionaries with 'func' and 'args'
            max_concurrent: Maximum concurrent tasks
            
        Returns:
            List of results
            
        Example:
            tasks = [
                {'func': audio_classify, 'args': (audio_file,)},
                {'func': speech_to_text, 'args': (audio_file,)},
                {'func': detect_faces, 'args': (image_file,)},
            ]
        """
        max_concurrent = max_concurrent or self.max_workers
        
        logger.info(f"Processing {len(tasks)} parallel tasks")
        
        futures = {}
        for i, task in enumerate(tasks):
            func = task['func']
            args = task.get('args', ())
            kwargs = task.get('kwargs', {})
            
            future = self.executor.submit(func, *args, **kwargs)
            futures[future] = {'index': i, 'task': task}
        
        # Collect results
        results = [None] * len(tasks)
        
        for future in as_completed(futures):
            task_info = futures[future]
            index = task_info['index']
            
            try:
                result = future.result()
                results[index] = result
                logger.debug(f"Task {index} completed successfully")
            except Exception as e:
                logger.error(f"Task {index} failed: {e}", exc_info=True)
                results[index] = {'error': str(e)}
        
        logger.info(f"All {len(tasks)} tasks completed")
        return results

    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.
        
        Args:
            wait: Whether to wait for tasks to complete
        """
        logger.info("Shutting down AI ThreadPool")
        self.executor.shutdown(wait=wait)


# Global thread pool instance
_thread_pool = None


def get_ai_threadpool() -> AIThreadPoolManager:
    """Get or create global AI thread pool."""
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = AIThreadPoolManager()
    return _thread_pool


def shutdown_ai_threadpool():
    """Shutdown global AI thread pool."""
    global _thread_pool
    if _thread_pool is not None:
        _thread_pool.shutdown()
        _thread_pool = None
