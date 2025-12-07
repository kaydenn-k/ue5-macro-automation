"""
Core module for UE5 Macro Automation System.

Contains the fundamental components:
- CommandQueue: Queue system for batch operations
- TaskExecutor: Synchronous and asynchronous task execution
- MacroRecorder: Capture and replay editor actions
- MacroEngine: Main engine coordinating all components
"""

from src.core.command_queue import Command, CommandPriority, CommandQueue, CommandStatus
from src.core.macro_engine import MacroEngine
from src.core.macro_recorder import ActionType, MacroRecorder, RecordedAction
from src.core.rollback import RollbackAction, RollbackManager
from src.core.task_executor import AsyncTaskExecutor, TaskExecutor, TaskResult, TaskStatus

__all__ = [
    "CommandQueue",
    "Command",
    "CommandStatus",
    "CommandPriority",
    "TaskExecutor",
    "AsyncTaskExecutor",
    "TaskResult",
    "TaskStatus",
    "MacroRecorder",
    "RecordedAction",
    "ActionType",
    "MacroEngine",
    "RollbackManager",
    "RollbackAction",
]
