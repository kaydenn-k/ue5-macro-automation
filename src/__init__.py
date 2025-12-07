"""
UE5 Macro Automation System

A comprehensive Python-based macro automation system for Unreal Engine 5
that provides programmatic control over the editor.
"""

__version__ = "1.0.0"
__author__ = "UE5 Macro Automation Team"

from src.core.command_queue import CommandQueue
from src.core.macro_engine import MacroEngine
from src.core.macro_recorder import MacroRecorder
from src.core.task_executor import AsyncTaskExecutor, TaskExecutor

__all__ = [
    "CommandQueue",
    "TaskExecutor",
    "AsyncTaskExecutor",
    "MacroRecorder",
    "MacroEngine",
]
