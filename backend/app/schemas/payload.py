"""
Pydantic v2 Request & Response Data Transfer Objects (Schemas)
Enforces strict payload validation, telemetry data formats, and documentation examples.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AnalyzeRequest(BaseModel):
    """
    Inbound request model containing user query in Persian or English.
    """
    user_query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="سوال تحلیلی کاربر به زبان طبیعی فارسی یا انگلیسی",
    )

    @field_validator("user_query")
    @classmethod
    def validate_user_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("پرسش کاربر نمی‌تواند خالی یا صرفاً شامل فاصله باشد.")
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_query": "پرفروش‌ترین دسته‌بندی محصولات در ماه گذشته کدام بوده و چه میزان درآمد ایجاد کرده است؟"
            }
        }
    )


class CorrectionAttempt(BaseModel):
    """
    Detailed telemetry on each self-correction attempt executed by the agent.
    """
    attempt_number: int = Field(..., description="شماره تلاش خود-اصلاحی")
    failed_sql: str = Field(..., description="کوئری دارای خطای سینتکس یا متادیتا")
    error_message: str = Field(..., description="پیغام خطای دریافتی از انجین پستگرس")


class AnalyzeResponse(BaseModel):
    """
    Outbound response model providing comprehensive executive answer, generated SQL, and telemetry.
    """
    answer: str = Field(
        ...,
        description="پاسخ نهایی به زبان طبیعی و روان فارسی برای نمایش به مدیر در تلگرام",
    )
    sql_query: str = Field(
        ...,
        description="کوئری نهایی و معتبر SQL که روی دیتابیس اجرا شده است",
    )
    execution_time_ms: int = Field(
        ...,
        description="مجموع زمان پردازش درخواست بر حسب میلی‌ثانیه",
    )
    retries_count: int = Field(
        default=0,
        description="تعداد دفعاتی که حلقه خود-اصلاح‌گر خطای SQL را برطرف کرده است",
    )
    row_count: int = Field(
        default=0,
        description="تعداد سطرهای بازگشتی از دیتابیس",
    )
    raw_data_preview: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="پیش‌نمایش حداکثر ۱۰ سطر اول داده‌های خام دیتابیس برای دیباگ و مانیتورینگ",
    )
    correction_history: List[CorrectionAttempt] = Field(
        default_factory=list,
        description="تاریخچه خطاها و اصلاحات خودکار هوش مصنوعی در صورت وقوع خطا",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "پرفروش‌ترین دسته‌بندی در ماه گذشته «الکترونیک و دیجیتال» با مجموع فروش ۴۲,۵۰۰,۰۰۰,۰۰۰ تومان بوده است.",
                "sql_query": "SELECT p.category, SUM(oi.line_total) AS total_revenue FROM orders o JOIN order_items oi ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id WHERE o.status = 'completed' AND o.order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND o.order_date < DATE_TRUNC('month', CURRENT_DATE) GROUP BY p.category ORDER BY total_revenue DESC LIMIT 1;",
                "execution_time_ms": 1420,
                "retries_count": 0,
                "row_count": 1,
                "raw_data_preview": [
                    {"category": "الکترونیک و دیجیتال", "total_revenue": 42500000000.0}
                ],
                "correction_history": [],
            }
        }
    )


class HealthResponse(BaseModel):
    """
    System diagnostic and connectivity health status.
    """
    status: str = Field(..., description="وضعیت کلی سرویس (ok یا degraded)")
    app_name: str = Field(..., description="نام سرویس")
    version: str = Field(..., description="نسخه نرم‌افزار")
    database_admin_connected: bool = Field(..., description="اتصال سشن ادمین به دیتابیس")
    database_readonly_connected: bool = Field(..., description="اتصال سشن امنیتی هوش مصنوعی به دیتابیس")
    llm_provider: str = Field(..., description="سرویس‌دهنده مدل زبانی فعال")
    llm_model: str = Field(..., description="نام مدل هوش مصنوعی در حال استفاده")


class ErrorResponse(BaseModel):
    """
    Standardized error payload returned upon failed processing.
    """
    error_code: str = Field(..., description="کد خطای استاندارد سیستم")
    message: str = Field(..., description="پیغام خطای توضیحی و قابل فهم برای کاربر")
    details: Optional[Any] = Field(default=None, description="اطلاعات تکمیلی یا تاریخچه خطاها جهت عیب‌یابی")
