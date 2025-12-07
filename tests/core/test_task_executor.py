"""
Tests for the TaskExecutor module.
"""


import pytest

from src.core.task_executor import (
    AsyncTaskExecutor,
    TaskConfig,
    TaskResult,
    TaskStatus,
)


class TestTaskExecutor:
    """Tests for the TaskExecutor class."""

    def test_executor_creation(self, task_executor):
        """Test creating a task executor."""
        assert task_executor is not None

    def test_execute_simple_task(self, task_executor):
        """Test executing a simple task."""
        def simple_task():
            return 42

        result = task_executor.execute(simple_task)

        assert result.success
        assert result.value == 42
        assert result.status == TaskStatus.COMPLETED

    def test_execute_task_with_args(self, task_executor):
        """Test executing a task with arguments."""
        def add(a, b):
            return a + b

        result = task_executor.execute(add, 5, 3)

        assert result.success
        assert result.value == 8

    def test_execute_task_with_kwargs(self, task_executor):
        """Test executing a task with keyword arguments."""
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = task_executor.execute(greet, "World", greeting="Hi")

        assert result.success
        assert result.value == "Hi, World!"

    def test_execute_failing_task(self, task_executor):
        """Test executing a task that raises an exception."""
        def failing_task():
            raise ValueError("Test error")

        result = task_executor.execute(failing_task)

        assert not result.success
        assert result.status == TaskStatus.FAILED
        assert result.error is not None
        assert "Test error" in result.error

    def test_execute_with_retry(self, task_executor):
        """Test executing a task with retry."""
        attempts = [0]

        def flaky_task():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("Not yet")
            return "Success"

        config = TaskConfig(max_retries=3, retry_delay=0.01)
        result = task_executor.execute(flaky_task, config=config)

        assert result.success
        assert result.value == "Success"
        assert attempts[0] == 3

    def test_execute_batch(self, task_executor):
        """Test executing multiple tasks."""
        tasks = [
            lambda: 1,
            lambda: 2,
            lambda: 3,
        ]

        results = task_executor.execute_batch(tasks)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.value for r in results] == [1, 2, 3]

    def test_task_result_properties(self):
        """Test TaskResult properties."""
        result = TaskResult(
            success=True,
            value=42,
            status=TaskStatus.COMPLETED,
            execution_time=1.5,
        )

        assert result.success
        assert result.value == 42
        assert result.status == TaskStatus.COMPLETED
        assert result.execution_time == 1.5


class TestAsyncTaskExecutor:
    """Tests for the AsyncTaskExecutor class."""

    @pytest.fixture
    def async_executor(self):
        """Create an AsyncTaskExecutor instance."""
        executor = AsyncTaskExecutor(max_workers=2)
        yield executor
        executor.shutdown()

    def test_async_executor_creation(self, async_executor):
        """Test creating an async task executor."""
        assert async_executor is not None

    def test_submit_task(self, async_executor):
        """Test submitting a task."""
        def task():
            return 42

        future = async_executor.submit(task)
        result = future.result(timeout=5)

        assert result.success
        assert result.value == 42

    def test_execute_parallel(self, async_executor):
        """Test executing tasks in parallel."""
        import time

        def slow_task(n):
            time.sleep(0.1)
            return n * 2

        tasks = [(slow_task, (i,)) for i in range(4)]

        start = time.time()
        results = async_executor.execute_parallel(tasks)
        elapsed = time.time() - start

        assert len(results) == 4
        assert all(r.success for r in results)
        assert elapsed < 0.5

    def test_shutdown(self, async_executor):
        """Test shutting down the executor."""
        async_executor.shutdown()

        assert async_executor._shutdown


class TestTaskConfig:
    """Tests for the TaskConfig class."""

    def test_default_config(self):
        """Test default task configuration."""
        config = TaskConfig()

        assert config.timeout is None
        assert config.max_retries == 0
        assert config.retry_delay == 1.0
        assert config.run_on_main_thread is False

    def test_custom_config(self):
        """Test custom task configuration."""
        config = TaskConfig(
            timeout=30.0,
            max_retries=3,
            retry_delay=0.5,
            run_on_main_thread=True,
        )

        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 0.5
        assert config.run_on_main_thread is True
