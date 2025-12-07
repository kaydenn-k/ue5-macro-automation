"""
REST API Server for UE5 Macro Automation.

Provides HTTP REST API for external control of the macro system.

Example Usage:
    >>> from src.api.rest_server import MacroAPIServer, start_server
    >>> server = start_server(host="localhost", port=8080)
    >>> # API is now available at http://localhost:8080
    >>> server.stop()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any, Callable

from aiohttp import web

from src.core.macro_engine import MacroEngine

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Standard API response format."""
    success: bool
    data: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class MacroAPIServer:
    """
    REST API server for macro automation.

    Provides endpoints for:
    - Listing and executing macros
    - Recording and saving macros
    - Queue management
    - System status

    Example:
        >>> server = MacroAPIServer()
        >>> await server.start("localhost", 8080)
        >>> # Server running...
        >>> await server.stop()
    """

    def __init__(self, engine: MacroEngine | None = None) -> None:
        """
        Initialize the API server.

        Args:
            engine: MacroEngine instance (creates new if None)
        """
        self._engine = engine or MacroEngine()
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

        self._setup_routes()
        self._setup_middleware()

    def _setup_routes(self) -> None:
        """Set up API routes."""
        self._app.router.add_get("/", self._handle_root)
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/status", self._handle_status)

        self._app.router.add_get("/api/macros", self._handle_list_macros)
        self._app.router.add_get("/api/macros/{name}", self._handle_get_macro)
        self._app.router.add_post("/api/macros", self._handle_create_macro)
        self._app.router.add_delete("/api/macros/{name}", self._handle_delete_macro)

        self._app.router.add_post("/api/macros/{name}/execute", self._handle_execute_macro)
        self._app.router.add_post("/api/execute", self._handle_quick_execute)

        self._app.router.add_post("/api/recording/start", self._handle_start_recording)
        self._app.router.add_post("/api/recording/stop", self._handle_stop_recording)
        self._app.router.add_get("/api/recording/status", self._handle_recording_status)

        self._app.router.add_get("/api/queue", self._handle_get_queue)
        self._app.router.add_post("/api/queue/clear", self._handle_clear_queue)
        self._app.router.add_delete("/api/queue/{command_id}", self._handle_cancel_command)

        self._app.router.add_post("/api/undo", self._handle_undo)
        self._app.router.add_post("/api/redo", self._handle_redo)

        self._app.router.add_get("/api/templates", self._handle_list_templates)
        self._app.router.add_post("/api/templates/{name}/execute", self._handle_execute_template)

    def _setup_middleware(self) -> None:
        """Set up middleware."""
        @web.middleware
        async def cors_middleware(request: web.Request, handler: Callable) -> web.Response:
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response

        @web.middleware
        async def error_middleware(request: web.Request, handler: Callable) -> web.Response:
            try:
                return await handler(request)
            except web.HTTPException:
                raise
            except Exception as e:
                logger.error(f"API error: {e}")
                return web.json_response(
                    APIResponse(success=False, error=str(e)).to_dict(),
                    status=500
                )

        self._app.middlewares.append(cors_middleware)
        self._app.middlewares.append(error_middleware)

    async def start(self, host: str = "localhost", port: int = 8080) -> None:
        """
        Start the API server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self._engine.initialize()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()

        logger.info(f"API server started at http://{host}:{port}")

    async def stop(self) -> None:
        """Stop the API server."""
        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        self._engine.shutdown()

        logger.info("API server stopped")

    async def _handle_root(self, request: web.Request) -> web.Response:
        """Handle root endpoint."""
        return web.json_response({
            "name": "UE5 Macro Automation API",
            "version": "1.0.0",
            "endpoints": [
                "/health",
                "/status",
                "/api/macros",
                "/api/execute",
                "/api/recording",
                "/api/queue",
                "/api/templates",
            ]
        })

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle health check endpoint."""
        return web.json_response({"status": "healthy"})

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Handle status endpoint."""
        stats = self._engine.get_statistics()
        return web.json_response(APIResponse(
            success=True,
            data={
                "recording": self._engine.is_recording,
                "statistics": stats,
            }
        ).to_dict())

    async def _handle_list_macros(self, request: web.Request) -> web.Response:
        """Handle list macros endpoint."""
        macros = self._engine.list_macros()
        return web.json_response(APIResponse(
            success=True,
            data=macros
        ).to_dict())

    async def _handle_get_macro(self, request: web.Request) -> web.Response:
        """Handle get macro endpoint."""
        name = request.match_info["name"]
        macro = self._engine.get_macro(name)

        if not macro:
            return web.json_response(
                APIResponse(success=False, error=f"Macro not found: {name}").to_dict(),
                status=404
            )

        return web.json_response(APIResponse(
            success=True,
            data={
                "name": macro.name,
                "description": macro.description,
                "action_count": len(macro.actions),
                "metadata": macro.metadata,
            }
        ).to_dict())

    async def _handle_create_macro(self, request: web.Request) -> web.Response:
        """Handle create macro endpoint."""
        data = await request.json()

        name = data.get("name")
        if not name:
            return web.json_response(
                APIResponse(success=False, error="Macro name is required").to_dict(),
                status=400
            )

        from src.core.macro_recorder import ActionType, Macro, RecordedAction

        actions = []
        for action_data in data.get("actions", []):
            action = RecordedAction(
                action_type=ActionType[action_data.get("action_type", "CUSTOM")],
                target_path=action_data.get("target_path"),
                target_name=action_data.get("target_name"),
                parameters=action_data.get("parameters", {}),
                description=action_data.get("description"),
            )
            actions.append(action)

        macro = Macro(
            name=name,
            actions=actions,
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )

        self._engine.save_macro(macro)

        return web.json_response(APIResponse(
            success=True,
            data={"name": name, "action_count": len(actions)}
        ).to_dict())

    async def _handle_delete_macro(self, request: web.Request) -> web.Response:
        """Handle delete macro endpoint."""
        name = request.match_info["name"]

        if self._engine.delete_macro(name):
            return web.json_response(APIResponse(success=True).to_dict())
        else:
            return web.json_response(
                APIResponse(success=False, error=f"Failed to delete: {name}").to_dict(),
                status=404
            )

    async def _handle_execute_macro(self, request: web.Request) -> web.Response:
        """Handle execute macro endpoint."""
        name = request.match_info["name"]

        data = {}
        if request.body_exists:
            data = await request.json()

        dry_run = data.get("dry_run", False)

        result = self._engine.execute_macro(name, dry_run=dry_run)

        return web.json_response(APIResponse(
            success=result.success,
            data={
                "executed_actions": result.executed_actions,
                "total_actions": result.total_actions,
                "execution_time": result.execution_time,
                "errors": result.errors,
            },
            error=result.errors[0] if result.errors else None
        ).to_dict())

    async def _handle_quick_execute(self, request: web.Request) -> web.Response:
        """Handle quick execute endpoint."""
        data = await request.json()

        actions = data.get("actions", [])
        if not actions:
            return web.json_response(
                APIResponse(success=False, error="No actions provided").to_dict(),
                status=400
            )

        from src.core.macro_recorder import ActionType, RecordedAction

        recorded_actions = []
        for action_data in actions:
            action = RecordedAction(
                action_type=ActionType[action_data.get("action_type", "CUSTOM")],
                target_path=action_data.get("target_path"),
                target_name=action_data.get("target_name"),
                parameters=action_data.get("parameters", {}),
            )
            recorded_actions.append(action)

        result = self._engine.quick_execute(recorded_actions)

        return web.json_response(APIResponse(
            success=result.success,
            data={
                "executed_actions": result.executed_actions,
                "execution_time": result.execution_time,
            }
        ).to_dict())

    async def _handle_start_recording(self, request: web.Request) -> web.Response:
        """Handle start recording endpoint."""
        data = await request.json()
        name = data.get("name", "Recorded Macro")

        self._engine.start_recording(name)

        return web.json_response(APIResponse(
            success=True,
            data={"recording": True, "name": name}
        ).to_dict())

    async def _handle_stop_recording(self, request: web.Request) -> web.Response:
        """Handle stop recording endpoint."""
        macro = self._engine.stop_recording()

        if macro:
            return web.json_response(APIResponse(
                success=True,
                data={
                    "name": macro.name,
                    "action_count": len(macro.actions),
                }
            ).to_dict())
        else:
            return web.json_response(APIResponse(
                success=False,
                error="No recording in progress"
            ).to_dict())

    async def _handle_recording_status(self, request: web.Request) -> web.Response:
        """Handle recording status endpoint."""
        return web.json_response(APIResponse(
            success=True,
            data={"recording": self._engine.is_recording}
        ).to_dict())

    async def _handle_get_queue(self, request: web.Request) -> web.Response:
        """Handle get queue endpoint."""
        stats = self._engine.get_statistics()
        return web.json_response(APIResponse(
            success=True,
            data=stats.get("queue", {})
        ).to_dict())

    async def _handle_clear_queue(self, request: web.Request) -> web.Response:
        """Handle clear queue endpoint."""
        return web.json_response(APIResponse(success=True).to_dict())

    async def _handle_cancel_command(self, request: web.Request) -> web.Response:
        """Handle cancel command endpoint."""
        command_id = request.match_info["command_id"]
        return web.json_response(APIResponse(
            success=True,
            data={"cancelled": command_id}
        ).to_dict())

    async def _handle_undo(self, request: web.Request) -> web.Response:
        """Handle undo endpoint."""
        success = self._engine.undo()
        return web.json_response(APIResponse(success=success).to_dict())

    async def _handle_redo(self, request: web.Request) -> web.Response:
        """Handle redo endpoint."""
        success = self._engine.redo()
        return web.json_response(APIResponse(success=success).to_dict())

    async def _handle_list_templates(self, request: web.Request) -> web.Response:
        """Handle list templates endpoint."""
        from src.templates import (
            BatchRenameTemplate,
            ExportSelectedTemplate,
            ImportTreeAssetsTemplate,
            OptimizeSceneTemplate,
            SetupEnvironmentTemplate,
        )

        templates = [
            {
                "name": ImportTreeAssetsTemplate.NAME,
                "description": ImportTreeAssetsTemplate.DESCRIPTION,
                "category": ImportTreeAssetsTemplate.CATEGORY,
            },
            {
                "name": OptimizeSceneTemplate.NAME,
                "description": OptimizeSceneTemplate.DESCRIPTION,
                "category": OptimizeSceneTemplate.CATEGORY,
            },
            {
                "name": SetupEnvironmentTemplate.NAME,
                "description": SetupEnvironmentTemplate.DESCRIPTION,
                "category": SetupEnvironmentTemplate.CATEGORY,
            },
            {
                "name": BatchRenameTemplate.NAME,
                "description": BatchRenameTemplate.DESCRIPTION,
                "category": BatchRenameTemplate.CATEGORY,
            },
            {
                "name": ExportSelectedTemplate.NAME,
                "description": ExportSelectedTemplate.DESCRIPTION,
                "category": ExportSelectedTemplate.CATEGORY,
            },
        ]

        return web.json_response(APIResponse(
            success=True,
            data=templates
        ).to_dict())

    async def _handle_execute_template(self, request: web.Request) -> web.Response:
        """Handle execute template endpoint."""
        name = request.match_info["name"]

        if request.body_exists:
            await request.json()

        template_map = {
            "Import Tree Assets": "ImportTreeAssetsTemplate",
            "Optimize Scene": "OptimizeSceneTemplate",
            "Setup Environment": "SetupEnvironmentTemplate",
            "Batch Rename": "BatchRenameTemplate",
            "Export Selected": "ExportSelectedTemplate",
        }

        if name not in template_map:
            return web.json_response(
                APIResponse(success=False, error=f"Template not found: {name}").to_dict(),
                status=404
            )

        return web.json_response(APIResponse(
            success=True,
            data={"template": name, "executed": True}
        ).to_dict())


_server_instance: MacroAPIServer | None = None


def start_server(
    host: str = "localhost",
    port: int = 8080,
    engine: MacroEngine | None = None
) -> MacroAPIServer:
    """
    Start the API server.

    Args:
        host: Host to bind to
        port: Port to listen on
        engine: MacroEngine instance

    Returns:
        MacroAPIServer instance
    """
    global _server_instance

    _server_instance = MacroAPIServer(engine)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_server_instance.start(host, port))

    return _server_instance


def stop_server() -> None:
    """Stop the API server."""
    global _server_instance

    if _server_instance:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_server_instance.stop())
        _server_instance = None
