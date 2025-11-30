from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.logs import router as logs_router
from .core.config import settings

app = FastAPI(title="Xray Logs API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs_router)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}
