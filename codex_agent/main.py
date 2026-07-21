from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hmac
import json
from typing import Annotated, Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from .config import Settings
from .models import AgentRun, CreateRunRequest, CreateRunResponse
from .runtime import CodexRuntime


settings = Settings.from_env()
runtime = CodexRuntime(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await runtime.start()
    try:
        yield
    finally:
        await runtime.close()


app = FastAPI(title="EIA Codex Agent", version="0.1.0", lifespan=lifespan)


async def require_api_key(authorization: Annotated[str | None, Header()] = None) -> None:
    if not settings.api_key:
        return
    expected = f"Bearer {settings.api_key}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid agent API key")


async def get_run_or_404(run_id: str) -> AgentRun:
    try:
        return await runtime.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.get("/health")
async def health() -> dict[str, Any]:
    return runtime.health()


@app.get("/api/ready")
async def ready() -> JSONResponse:
    status = runtime.health()
    if status["status"] != "ok":
        return JSONResponse(status_code=503, content=status)
    return JSONResponse(content=status)


@app.post("/v1/runs", response_model=CreateRunResponse, status_code=202)
async def create_run(
    request: CreateRunRequest,
    _: None = Depends(require_api_key),
) -> CreateRunResponse:
    try:
        run = await runtime.create(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateRunResponse(run_id=run.run_id, status=run.status)


@app.get("/v1/runs/{run_id}")
async def get_run(run_id: str, _: None = Depends(require_api_key)) -> dict[str, Any]:
    run = await get_run_or_404(run_id)
    return run.model_dump()


@app.post("/v1/runs/{run_id}/stop")
async def stop_run(run_id: str, _: None = Depends(require_api_key)) -> dict[str, Any]:
    try:
        run = await runtime.stop(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return {"run_id": run.run_id, "status": run.status, "stop_requested": run.stop_requested}


@app.get("/v1/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    _: None = Depends(require_api_key),
    after: int = Query(default=0, ge=0),
) -> StreamingResponse:
    await get_run_or_404(run_id)

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in runtime.events(run_id, after=after):
                if event is None:
                    yield ": keepalive\n\n"
                    continue
                event_name = str(event.get("event") or "message")
                yield f"id: {event['id']}\nevent: {event_name}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
