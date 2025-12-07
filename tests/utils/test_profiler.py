"""
Tests for the profiler module.
"""

import time

import pytest

from src.utils.profiler import (
    Profiler,
    ProfileResult,
    profile,
)


class TestProfiler:
    """Tests for the Profiler class."""

    @pytest.fixture
    def profiler(self):
        """Create a Profiler instance."""
        return Profiler()

    def test_profiler_creation(self, profiler):
        """Test creating a profiler."""
        assert profiler is not None

    def test_start_stop(self, profiler):
        """Test starting and stopping profiler."""
        profiler.start("test_operation")
        time.sleep(0.01)
        result = profiler.stop("test_operation")

        assert result is not None
        assert result.name == "test_operation"
        assert result.duration >= 0.01

    def test_context_manager(self, profiler):
        """Test using profiler as context manager."""
        with profiler.profile("test_operation"):
            time.sleep(0.01)

        results = profiler.get_results()
        assert "test_operation" in results

    def test_multiple_operations(self, profiler):
        """Test profiling multiple operations."""
        profiler.start("op1")
        time.sleep(0.01)
        profiler.stop("op1")

        profiler.start("op2")
        time.sleep(0.01)
        profiler.stop("op2")

        results = profiler.get_results()

        assert "op1" in results
        assert "op2" in results

    def test_nested_operations(self, profiler):
        """Test nested profiling."""
        profiler.start("outer")
        profiler.start("inner")
        time.sleep(0.01)
        profiler.stop("inner")
        profiler.stop("outer")

        results = profiler.get_results()

        assert results["outer"].duration >= results["inner"].duration

    def test_get_summary(self, profiler):
        """Test getting profiler summary."""
        profiler.start("test")
        time.sleep(0.01)
        profiler.stop("test")

        summary = profiler.get_summary()

        assert "test" in summary
        assert "duration" in summary.lower() or "time" in summary.lower()

    def test_clear(self, profiler):
        """Test clearing profiler results."""
        profiler.start("test")
        profiler.stop("test")

        profiler.clear()

        results = profiler.get_results()
        assert len(results) == 0


class TestProfileDecorator:
    """Tests for the profile decorator."""

    def test_decorator(self):
        """Test profile decorator."""
        @profile
        def slow_function():
            time.sleep(0.01)
            return 42

        result = slow_function()

        assert result == 42

    def test_decorator_with_args(self):
        """Test profile decorator with function arguments."""
        @profile
        def add(a, b):
            return a + b

        result = add(5, 3)

        assert result == 8

    def test_decorator_preserves_name(self):
        """Test that decorator preserves function name."""
        @profile
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestProfileResult:
    """Tests for the ProfileResult class."""

    def test_result_creation(self):
        """Test creating a profile result."""
        result = ProfileResult(
            name="test",
            duration=1.5,
            start_time=0.0,
            end_time=1.5,
        )

        assert result.name == "test"
        assert result.duration == 1.5

    def test_result_str(self):
        """Test profile result string representation."""
        result = ProfileResult(
            name="test",
            duration=1.5,
            start_time=0.0,
            end_time=1.5,
        )

        result_str = str(result)

        assert "test" in result_str
        assert "1.5" in result_str or "1.50" in result_str
