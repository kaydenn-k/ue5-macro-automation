"""
Performance Profiler for UE5 Macro Automation.

Provides performance profiling and timing utilities for macro execution
analysis and optimization.

Example Usage:
    >>> profiler = Profiler()
    >>> profiler.start("import_assets")
    >>> # ... do work ...
    >>> profiler.stop("import_assets")
    >>> print(profiler.get_report())

    >>> @profile_function
    ... def my_function():
    ...     pass
"""

from __future__ import annotations

import functools
import logging
import statistics
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ProfileEntry:
    """
    A single profiling entry.

    Attributes:
        name: Name of the profiled operation
        start_time: When the operation started
        end_time: When the operation ended
        duration: Duration in seconds
        memory_start: Memory usage at start (bytes)
        memory_end: Memory usage at end (bytes)
        metadata: Additional metadata
    """
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    memory_start: int = 0
    memory_end: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def memory_delta(self) -> int:
        """Memory change during operation."""
        return self.memory_end - self.memory_start


@dataclass
class ProfileStats:
    """
    Statistics for a profiled operation.

    Attributes:
        name: Operation name
        call_count: Number of times called
        total_time: Total time spent
        min_time: Minimum execution time
        max_time: Maximum execution time
        avg_time: Average execution time
        std_dev: Standard deviation of execution times
        total_memory_delta: Total memory change
    """
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    avg_time: float = 0.0
    std_dev: float = 0.0
    total_memory_delta: int = 0
    times: list[float] = field(default_factory=list)

    def add_entry(self, entry: ProfileEntry) -> None:
        """Add a profile entry to statistics."""
        self.call_count += 1
        self.total_time += entry.duration
        self.min_time = min(self.min_time, entry.duration)
        self.max_time = max(self.max_time, entry.duration)
        self.total_memory_delta += entry.memory_delta
        self.times.append(entry.duration)

        self.avg_time = self.total_time / self.call_count
        if len(self.times) > 1:
            self.std_dev = statistics.stdev(self.times)


class Profiler:
    """
    Performance profiler for macro operations.

    Tracks execution time, memory usage, and provides detailed reports
    for performance analysis.

    Example:
        >>> profiler = Profiler()
        >>>
        >>> # Manual timing
        >>> profiler.start("operation")
        >>> # ... do work ...
        >>> profiler.stop("operation")
        >>>
        >>> # Context manager
        >>> with profiler.profile("another_operation"):
        ...     # ... do work ...
        ...     pass
        >>>
        >>> # Get report
        >>> print(profiler.get_report())
    """

    _instance: Profiler | None = None
    _lock = threading.Lock()

    def __new__(cls) -> Profiler:
        """Singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initialize the profiler."""
        if self._initialized:
            return

        self._entries: dict[str, list[ProfileEntry]] = {}
        self._stats: dict[str, ProfileStats] = {}
        self._active: dict[str, ProfileEntry] = {}
        self._enabled = True
        self._lock = threading.Lock()
        self._initialized = True

    @classmethod
    def get_instance(cls) -> Profiler:
        """Get the singleton instance."""
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance."""
        with cls._lock:
            cls._instance = None

    @property
    def enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable profiling."""
        self._enabled = value

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        if not PSUTIL_AVAILABLE:
            return 0

        try:
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            return 0

    def start(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Start profiling an operation.

        Args:
            name: Operation name
            metadata: Optional metadata to attach

        Example:
            >>> profiler.start("import_fbx")
        """
        if not self._enabled:
            return

        with self._lock:
            entry = ProfileEntry(
                name=name,
                start_time=time.perf_counter(),
                memory_start=self._get_memory_usage(),
                metadata=metadata or {}
            )
            self._active[name] = entry

    def stop(self, name: str) -> ProfileEntry | None:
        """
        Stop profiling an operation.

        Args:
            name: Operation name

        Returns:
            The completed profile entry

        Example:
            >>> entry = profiler.stop("import_fbx")
            >>> print(f"Duration: {entry.duration:.3f}s")
        """
        if not self._enabled:
            return None

        with self._lock:
            if name not in self._active:
                logger.warning(f"No active profile for: {name}")
                return None

            entry = self._active.pop(name)
            entry.end_time = time.perf_counter()
            entry.duration = entry.end_time - entry.start_time
            entry.memory_end = self._get_memory_usage()

            if name not in self._entries:
                self._entries[name] = []
            self._entries[name].append(entry)

            if name not in self._stats:
                self._stats[name] = ProfileStats(name=name)
            self._stats[name].add_entry(entry)

            return entry

    @contextmanager
    def profile(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> Generator[None, None, None]:
        """
        Context manager for profiling.

        Args:
            name: Operation name
            metadata: Optional metadata

        Example:
            >>> with profiler.profile("process_mesh"):
            ...     # ... do work ...
            ...     pass
        """
        self.start(name, metadata)
        try:
            yield
        finally:
            self.stop(name)

    def get_stats(self, name: str) -> ProfileStats | None:
        """
        Get statistics for an operation.

        Args:
            name: Operation name

        Returns:
            ProfileStats or None if not found
        """
        return self._stats.get(name)

    def get_all_stats(self) -> dict[str, ProfileStats]:
        """
        Get all profiling statistics.

        Returns:
            Dictionary of operation names to stats
        """
        return self._stats.copy()

    def get_entries(self, name: str) -> list[ProfileEntry]:
        """
        Get all entries for an operation.

        Args:
            name: Operation name

        Returns:
            List of profile entries
        """
        return self._entries.get(name, []).copy()

    def clear(self) -> None:
        """Clear all profiling data."""
        with self._lock:
            self._entries.clear()
            self._stats.clear()
            self._active.clear()

    def get_report(self, sort_by: str = "total_time") -> str:
        """
        Generate a profiling report.

        Args:
            sort_by: Field to sort by (total_time, call_count, avg_time)

        Returns:
            Formatted report string

        Example:
            >>> print(profiler.get_report())
        """
        if not self._stats:
            return "No profiling data available."

        lines = [
            "=" * 80,
            "PERFORMANCE PROFILING REPORT",
            "=" * 80,
            "",
            f"{'Operation':<30} {'Calls':>8} {'Total':>10} {'Avg':>10} {'Min':>10} {'Max':>10}",
            "-" * 80,
        ]

        stats_list = list(self._stats.values())

        if sort_by == "call_count":
            stats_list.sort(key=lambda s: s.call_count, reverse=True)
        elif sort_by == "avg_time":
            stats_list.sort(key=lambda s: s.avg_time, reverse=True)
        else:
            stats_list.sort(key=lambda s: s.total_time, reverse=True)

        for stats in stats_list:
            lines.append(
                f"{stats.name:<30} {stats.call_count:>8} "
                f"{stats.total_time:>9.3f}s {stats.avg_time:>9.3f}s "
                f"{stats.min_time:>9.3f}s {stats.max_time:>9.3f}s"
            )

        lines.extend([
            "-" * 80,
            "",
            "Memory Usage:",
        ])

        for stats in stats_list:
            if stats.total_memory_delta != 0:
                delta_mb = stats.total_memory_delta / (1024 * 1024)
                lines.append(f"  {stats.name}: {delta_mb:+.2f} MB")

        lines.append("=" * 80)

        return "\n".join(lines)

    def get_json_report(self) -> dict[str, Any]:
        """
        Get profiling data as JSON-serializable dictionary.

        Returns:
            Dictionary with profiling data
        """
        return {
            "stats": {
                name: {
                    "call_count": stats.call_count,
                    "total_time": stats.total_time,
                    "avg_time": stats.avg_time,
                    "min_time": stats.min_time if stats.min_time != float("inf") else 0,
                    "max_time": stats.max_time,
                    "std_dev": stats.std_dev,
                    "total_memory_delta": stats.total_memory_delta,
                }
                for name, stats in self._stats.items()
            },
            "entries_count": {
                name: len(entries)
                for name, entries in self._entries.items()
            }
        }


def profile_function(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to profile a function.

    Example:
        >>> @profile_function
        ... def my_expensive_function():
        ...     time.sleep(1)
        ...     return "done"
        >>>
        >>> result = my_expensive_function()
        >>> print(Profiler.get_instance().get_report())
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        profiler = Profiler.get_instance()
        with profiler.profile(func.__name__):
            return func(*args, **kwargs)
    return wrapper


def profile_method(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to profile a method (includes class name).

    Example:
        >>> class MyClass:
        ...     @profile_method
        ...     def my_method(self):
        ...         pass
    """
    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
        profiler = Profiler.get_instance()
        name = f"{self.__class__.__name__}.{func.__name__}"
        with profiler.profile(name):
            return func(self, *args, **kwargs)
    return wrapper


class Timer:
    """
    Simple timer for measuring execution time.

    Example:
        >>> timer = Timer()
        >>> timer.start()
        >>> # ... do work ...
        >>> elapsed = timer.stop()
        >>> print(f"Elapsed: {elapsed:.3f}s")
    """

    def __init__(self) -> None:
        """Initialize the timer."""
        self._start_time: float | None = None
        self._end_time: float | None = None

    def start(self) -> Timer:
        """Start the timer."""
        self._start_time = time.perf_counter()
        self._end_time = None
        return self

    def stop(self) -> float:
        """
        Stop the timer and return elapsed time.

        Returns:
            Elapsed time in seconds
        """
        self._end_time = time.perf_counter()
        return self.elapsed

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self._start_time is None:
            return 0.0

        end = self._end_time or time.perf_counter()
        return end - self._start_time

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed * 1000

    def __enter__(self) -> Timer:
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()


def measure_time(func: Callable[..., T], *args: Any, **kwargs: Any) -> tuple[T, float]:
    """
    Measure execution time of a function call.

    Args:
        func: Function to call
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Tuple of (result, elapsed_time)

    Example:
        >>> result, elapsed = measure_time(my_function, arg1, arg2)
        >>> print(f"Result: {result}, Time: {elapsed:.3f}s")
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def benchmark(
    func: Callable[..., Any],
    *args: Any,
    iterations: int = 100,
    warmup: int = 10,
    **kwargs: Any
) -> dict[str, float]:
    """
    Benchmark a function with multiple iterations.

    Args:
        func: Function to benchmark
        *args: Positional arguments
        iterations: Number of iterations
        warmup: Number of warmup iterations
        **kwargs: Keyword arguments

    Returns:
        Dictionary with benchmark statistics

    Example:
        >>> stats = benchmark(my_function, arg1, iterations=1000)
        >>> print(f"Average: {stats['avg']:.6f}s")
    """
    for _ in range(warmup):
        func(*args, **kwargs)

    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        times.append(time.perf_counter() - start)

    return {
        "iterations": iterations,
        "total": sum(times),
        "avg": statistics.mean(times),
        "min": min(times),
        "max": max(times),
        "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        "median": statistics.median(times),
    }
