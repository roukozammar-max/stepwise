"""Minimal HTTP API around the verifier.

    uvicorn api:app --reload
    open http://127.0.0.1:8000/docs   (interactive docs, try requests there)

Endpoints:
    POST /verify      {"lines": ["(x+1)^2", "= x^2 + 2x + 1"]}
    POST /hint-check  {"hint": "Try $\\cos(x^2) \\cdot 2x$", "answer": "2x\\cos(x^2)"}
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from verifier import check_derivation, hint_reveals_answer, start_workers

MAX_LINES = 50
MAX_LINE_LENGTH = 500

# Web pages allowed to call this API from a browser (CORS). Set ALLOWED_ORIGINS
# to a comma-separated list, e.g. "https://stepwise.vercel.app" in production.
DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_workers()  # pay the one-time warm-up when the server boots, not on the first request
    yield


app = FastAPI(title="Stepwise verifier", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class VerifyRequest(BaseModel):
    lines: list[str] = Field(..., min_length=1, max_length=MAX_LINES,
                             examples=[["\\frac{d}{dx}\\sin(x^2)", "= \\cos(x^2)"]])


class HintCheckRequest(BaseModel):
    hint: str = Field(..., max_length=2000)
    answer: str = Field(..., max_length=MAX_LINE_LENGTH)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/verify")
def verify(req: VerifyRequest):
    # Plain "def" (not "async def"): FastAPI runs it in a thread pool, so a
    # slow check doesn't block other requests.
    lines = [line[:MAX_LINE_LENGTH] for line in req.lines if line.strip()]
    return {"steps": [r.to_dict() for r in check_derivation(lines)]}


@app.post("/hint-check")
def hint_check(req: HintCheckRequest):
    return {"reveals_answer": hint_reveals_answer(req.hint, req.answer)}
