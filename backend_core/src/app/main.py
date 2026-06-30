from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.database import dispose_database
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.openapi import OPENAPI_TAGS
from app.core.router import router as health_router
from app.mod_agenda.router import router as agenda_router
from app.mod_cadastro.router import router as cadastro_router
from app.mod_dashboard.router import router as dashboard_router
from app.mod_demandas.router import router as demandas_router
from app.mod_metas.router import router as metas_router
from app.mod_territorio.router import router as territorio_router
from app.tenants.public_router import router as public_router
from app.tenants.router import router as tenants_router

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_database()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "X-Campaign-ID",
        "X-Request-ID",
        "X-Webhook-Signature",
    ],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware)
install_exception_handlers(app)

app.include_router(health_router)
app.include_router(public_router)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(tenants_router, prefix=settings.api_v1_prefix)
app.include_router(cadastro_router, prefix=settings.api_v1_prefix)
app.include_router(territorio_router, prefix=settings.api_v1_prefix)
app.include_router(metas_router, prefix=settings.api_v1_prefix)
app.include_router(agenda_router, prefix=settings.api_v1_prefix)
app.include_router(demandas_router, prefix=settings.api_v1_prefix)
app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
