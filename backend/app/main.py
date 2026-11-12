import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.limiter import limiter
from app.middleware.error_handler import (
    auth_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import (
    ai_sessions,
    analytics,
    auth,
    buyers,
    catalog,
    categories,
    chat,
    collections,
    dashboard,
    governance,
    imports,
    marketplace_scoring,
    merchants,
    notifications,
    orders,
    products,
    public_chat,
    seo,
    stores,
    uploads,
    user_settings,
    webhooks,
    widget,
)
from app.services import webhook_service
from app.services.auth_service import AuthError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_service.log_whatsapp_configuration()
    yield


app = FastAPI(
    title="Social Selling Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter

# Centralized error handlers: consistent JSON error shape for auth, HTTP,
# validation and any unhandled exception (no stack traces leaked to clients).
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(AuthError, auth_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Middleware order (outermost first in the stack): CORS wraps request logging
# which wraps the rate limiter. Default limits therefore apply to every route.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        settings.frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(chat.router)
app.include_router(orders.router)
app.include_router(analytics.router)
app.include_router(products.router)
app.include_router(imports.router)
app.include_router(widget.router)
app.include_router(public_chat.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)
app.include_router(user_settings.router)
app.include_router(uploads.router)
app.include_router(notifications.router)
app.include_router(merchants.router)
app.include_router(stores.router)
app.include_router(buyers.router)
app.include_router(catalog.router)
app.include_router(collections.router)
app.include_router(seo.router)
app.include_router(seo.public_router)
app.include_router(marketplace_scoring.router)
app.include_router(ai_sessions.router)
app.include_router(governance.router)


@app.get("/widget.js")
async def serve_widget_js():
    widget_path = Path(__file__).parent.parent.parent / "frontend" / "public" / "widget.js"
    if widget_path.exists():
        return FileResponse(str(widget_path), media_type="application/javascript")
    return {"error": "widget.js not found"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
