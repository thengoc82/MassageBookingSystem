import asyncio
import logging
from typing import Any

import httpx

from gateway.config import GatewayConfig
from gateway.errors import (
    ChatbotError,
    ChatbotErrorCode,
    GatewayConnectionError,
    GatewayTimeoutError,
    map_flask_error,
)

logger = logging.getLogger(__name__)


class HTTPClient:
    """Async HTTP client with timeout, retry, and error mapping."""

    def __init__(self, config: GatewayConfig | None = None) -> None:
        self._config = config or GatewayConfig()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._config.flask_base_url,
                timeout=httpx.Timeout(self._config.timeout_seconds),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "HTTPClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        delay = min(
            self._config.retry_backoff_factor * (2 ** attempt),
            self._config.retry_backoff_max,
        )
        return delay

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )

                if response.status_code >= 400:
                    error_data: dict[str, Any] = {}
                    try:
                        error_data = response.json()
                    except Exception as json_err:  # noqa: BLE001
                        logger.debug("Failed to parse error response: %s", json_err)

                    error_code = error_data.get("error", {}).get("code", "UNKNOWN_ERROR")
                    error_message = error_data.get("error", {}).get("message", response.text)

                    raise map_flask_error(response.status_code, error_code, error_message)

                return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "Request timeout (attempt %d/%d): %s %s",
                    attempt + 1,
                    self._config.max_retries + 1,
                    method,
                    path,
                )

            except httpx.ConnectError as e:
                last_exception = e
                logger.warning(
                    "Connection error (attempt %d/%d): %s %s",
                    attempt + 1,
                    self._config.max_retries + 1,
                    method,
                    path,
                )

            except ChatbotError as e:
                if not e.retryable or attempt >= self._config.max_retries:
                    raise
                last_exception = e
                logger.warning(
                    "Retryable error (attempt %d/%d): %s",
                    attempt + 1,
                    self._config.max_retries + 1,
                    e.message,
                )

            except Exception as e:  # noqa: BLE001
                last_exception = e
                logger.error(
                    "Unexpected error (attempt %d/%d): %s %s - %s",
                    attempt + 1,
                    self._config.max_retries + 1,
                    method,
                    path,
                    e,
                )
                break

            if attempt < self._config.max_retries:
                delay = self._calculate_backoff(attempt)
                await asyncio.sleep(delay)

        if isinstance(last_exception, httpx.TimeoutException):
            raise GatewayTimeoutError(f"Request timed out after {self._config.max_retries + 1} attempts") from last_exception
        if isinstance(last_exception, httpx.ConnectError):
            raise GatewayConnectionError(f"Connection failed after {self._config.max_retries + 1} attempts") from last_exception
        raise last_exception or ChatbotError(ChatbotErrorCode.INTERNAL_SERVER_ERROR, "Request failed")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request_with_retry("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request_with_retry("POST", path, json=json)

    async def patch(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request_with_retry("PATCH", path, json=json)


async def create_client(config: GatewayConfig | None = None) -> HTTPClient:
    """Factory to create and return an HTTP client."""
    return HTTPClient(config)