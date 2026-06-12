import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.exceptions import AppError
from app.core.ratelimit import limiter
from app.database import engine
from app.routers import auth, conversations, directives, health, reports, users
from app.services.llm.client import OpenRouterProvider

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # One shared LLM provider (and underlying HTTP client) for the app lifetime
    app.state.llm_provider = OpenRouterProvider()
    yield
    await app.state.llm_provider.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="SalesLoop AI",
        description="Plateforme d'agents conversationnels pour équipes commerciales",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(conversations.router)
    app.include_router(directives.router)
    app.include_router(reports.router)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Trop de tentatives, réessaie dans quelques instants."},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces to clients; details go to the logs only
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})

    return app


app = create_app()
