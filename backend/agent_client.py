from __future__ import annotations

import json
from typing import Any, AsyncIterator, Protocol, runtime_checkable

import httpx


@runtime_checkable
class AgentClient(Protocol):
    async def health(self) -> dict[str, Any]: ...

    async def create_run(
        self,
        user_input: str,
        *,
        instructions: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
        local_images: list[str] | None = None,
        output_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def get_run(self, run_id: str) -> dict[str, Any]: ...

    async def stop_run(self, run_id: str) -> dict[str, Any]: ...

    def stream_run_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]: ...


class HttpAgentClient:
    """Provider-neutral client for the internal Agent run API."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str = "",
        request_timeout_seconds: float = 3600,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.request_timeout_seconds = request_timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def create_run(
        self,
        user_input: str,
        *,
        instructions: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
        local_images: list[str] | None = None,
        output_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"input": user_input}
        optional = {
            "instructions": instructions,
            "conversation_history": conversation_history,
            "session_id": session_id,
            "local_images": local_images,
            "output_schema": output_schema,
        }
        body.update({key: value for key, value in optional.items() if value is not None})
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/v1/runs",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def get_run(self, run_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.base_url}/v1/runs/{run_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def stop_run(self, run_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/v1/runs/{run_id}/stop",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def stream_run_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        timeout = httpx.Timeout(self.request_timeout_seconds, connect=20)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "GET",
                f"{self.base_url}/v1/runs/{run_id}/events",
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        yield {"event": "raw", "data": payload}
