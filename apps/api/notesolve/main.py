from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from notesolve.api.middleware import SecurityHeadersMiddleware
from notesolve.api.routes import router
from notesolve.application.recovery import mark_interrupted_jobs_failed
from notesolve.config import get_settings
from notesolve.infrastructure.db import SessionLocal

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    session_factory = app.state.session_factory
    with session_factory() as session:
        mark_interrupted_jobs_failed(session)
    yield


app = FastAPI(
    title="NoteSolve API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.state.session_factory = SessionLocal
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")
