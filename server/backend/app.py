import json
import os

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

app = FastAPI(title="Ollama Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"]
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str | None = None


THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"


def strip_think_stream(text: str, state: dict) -> str:
    buffer = state.get("buffer", "") + text
    output = ""

    while True:
        start = buffer.find(THINK_OPEN)
        if start == -1:
            break
        end = buffer.find(THINK_CLOSE, start + len(THINK_OPEN))
        if end == -1:
            output += buffer[:start]
            buffer = buffer[start:]
            state["buffer"] = buffer
            return output
        output += buffer[:start]
        buffer = buffer[end + len(THINK_CLOSE) :]

    tail_len = max(len(THINK_OPEN), len(THINK_CLOSE)) - 1
    if len(buffer) > tail_len:
        output += buffer[:-tail_len]
        buffer = buffer[-tail_len:]

    state["buffer"] = buffer
    return output


def finalize_strip_think(state: dict) -> str:
    buffer = state.get("buffer", "")
    state["buffer"] = ""
    return buffer.replace(THINK_OPEN, "").replace(THINK_CLOSE, "")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/generate")
async def generate(request: GenerateRequest, stream: bool = Query(True)) -> StreamingResponse | dict:
    payload = {
        "model": request.model or os.getenv("OLLAMA_MODEL", "deepseek-r1"),
        "prompt": request.prompt,
        "stream": stream,
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=None,
            )
            response.raise_for_status()
            if not stream:
                data = response.json()
                cleaned = data.get("response", "")
                cleaned = cleaned.replace(THINK_OPEN, "").replace(THINK_CLOSE, "")
                return {
                    "model": data.get("model"),
                    "response": cleaned,
                    "total_duration": data.get("total_duration"),
                }

            async def stream_body():
                state: dict = {}
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        payload_line = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunk = payload_line.get("response", "")
                    if chunk:
                        cleaned_chunk = strip_think_stream(chunk, state)
                        if cleaned_chunk:
                            yield cleaned_chunk
                    if payload_line.get("done"):
                        tail = finalize_strip_think(state)
                        if tail:
                            yield tail
                        break

            return StreamingResponse(stream_body(), media_type="text/plain; charset=utf-8")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama request failed: {exc}") from exc
