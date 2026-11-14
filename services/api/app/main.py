import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import errors
from app.auth import TokenVerifier
from app.config import Settings, settings
from app.db import make_engine, make_sessionmaker
from app.embeddings import Embedder, VoyageEmbedder
from app.realtime import Hub, listen
from app.routes import cabinet, households, realtime, recipes, shopping_lists

# The one place domain errors become HTTP status codes.
ERROR_STATUS: dict[type[errors.DomainError], int] = {
    errors.NotInHousehold: 403,
    errors.PermissionDenied: 403,
    errors.NotFound: 404,
    errors.InviteInvalid: 404,
    errors.AlreadyInHousehold: 409,
    errors.Conflict: 409,
    errors.LimitReached: 409,
    errors.IdempotencyKeyReused: 422,
    errors.Unavailable: 503,
}


async def handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, errors.DomainError)
    status_code = ERROR_STATUS.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={"code": exc.code, "detail": exc.message})


def default_embedder(app_settings: Settings) -> Embedder | None:
    key = app_settings.voyage_api_key
    if key is None:
        return None  # search is switched off; browsing still works
    # Someone is waiting on a search: one quick retry, then a clear "unavailable".
    return VoyageEmbedder(
        key.get_secret_value(), app_settings.embedding_model, retries=1, backoff=1.0
    )


def create_app(
    app_settings: Settings | None = None,
    token_verifier: TokenVerifier | None = None,
    embedder: Embedder | None = None,
) -> FastAPI:
    """Build the app. Tests pass their own settings, a verifier that trusts a test key,
    and a fake embedder."""
    app_settings = app_settings or settings
    # Creating an engine doesn't connect yet; the first query does.
    engine = make_engine(app_settings.database_url)

    hub = Hub()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # One background task per API instance holds a Postgres LISTEN connection and
        # hands change notices to this instance's WebSockets.
        listener = asyncio.create_task(listen(app_settings.database_url, hub))
        yield
        listener.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener
        await engine.dispose()  # close pooled connections on shutdown

    app = FastAPI(title="Sweep API", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.hub = hub
    app.state.token_verifier = token_verifier or TokenVerifier.from_settings(
        app_settings.auth_issuers
    )
    app.state.embedder = embedder or default_embedder(app_settings)

    # Browsers block cross-origin requests unless the server allows them.
    # Native iOS/Android apps aren't subject to CORS; this is for the web build.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(errors.DomainError, handle_domain_error)
    app.include_router(households.router)
    app.include_router(shopping_lists.router)
    app.include_router(cabinet.router)
    app.include_router(recipes.router)
    app.include_router(realtime.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
