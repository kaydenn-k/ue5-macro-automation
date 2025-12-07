"""
Tests for the rest_server module.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.api.rest_server import (
    APIResponse,
    MacroAPIServer,
)


class TestAPIResponse:
    """Tests for the APIResponse class."""

    def test_success_response(self):
        """Test creating a success response."""
        response = APIResponse(
            success=True,
            data={"key": "value"},
        )

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.error is None

    def test_error_response(self):
        """Test creating an error response."""
        response = APIResponse(
            success=False,
            error="Something went wrong",
        )

        assert response.success is False
        assert response.error == "Something went wrong"

    def test_to_dict(self):
        """Test converting response to dictionary."""
        response = APIResponse(
            success=True,
            data={"key": "value"},
        )

        result = response.to_dict()

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["data"] == {"key": "value"}


class TestMacroAPIServer:
    """Tests for the MacroAPIServer class."""

    @pytest.fixture
    def server(self):
        """Create a MacroAPIServer instance."""
        with patch("src.api.rest_server.MacroEngine"):
            server = MacroAPIServer(host="127.0.0.1", port=8080)
            yield server

    def test_server_creation(self, server):
        """Test creating a server."""
        assert server is not None
        assert server._host == "127.0.0.1"
        assert server._port == 8080

    def test_routes_setup(self, server):
        """Test that routes are set up."""
        assert server._app is not None

    @pytest.mark.asyncio
    async def test_health_endpoint(self, server):
        """Test health check endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        async with TestClient(TestServer(server._app)) as client:
            response = await client.get("/health")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_status_endpoint(self, server):
        """Test status endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        server._engine.get_status.return_value = {
            "initialized": True,
            "recording": False,
        }

        async with TestClient(TestServer(server._app)) as client:
            response = await client.get("/status")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_macros_endpoint(self, server):
        """Test list macros endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        server._engine.get_macro_names.return_value = ["Macro1", "Macro2"]

        async with TestClient(TestServer(server._app)) as client:
            response = await client.get("/api/macros")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True
            assert "macros" in data["data"]

    @pytest.mark.asyncio
    async def test_create_macro_endpoint(self, server):
        """Test create macro endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        server._engine.register_macro.return_value = True

        macro_data = {
            "name": "Test Macro",
            "actions": [
                {"action_type": "CUSTOM", "parameters": {}}
            ],
        }

        async with TestClient(TestServer(server._app)) as client:
            response = await client.post(
                "/api/macros",
                json=macro_data,
            )

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_execute_macro_endpoint(self, server):
        """Test execute macro endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        mock_result = MagicMock()
        mock_result.success = True
        server._engine.execute_macro.return_value = mock_result

        async with TestClient(TestServer(server._app)) as client:
            response = await client.post("/api/macros/TestMacro/execute")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_start_recording_endpoint(self, server):
        """Test start recording endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        async with TestClient(TestServer(server._app)) as client:
            response = await client.post(
                "/api/recording/start",
                json={"name": "Test Recording"},
            )

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_stop_recording_endpoint(self, server):
        """Test stop recording endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        mock_macro = MagicMock()
        mock_macro.name = "Test Recording"
        mock_macro.actions = []
        server._engine.stop_recording.return_value = mock_macro

        async with TestClient(TestServer(server._app)) as client:
            response = await client.post("/api/recording/stop")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_templates_endpoint(self, server):
        """Test list templates endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        async with TestClient(TestServer(server._app)) as client:
            response = await client.get("/api/templates")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True
            assert "templates" in data["data"]

    @pytest.mark.asyncio
    async def test_undo_endpoint(self, server):
        """Test undo endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        server._engine.undo.return_value = True

        async with TestClient(TestServer(server._app)) as client:
            response = await client.post("/api/undo")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_redo_endpoint(self, server):
        """Test redo endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        server._engine.redo.return_value = True

        async with TestClient(TestServer(server._app)) as client:
            response = await client.post("/api/redo")

            assert response.status == 200
            data = await response.json()
            assert data["success"] is True
