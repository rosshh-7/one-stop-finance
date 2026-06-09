from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import AppException, app_exception_handler, http_exception_handler, unhandled_exception_handler
from app.redis import close_redis, get_redis

# Feature routers
from app.features.auth.router import router as auth_router
from app.features.billing.router import router as billing_router
from app.features.public.router import router as public_router
from app.features.themes.router import router as themes_router
from app.features.options.router import router as options_router
from app.features.insiders.router import router as insiders_router
from app.features.sentiment.router import router as sentiment_router
from app.features.trend.router import router as trend_router
from app.features.search.router import router as search_router
from app.features.realtime.router import router as realtime_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_redis()
    yield
    # Shutdown
    await close_redis()


app = FastAPI(
    title="One Stop Finance API",
    version="0.1.0",
    description="Real-time financial intelligence platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
_cors_origins = list({
    settings.frontend_url,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
})
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Register all routers
for router in [
    public_router,
    auth_router,
    billing_router,
    themes_router,
    options_router,
    insiders_router,
    sentiment_router,
    trend_router,
    search_router,
]:
    app.include_router(router, prefix=API_PREFIX)

# WebSocket (no prefix — connects at /ws/v1/connect)
app.include_router(realtime_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
