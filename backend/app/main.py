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
from app.routers import auth, conversations, directives, health, reports, training, users
from app.services.llm.client import OpenRouterProvider
from app.services.rag.embeddings import OpenAICompatibleEmbeddingProvider

logger = logging.getLogger(__name__)

DESCRIPTION = """
API de **SalesLoop AI** — agents conversationnels IA pour équipes commerciales.

Authentification par **JWT Bearer** : crée un espace via `POST /auth/register`,
puis connecte-toi via `POST /auth/login` et clique sur **Authorize** avec le
token renvoyé. Toutes les ressources sont isolées par tenant.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Inscription entreprise, connexion, création de comptes."},
    {"name": "users", "description": "Profil courant et gestion des utilisateurs (scopé rôle)."},
    {"name": "conversations", "description": "Sessions avec les agents Collector et Trainer."},
    {"name": "directives", "description": "Consignes du management injectées dans les agents."},
    {"name": "reports", "description": "Rapports périodiques générés par LLM (manager+)."},
    {
        "name": "training",
        "description": "Contenus de formation (RAG) : upload texte/PDF, indexation.",
    },
    {"name": "health", "description": "Disponibilité du service et de la base."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Shared providers (and underlying HTTP clients) for the app lifetime
    app.state.llm_provider = OpenRouterProvider()
    app.state.embedding_provider = OpenAICompatibleEmbeddingProvider()
    yield
    await app.state.llm_provider.aclose()
    await app.state.embedding_provider.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="SalesLoop AI",
        description=DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=TAGS_METADATA,
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
    app.include_router(training.router)

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
