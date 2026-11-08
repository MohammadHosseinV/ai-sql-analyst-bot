"""
FastAPI v1 Routing Module
Exposes endpoints for analytical query processing and schema knowledge base inspection.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.core.database import get_readonly_db
from app.schemas.payload import (
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
)
from app.services.agent_service import (
    AutonomousAnalystAgent,
    SQLMaxRetriesExceededError,
)
from app.services.llm_client import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMResponseError,
)
from app.services.sql_executor import UnsafeSQLError
from app.services.prompts import DATABASE_SCHEMA_DDL

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Autonomous Data Analyst"],
)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "دستور SQL ناامن یا ورودی نامعتبر"},
        422: {"model": ErrorResponse, "description": "عدم موفقیت در حل خطا پس از حداکثر تلاش‌ها"},
        503: {"model": ErrorResponse, "description": "عدم دسترسی به پایگاه داده یا سرویس هوش مصنوعی"},
    },
    summary="تحلیل سوال کسب‌وکاری با مدل زبانی و استخراج داده از PostgreSQL",
    description="سوال به زبان طبیعی را دریافت کرده، کوئری SQL تولید و اعتبارسنجی می‌کند، در صورت خطا خود را اصلاح کرده و پاسخ مدیریتی فارسی بازمی‌گرداند.",
)
def analyze_query(
    request: AnalyzeRequest,
    readonly_db: Session = Depends(get_readonly_db),
) -> AnalyzeResponse:
    """
    Main endpoint executing the 3-Stage Structured RAG Agent workflow.
    """
    agent = AutonomousAnalystAgent()

    try:
        response = agent.analyze(
            user_query=request.user_query,
            readonly_db=readonly_db,
        )
        return response

    except (LLMConfigurationError, LLMConnectionError) as llm_err:
        logger.error("LLM Provider Unavailable: %s", llm_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "LLM_SERVICE_UNAVAILABLE",
                "message": "در حال حاضر ارتباط با موتور هوش مصنوعی برقرار نیست. لطفاً تنظیمات API Key را بررسی کرده یا چند لحظه دیگر تلاش کنید.",
                "details": str(llm_err),
            },
        )

    except SQLMaxRetriesExceededError as retries_err:
        logger.warning("Agent exceeded retry limits: %s", retries_err)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "SQL_MAX_RETRIES_EXCEEDED",
                "message": "سیستم پس از چندین تلاش خودکار موفق به تولید کوئری معتبر برای این سوال نشد. لطفاً سوال خود را واضح‌تر مطرح کنید.",
                "details": [attempt.model_dump() for attempt in retries_err.history],
            },
        )

    except UnsafeSQLError as unsafe_err:
        logger.warning("Unsafe SQL blocked by firewall: %s", unsafe_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "UNSAFE_SQL_DETECTED",
                "message": str(unsafe_err),
            },
        )

    except OperationalError as db_op_err:
        logger.error("PostgreSQL Connection Failure: %s", db_op_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "خطا در برقراری ارتباط با پایگاه داده PostgreSQL.",
                "details": str(db_op_err),
            },
        )

    except LLMResponseError as resp_err:
        logger.error("LLM Malformed Response: %s", resp_err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": "LLM_MALFORMED_RESPONSE",
                "message": "پاسخ دریافتی از سرور هوش مصنوعی نامعتبر بود.",
                "details": str(resp_err),
            },
        )

    except Exception as general_err:
        logger.exception("Unexpected error during analysis: %s", general_err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "خطای پیش‌بینی‌نشده‌ای در سرور رخ داده است.",
                "details": str(general_err),
            },
        )


@router.get(
    "/schema",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="مشاهده ساختار متادیتا و مقادیر مجاز دامنه دیتابیس",
    description="اطلاعات DDL جداول، نگاشت‌های فارسی دسته‌بندی‌ها، شهرها و وضعیت سفارش‌ها را برای عیب‌یابی بازمی‌گرداند.",
)
def get_schema_metadata() -> Dict[str, Any]:
    """
    Returns active schema overview and Persian domain dictionaries.
    """
    return {
        "database_name": "ecommerce_analytics",
        "supported_tables": ["customers", "products", "orders", "order_items"],
        "persian_categories": [
            "الکترونیک و دیجیتال",
            "لوازم خانگی و آشپزخانه",
            "پوشاک و مد",
            "آرایشی و بهداشتی",
            "کتاب، فرهنگ و ورزش",
        ],
        "persian_cities": [
            "تهران", "مشهد", "اصفهان", "شیراز", "تبریز",
            "کرج", "اهواز", "رشت", "کرمان", "یزد", "قم",
        ],
        "order_statuses": {
            "completed": "تکمیل‌شده (مبنای درآمد قطعی)",
            "processing": "در حال پردازش",
            "cancelled": "لغوشده",
            "returned": "مرجوعی",
        },
        "schema_ddl": DATABASE_SCHEMA_DDL.strip(),
    }
