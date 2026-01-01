"""
Process Recycling Utilities for Long-Running TTS Batch Jobs

Post-Coqui Era Fix: CUDA context corruption and memory leaks are common
in long-running XTTS synthesis. Process recycling forces the OS kernel
to reclaim all resources after a task, guaranteeing a clean slate.

Usage:
    from process_recycling import RecyclingProcessPool, should_recycle

    # Option 1: Use the recycling pool directly
    with RecyclingProcessPool(max_workers=2, tasks_per_worker=50) as pool:
        results = pool.map(synthesize_chunk, chunks)

    # Option 2: Check if recycling is needed after each batch
    for batch in batches:
        process_batch(batch)
        if should_recycle(completed_chunks, recycle_interval=100):
            force_gc_and_cache_clear()

Configuration:
    Set ENABLE_PROCESS_RECYCLING=true in environment or config to use
    multiprocessing instead of threading for batch synthesis.
"""

import gc
import logging
import os
from multiprocessing import Pool
from typing import Any, Callable, Iterable, List, Optional

logger = logging.getLogger(__name__)

# Default: recycle every 50 tasks per worker (conservative for stability)
DEFAULT_TASKS_PER_WORKER = 50


def should_recycle(completed_count: int, recycle_interval: int = 100) -> bool:
    """
    Check if it's time to trigger garbage collection and cache clearing.

    Args:
        completed_count: Number of completed chunks/tasks
        recycle_interval: How often to trigger cleanup

    Returns:
        True if cleanup should be triggered
    """
    return completed_count > 0 and completed_count % recycle_interval == 0


def force_gc_and_cache_clear() -> None:
    """
    Force garbage collection and CUDA cache clearing.

    Call this periodically during long batch jobs to prevent memory creep.
    """
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.debug("CUDA cache cleared via process recycling")
    except ImportError:
        pass


class RecyclingProcessPool:
    """
    Process pool that recycles workers after a fixed number of tasks.

    This prevents CUDA context corruption and memory leaks in long-running
    batch synthesis jobs. Each worker process terminates and restarts after
    completing `tasks_per_worker` tasks.

    Example:
        with RecyclingProcessPool(max_workers=2, tasks_per_worker=50) as pool:
            results = pool.map(synthesize_chunk, chunks)
    """

    def __init__(
        self,
        max_workers: int = 1,
        tasks_per_worker: int = DEFAULT_TASKS_PER_WORKER,
    ):
        """
        Initialize the recycling process pool.

        Args:
            max_workers: Maximum number of worker processes
            tasks_per_worker: Recycle each worker after this many tasks
        """
        self.max_workers = max_workers
        self.tasks_per_worker = tasks_per_worker
        self._pool: Optional[Pool] = None

    def __enter__(self) -> "RecyclingProcessPool":
        """Context manager entry - create the pool."""
        self._pool = Pool(
            processes=self.max_workers,
            maxtasksperchild=self.tasks_per_worker,
        )
        logger.info(
            f"RecyclingProcessPool started: {self.max_workers} workers, "
            f"recycling every {self.tasks_per_worker} tasks"
        )
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit - cleanup the pool."""
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None
            force_gc_and_cache_clear()
            logger.debug("RecyclingProcessPool terminated and cleaned up")

    def map(
        self,
        func: Callable,
        iterable: Iterable,
        chunksize: int = 1,
    ) -> List[Any]:
        """
        Map function over iterable with process recycling.

        Args:
            func: Function to apply to each item
            iterable: Items to process
            chunksize: Chunk size for multiprocessing.Pool.map

        Returns:
            List of results
        """
        if self._pool is None:
            raise RuntimeError("Pool not initialized - use context manager")
        return self._pool.map(func, iterable, chunksize=chunksize)

    def imap_unordered(
        self,
        func: Callable,
        iterable: Iterable,
        chunksize: int = 1,
    ):
        """
        Lazy map with unordered results (memory efficient for large batches).

        Args:
            func: Function to apply to each item
            iterable: Items to process
            chunksize: Chunk size for multiprocessing.Pool.imap_unordered

        Yields:
            Results as they complete (unordered)
        """
        if self._pool is None:
            raise RuntimeError("Pool not initialized - use context manager")
        yield from self._pool.imap_unordered(func, iterable, chunksize=chunksize)


def is_process_recycling_enabled() -> bool:
    """
    Check if process recycling is enabled via environment variable.

    Set ENABLE_PROCESS_RECYCLING=true to enable.
    """
    env_val = os.getenv("ENABLE_PROCESS_RECYCLING", "").lower()
    return env_val in ("true", "1", "yes")


def get_recycle_interval() -> int:
    """
    Get the recycling interval from environment.

    Set PROCESS_RECYCLE_INTERVAL=N to recycle every N tasks.
    Default: 50
    """
    try:
        return int(os.getenv("PROCESS_RECYCLE_INTERVAL", str(DEFAULT_TASKS_PER_WORKER)))
    except ValueError:
        return DEFAULT_TASKS_PER_WORKER
