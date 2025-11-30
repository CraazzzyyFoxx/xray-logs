from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .api.logs import router as logs_router
from .api.users import router as users_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.logs import router as logs_router
from .core.config import settings

app = FastAPI(title="Xray Logs API", version="0.2.0")


class TimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        url_path = request.url.path
        if request.query_params:
            url_path += f"?{request.query_params}"

        if request.client is not None:
            logger.info(
                f'{request.client.host}:{request.client.port} - "{request.method} {url_path}" '
                f"{response.status_code} [process time: {int(process_time * 1000)} ms]"
            )
        else:
            logger.info(
                f'Unknown - "{request.method} {request.url.path}" '
                f"{response.status_code} [process time: {int(process_time * 1000)} ms]"
            )
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimeMiddleware)

app.include_router(logs_router)
app.include_router(users_router)

app.include_router(logs_router)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}
