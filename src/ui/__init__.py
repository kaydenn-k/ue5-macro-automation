"""
UI module for UE5 Macro Automation System.

Contains Qt-based GUI components:
- Main panel that docks inside Unreal Editor
- Macro library browser
- Macro editor with syntax highlighting
- Progress and logging displays
- Hotkey configuration
"""

from src.ui.hotkey_manager import HotkeyManager
from src.ui.log_widget import LogWidget
from src.ui.macro_editor import MacroEditorWidget
from src.ui.macro_library import MacroLibraryWidget
from src.ui.main_panel import MacroAutomationPanel
from src.ui.progress_widget import ProgressWidget

__all__ = [
    "MacroAutomationPanel",
    "MacroLibraryWidget",
    "MacroEditorWidget",
    "ProgressWidget",
    "LogWidget",
    "HotkeyManager",
]
