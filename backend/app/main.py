"""
FastAPI Application Entry Point
Configures structured logging, CORS middleware, global exception handlers,
and system lifecycle events.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import check_database_health
from app.schemas.payload import HealthResponse
from app.api.v1.router import router as v1_router

# =============================================================================
# STRUCTURED LOGGING SETUP
# =============================================================================

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("autonomous_analyst")

# =============================================================================
# APPLICATION FACTORY & MIDDLEWARE
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "سازمان‌یابی معماری تمیز برای ایجنت خودترمیم‌شونده تحلیل داده (Structured RAG & Text-to-SQL). "
        "این سرویس پرسش‌های فارسی را دریافت نموده، به کوئری‌های بهینه PostgreSQL تبدیل کرده و با اتصال به کاربر "
        "امنیت‌یافته llm_reader اجرا می‌کند."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register v1 API Router
app.include_router(v1_router)


# =============================================================================
# GLOBAL EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches all uncaught exceptions, preventing internal stack trace leaks to consumers.
    """
    logger.exception("Global Unhandled Exception on path %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "یک خطای سیستمی در سرور رخ داده است. لطفاً با راهبر سیستم تماس بگیرید.",
            "details": str(exc),
        },
    )


# =============================================================================
# BASE & HEALTH DIAGNOSTIC ENDPOINTS
# =============================================================================

@app.get(
    "/",
    tags=["General"],
    summary="اطلاعات پایه سرویس",
)
def root():
    """
    Root informational endpoint providing quick navigation links.
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "health_check": "/health",
        "api_v1_analyze": "/api/v1/analyze",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["General"],
    summary="پایش سلامت سرویس و دیتابیس",
)
def health_check():
    """
    Diagnostic probe returning database pool connectivity and LLM configurations.
    """
    db_health = check_database_health()
    all_healthy = db_health["admin_connected"] and db_health["readonly_connected"]

    return HealthResponse(
        status="ok" if all_healthy else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        database_admin_connected=db_health["admin_connected"],
        database_readonly_connected=db_health["readonly_connected"],
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
    )
