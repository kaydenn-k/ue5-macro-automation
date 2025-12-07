"""
API module for UE5 Macro Automation System.

Contains REST API server and client for external control:
- HTTP REST API server
- WebSocket support for real-time updates
- Watch folder automation
- External tool integration
"""

from src.api.external_tools import BlenderIntegration, SubstanceIntegration
from src.api.rest_server import MacroAPIServer, start_server, stop_server
from src.api.watch_folder import WatchFolderAutomation

__all__ = [
    "MacroAPIServer",
    "start_server",
    "stop_server",
    "WatchFolderAutomation",
    "BlenderIntegration",
    "SubstanceIntegration",
]
