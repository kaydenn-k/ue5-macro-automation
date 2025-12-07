"""
Task Executor for UE5 Macro Automation.

Provides synchronous and asynchronous task execution with support for
Unreal Engine's threading model, progress tracking, and cancellation.

Example Usage:
    >>> executor = TaskExecutor()
    >>> result = executor.execute(my_task_func, arg1, arg2, timeout=30.0)

    >>> async_executor = AsyncTaskExecutor()
    >>> future = async_executor.submit(my_task_func, arg1, arg2)
    >>> result = await future
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    TIMEOUT = auto()


@dataclass
class TaskResult(Generic[T]):
    """
    Result of a task execution.

    Attributes:
        status: The final status of the task
        data: The return value of the task (if successful)
        error: Error message (if failed)
        execution_time: Time taken to execute in seconds
        retries: Number of retry attempts made
    """
    status: TaskStatus
    data: T | None = None
    error: str | None = None
    execution_time: float = 0.0
    retries: int = 0

    @property
    def success(self) -> bool:
        """Check if the task completed successfully."""
        return self.status == TaskStatus.COMPLETED


@dataclass
class TaskConfig:
    """
    Configuration for task execution.

    Attributes:
        timeout: Maximum execution time in seconds
        retries: Number of retry attempts on failure
        retry_delay: Delay between retries in seconds
        run_on_game_thread: Whether to run on Unreal's game thread
        progress_callback: Callback for progress updates
    """
    timeout: float | None = None
    retries: int = 0
    retry_delay: float = 1.0
    run_on_game_thread: bool = True
    progress_callback: Callable[[float, str], None] | None = None


class TaskExecutor:
    """
    Synchronous task executor with Unreal Engine threading support.

    This executor ensures tasks are run safely within Unreal's threading model,
    using EditorLevelLibrary for editor operations.

    Example:
        >>> executor = TaskExecutor()
        >>>
        >>> def import_asset(path: str) -> bool:
        ...     # Import logic here
        ...     return True
        >>>
        >>> result = executor.execute(
        ...     import_asset,
        ...     "/path/to/asset.fbx",
        ...     config=TaskConfig(timeout=60.0, retries=2)
        ... )
        >>>
        >>> if result.success:
        ...     print("Asset imported successfully")
    """

    def __init__(self) -> None:
        """Initialize the task executor."""
        self._lock = threading.Lock()
        self._current_task: str | None = None
        self._should_cancel = False
        self._unreal_available = self._check_unreal_available()

    def _check_unreal_available(self) -> bool:
        """Check if Unreal Python API is available."""
        try:
            import unreal  # noqa: F401
            return True
        except ImportError:
            logger.warning("Unreal Python API not available - running in standalone mode")
            return False

    def _run_on_game_thread(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function on Unreal's game thread.

        Args:
            func: The function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The function's return value
        """
        if not self._unreal_available:
            return func(*args, **kwargs)

        try:
            import unreal  # noqa: F401

            result_container: list[Any] = [None]
            error_container: list[Exception | None] = [None]
            completed = threading.Event()

            def game_thread_wrapper() -> None:
                try:
                    result_container[0] = func(*args, **kwargs)
                except Exception as e:
                    error_container[0] = e
                finally:
                    completed.set()

            unreal.EditorLevelLibrary.editor_set_game_view(False)

            if threading.current_thread() is threading.main_thread():
                return func(*args, **kwargs)
            else:
                game_thread_wrapper()

            completed.wait()

            if error_container[0]:
                raise error_container[0]

            return result_container[0]

        except ImportError:
            return func(*args, **kwargs)

    def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        config: TaskConfig | None = None,
        **kwargs: Any
    ) -> TaskResult[T]:
        """
        Execute a task synchronously.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            config: Task configuration
            **kwargs: Keyword arguments for the function

        Returns:
            TaskResult containing the execution result

        Example:
            >>> def process_mesh(path: str, optimize: bool = True) -> dict:
            ...     return {"processed": True, "path": path}
            >>>
            >>> result = executor.execute(
            ...     process_mesh,
            ...     "/Game/Meshes/Tree.uasset",
            ...     optimize=True,
            ...     config=TaskConfig(timeout=30.0)
            ... )
        """
        config = config or TaskConfig()
        start_time = time.time()
        attempts = 0
        max_attempts = config.retries + 1
        last_error: str | None = None

        with self._lock:
            self._current_task = func.__name__
            self._should_cancel = False

        try:
            while attempts < max_attempts:
                if self._should_cancel:
                    return TaskResult(
                        status=TaskStatus.CANCELLED,
                        error="Task was cancelled",
                        execution_time=time.time() - start_time,
                        retries=attempts
                    )

                try:
                    logger.debug(f"Executing task: {func.__name__} (attempt {attempts + 1})")

                    if config.run_on_game_thread:
                        result_data = self._run_on_game_thread(func, *args, **kwargs)
                    else:
                        if config.timeout:
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                                future = pool.submit(func, *args, **kwargs)
                                result_data = future.result(timeout=config.timeout)
                        else:
                            result_data = func(*args, **kwargs)

                    execution_time = time.time() - start_time

                    return TaskResult(
                        status=TaskStatus.COMPLETED,
                        data=result_data,
                        execution_time=execution_time,
                        retries=attempts
                    )

                except concurrent.futures.TimeoutError:
                    return TaskResult(
                        status=TaskStatus.TIMEOUT,
                        error=f"Task timed out after {config.timeout}s",
                        execution_time=time.time() - start_time,
                        retries=attempts
                    )

                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Task {func.__name__} failed (attempt {attempts + 1}): {last_error}"
                    )
                    attempts += 1

                    if attempts < max_attempts:
                        time.sleep(config.retry_delay)

            return TaskResult(
                status=TaskStatus.FAILED,
                error=last_error,
                execution_time=time.time() - start_time,
                retries=attempts
            )

        finally:
            with self._lock:
                self._current_task = None

    def cancel(self) -> bool:
        """
        Request cancellation of the current task.

        Returns:
            True if a task was running and cancellation was requested
        """
        with self._lock:
            if self._current_task:
                self._should_cancel = True
                logger.info(f"Cancellation requested for task: {self._current_task}")
                return True
        return False

    def execute_batch(
        self,
        tasks: list[tuple[Callable[..., Any], tuple, dict]],
        config: TaskConfig | None = None,
        stop_on_error: bool = False
    ) -> list[TaskResult[Any]]:
        """
        Execute multiple tasks sequentially.

        Args:
            tasks: List of (func, args, kwargs) tuples
            config: Shared task configuration
            stop_on_error: Whether to stop on first error

        Returns:
            List of TaskResults

        Example:
            >>> tasks = [
            ...     (import_asset, ("/path/to/a.fbx",), {}),
            ...     (import_asset, ("/path/to/b.fbx",), {}),
            ...     (import_asset, ("/path/to/c.fbx",), {}),
            ... ]
            >>> results = executor.execute_batch(tasks)
        """
        results: list[TaskResult[Any]] = []

        for func, args, kwargs in tasks:
            result = self.execute(func, *args, config=config, **kwargs)
            results.append(result)

            if stop_on_error and not result.success:
                logger.warning(f"Batch execution stopped due to error in {func.__name__}")
                break

        return results


class AsyncTaskExecutor:
    """
    Asynchronous task executor for non-blocking operations.

    Useful for long-running operations that shouldn't block the editor UI.

    Example:
        >>> async_executor = AsyncTaskExecutor()
        >>>
        >>> async def main():
        ...     result = await async_executor.execute_async(
        ...         long_running_task,
        ...         arg1, arg2
        ...     )
        ...     print(f"Task completed: {result.success}")
        >>>
        >>> asyncio.run(main())
    """

    def __init__(self, max_workers: int = 4) -> None:
        """
        Initialize the async task executor.

        Args:
            max_workers: Maximum number of concurrent workers
        """
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._pending_futures: dict[str, concurrent.futures.Future[Any]] = {}
        self._lock = threading.Lock()
        self._sync_executor = TaskExecutor()

    async def execute_async(
        self,
        func: Callable[..., T],
        *args: Any,
        config: TaskConfig | None = None,
        **kwargs: Any
    ) -> TaskResult[T]:
        """
        Execute a task asynchronously.

        Args:
            func: The function to execute
            *args: Positional arguments
            config: Task configuration
            **kwargs: Keyword arguments

        Returns:
            TaskResult containing the execution result

        Example:
            >>> async def process_assets():
            ...     result = await executor.execute_async(
            ...         batch_import,
            ...         asset_list,
            ...         config=TaskConfig(timeout=300.0)
            ...     )
            ...     return result
        """
        config = config or TaskConfig()
        loop = asyncio.get_event_loop()

        def wrapped_task() -> TaskResult[T]:
            return self._sync_executor.execute(func, *args, config=config, **kwargs)

        try:
            result = await loop.run_in_executor(self._executor, wrapped_task)
            return result
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                error=str(e)
            )

    def submit(
        self,
        func: Callable[..., T],
        *args: Any,
        config: TaskConfig | None = None,
        **kwargs: Any
    ) -> concurrent.futures.Future[TaskResult[T]]:
        """
        Submit a task for execution and return a Future.

        Args:
            func: The function to execute
            *args: Positional arguments
            config: Task configuration
            **kwargs: Keyword arguments

        Returns:
            Future that will contain the TaskResult

        Example:
            >>> future = executor.submit(process_asset, "/path/to/asset")
            >>> # Do other work...
            >>> result = future.result()  # Block until complete
        """
        config = config or TaskConfig()

        def wrapped_task() -> TaskResult[T]:
            return self._sync_executor.execute(func, *args, config=config, **kwargs)

        future = self._executor.submit(wrapped_task)

        with self._lock:
            task_id = f"{func.__name__}_{id(future)}"
            self._pending_futures[task_id] = future

        return future

    async def execute_parallel(
        self,
        tasks: list[tuple[Callable[..., Any], tuple, dict]],
        config: TaskConfig | None = None,
        max_concurrent: int | None = None
    ) -> list[TaskResult[Any]]:
        """
        Execute multiple tasks in parallel.

        Args:
            tasks: List of (func, args, kwargs) tuples
            config: Shared task configuration
            max_concurrent: Maximum concurrent tasks (None = unlimited)

        Returns:
            List of TaskResults in the same order as input tasks

        Example:
            >>> tasks = [
            ...     (process_asset, (path,), {}) for path in asset_paths
            ... ]
            >>> results = await executor.execute_parallel(tasks, max_concurrent=4)
        """
        if max_concurrent:
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_execute(
                func: Callable[..., Any], args: tuple, kwargs: dict
            ) -> TaskResult[Any]:
                async with semaphore:
                    return await self.execute_async(func, *args, config=config, **kwargs)

            coroutines = [
                limited_execute(func, args, kwargs)
                for func, args, kwargs in tasks
            ]
        else:
            coroutines = [
                self.execute_async(func, *args, config=config, **kwargs)
                for func, args, kwargs in tasks
            ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        processed_results: list[TaskResult[Any]] = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(TaskResult(
                    status=TaskStatus.FAILED,
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def cancel_all(self) -> int:
        """
        Cancel all pending tasks.

        Returns:
            Number of tasks cancelled
        """
        cancelled = 0
        with self._lock:
            for task_id, future in list(self._pending_futures.items()):
                if future.cancel():
                    cancelled += 1
                    del self._pending_futures[task_id]

        logger.info(f"Cancelled {cancelled} pending tasks")
        return cancelled

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the executor.

        Args:
            wait: Whether to wait for pending tasks to complete
        """
        self._executor.shutdown(wait=wait)
        logger.info("AsyncTaskExecutor shutdown complete")

    def __enter__(self) -> AsyncTaskExecutor:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.shutdown(wait=True)


def run_on_main_thread(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure a function runs on Unreal's main thread.

    Example:
        >>> @run_on_main_thread
        ... def spawn_actor(actor_class, location):
        ...     import unreal  # noqa: F401
        ...     return unreal.EditorLevelLibrary.spawn_actor_from_class(
        ...         actor_class, location
        ...     )
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        executor = TaskExecutor()
        result = executor.execute(func, *args, config=TaskConfig(run_on_game_thread=True), **kwargs)
        if result.success:
            return result.data  # type: ignore
        raise RuntimeError(result.error)
    return wrapper
