"""Tests for gateway — HTTP client with retry, timeout, error mapping"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gateway.client import HTTPClient
from gateway.config import GatewayConfig
from gateway.errors import (
    ChatbotError,
    ChatbotErrorCode,
    GatewayConnectionError,
    GatewayTimeoutError,
    NotFoundError,
    ShopNotFoundError,
    ValidationError,
)


def make_response(status_code: int, json_data: dict | None = None) -> httpx.Response:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = "error"
    if json_data is not None:
        response.json = MagicMock(return_value=json_data)
    else:
        response.json = MagicMock(side_effect=Exception("invalid json"))
    return response


@pytest.fixture
def config() -> GatewayConfig:
    return GatewayConfig(
        flask_base_url="http://test:5000",
        timeout_seconds=1.0,
        max_retries=2,
        retry_backoff_factor=0.01,
        retry_backoff_max=0.1,
    )


@pytest.fixture
def client(config: GatewayConfig) -> HTTPClient:
    return HTTPClient(config)


@pytest.mark.asyncio
async def test_get_success(client: HTTPClient) -> None:
    mock_response = make_response(200, {"success": True, "data": []})
    with patch.object(client, "_get_client") as mock_get:
        mock_http_client = AsyncMock()
        mock_http_client.is_closed = False
        mock_http_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_http_client
        result = await client.get("/shops")
        assert result == {"success": True, "data": []}


@pytest.mark.asyncio
async def test_get_404_maps_to_not_found(client: HTTPClient) -> None:
    mock_response = make_response(404, {"error": {"code": "SHOP_NOT_FOUND", "message": "Not found"}})
    with patch.object(client, "_get_client") as mock_get:
        mock_http_client = AsyncMock()
        mock_http_client.is_closed = False
        mock_http_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_http_client
        with pytest.raises(ShopNotFoundError):
            await client.get("/shops/999")


@pytest.mark.asyncio
async def test_get_400_maps_to_validation_error(client: HTTPClient) -> None:
    mock_response = make_response(400, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid"}})
    with patch.object(client, "_get_client") as mock_get:
        mock_http_client = AsyncMock()
        mock_http_client.is_closed = False
        mock_http_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_http_client
        with pytest.raises(ValidationError):
            await client.get("/shops")


@pytest.mark.asyncio
async def test_retry_on_timeout(client: HTTPClient) -> None:
    success_response = make_response(200, {"success": True, "data": []})
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(side_effect=[httpx.TimeoutException("timeout"), success_response])
    with patch.object(client, "_get_client", return_value=mock_http_client):
        result = await client.get("/shops")
        assert result == {"success": True, "data": []}
        assert mock_http_client.request.call_count == 2


@pytest.mark.asyncio
async def test_retry_on_connection_error(client: HTTPClient) -> None:
    success_response = make_response(200, {"success": True, "data": []})
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(side_effect=[httpx.ConnectError("conn error"), success_response])
    with patch.object(client, "_get_client", return_value=mock_http_client):
        result = await client.get("/shops")
        assert result == {"success": True, "data": []}


@pytest.mark.asyncio
async def test_retry_exhausted_timeout(client: HTTPClient) -> None:
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    with patch.object(client, "_get_client", return_value=mock_http_client):
        with pytest.raises(GatewayTimeoutError):
            await client.get("/shops")


@pytest.mark.asyncio
async def test_retry_exhausted_connection_error(client: HTTPClient) -> None:
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(side_effect=httpx.ConnectError("conn error"))
    with patch.object(client, "_get_client", return_value=mock_http_client):
        with pytest.raises(GatewayConnectionError):
            await client.get("/shops")


@pytest.mark.asyncio
async def test_no_retry_on_4xx(client: HTTPClient) -> None:
    mock_response = make_response(400, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid"}})
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(return_value=mock_response)
    with patch.object(client, "_get_client", return_value=mock_http_client):
        with pytest.raises(ValidationError):
            await client.get("/shops")
        assert mock_http_client.request.call_count == 1


@pytest.mark.asyncio
async def test_post_success(client: HTTPClient) -> None:
    mock_response = make_response(200, {"success": True, "data": {}})
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(return_value=mock_response)
    with patch.object(client, "_get_client", return_value=mock_http_client):
        result = await client.post("/test", json={"key": "value"})
        assert result == {"success": True, "data": {}}


@pytest.mark.asyncio
async def test_patch_success(client: HTTPClient) -> None:
    mock_response = make_response(200, {"success": True, "data": {}})
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(return_value=mock_response)
    with patch.object(client, "_get_client", return_value=mock_http_client):
        result = await client.patch("/test", json={"key": "value"})
        assert result == {"success": True, "data": {}}


@pytest.mark.asyncio
async def test_backoff_calculation(client: HTTPClient) -> None:
    delay = client._calculate_backoff(0)
    assert delay >= 0
    assert delay <= client._config.retry_backoff_max


@pytest.mark.asyncio
async def test_retry_on_5xx(client: HTTPClient) -> None:
    success_response = make_response(200, {"success": True, "data": []})
    server_error = make_response(500, {"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Error"}})
    mock_http_client = AsyncMock()
    mock_http_client.is_closed = False
    mock_http_client.request = AsyncMock(side_effect=[server_error, success_response])
    with patch.object(client, "_get_client", return_value=mock_http_client):
        result = await client.get("/shops")
        assert result == {"success": True, "data": []}


@pytest.mark.asyncio
async def test_close_when_client_none(client: HTTPClient) -> None:
    await client.close()
    assert client._client is None


@pytest.mark.asyncio
async def test_async_context_manager(config: GatewayConfig) -> None:
    async with HTTPClient(config) as c:
        assert c is not None
    assert c._client is None or c._client.is_closed