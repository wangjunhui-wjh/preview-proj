from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .config import settings


class HermesClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.hermes_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.hermes_api_key
        self.model = settings.hermes_model

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
        # Hermes does not accept these Codex-specific request fields; keeping
        # them in the signature lets it satisfy the provider-neutral contract.
        del local_images, output_schema
        body: dict[str, Any] = {"input": user_input}
        if instructions:
            body["instructions"] = instructions
        if conversation_history:
            body["conversation_history"] = conversation_history
        if session_id:
            body["session_id"] = session_id
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
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
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
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                        if not payload:
                            continue
                        try:
                            yield json.loads(payload)
                        except json.JSONDecodeError:
                            yield {"event": "raw", "data": payload}


hermes_client = HermesClient()
