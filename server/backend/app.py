import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/generate")
async def generate(request: GenerateRequest) -> dict:
    payload = {
        "model": request.model or os.getenv("OLLAMA_MODEL", "deepseek-r1"),
        "prompt": request.prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama request failed: {exc}") from exc

    return {
        "model": data.get("model"),
        "response": data.get("response"),
        "total_duration": data.get("total_duration"),
    }
