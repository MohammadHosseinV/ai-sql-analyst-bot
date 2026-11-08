"""
Pure REST HTTP Client for Multi-Provider LLMs (Google Gemini & OpenAI Compatible)
Zero external agent framework dependencies (strictly no LangChain/LlamaIndex).
"""

import re
import logging
from typing import Optional
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class LLMConfigurationError(Exception):
    """Raised when LLM API keys or required configurations are missing or placeholder."""
    pass


class LLMConnectionError(Exception):
    """Raised when network transport, timeout, or provider 5xx outages occur."""
    pass


class LLMResponseError(Exception):
    """Raised when LLM returns an unexpected payload structure or empty response."""
    pass


# =============================================================================
# SQL CLEANING UTILITY
# =============================================================================

def clean_sql_output(raw_llm_text: str) -> str:
    """
    Deterministically cleans raw LLM output:
    1. Removes markdown code block wrappers (```sql ... ```).
    2. Strips leading or trailing non-SQL chatter.
    3. Locates starting keyword (SELECT or WITH).
    4. Trims trailing semicolons and extraneous whitespaces.
    """
    if not raw_llm_text:
        return ""

    text = raw_llm_text.strip()

    # Remove markdown code blocks if present
    code_block_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # Match starting from first SELECT or WITH keyword
    query_start_match = re.search(r"\b(SELECT|WITH)\b", text, re.IGNORECASE)
    if query_start_match:
        text = text[query_start_match.start():].strip()

    # Remove trailing semicolon
    if text.endswith(";"):
        text = text[:-1].strip()

    return text


# =============================================================================
# LLM CLIENT CLASS
# =============================================================================

class LLMClient:
    """
    High-performance asynchronous and synchronous HTTP client for LLM API invocation.
    Supports official Google Gemini REST API and standard OpenAI-compatible endpoints.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.timeout = float(settings.LLM_TIMEOUT_SECONDS)
        self.openai_base_url = settings.OPENAI_BASE_URL.rstrip("/")

        self._validate_configuration()

    def _validate_configuration(self):
        """
        Ensures the client has a valid API key before attempting requests.
        """
        invalid_keys = {"", "your_llm_api_key_here", "your_api_key_here"}
        if not self.api_key or self.api_key.strip() in invalid_keys:
            logger.warning("LLM API key is not configured or holds a placeholder value.")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Executes a synchronous HTTP request to the selected LLM provider.
        """
        invalid_keys = {"", "your_llm_api_key_here", "your_api_key_here"}
        if not self.api_key or self.api_key.strip() in invalid_keys:
            raise LLMConfigurationError(
                "کلید دسترسی هوش مصنوعی (LLM_API_KEY) در فایل تنظیمات .env ثبت نشده است. "
                "لطفاً کلید معتبر Google Gemini یا OpenAI را در .env وارد نمایید."
            )

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE

        if self.provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt, temp)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, temp)
        else:
            raise LLMConfigurationError(
                f"سرویس‌دهنده هوش مصنوعی نامعتبر است: '{self.provider}'. مقادیر معتبر 'gemini' یا 'openai' هستند."
            )

    def _call_gemini(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """
        Invokes Google Generative Language API (v1beta generateContent).
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "generationConfig": {
                "temperature": temperature,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error("Gemini API error (Status %s): %s", response.status_code, response.text)
                raise LLMConnectionError(
                    f"خطا در ارتباط با سرویس Google Gemini (کد وضعیت: {response.status_code})."
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMResponseError("مدل Gemini پاسخی برای درخواست بازنگرداند.")

            first_candidate = candidates[0]
            content = first_candidate.get("content", {})
            parts = content.get("parts", [])
            if not parts or "text" not in parts[0]:
                raise LLMResponseError("ساختار پاسخ بازگشتی از Gemini فاقد متن معتبر است.")

            return parts[0]["text"].strip()

        except httpx.TimeoutException as te:
            logger.error("Gemini API call timed out: %s", te)
            raise LLMConnectionError("پاسخ مدل هوش مصنوعی در مهلت مقرر (Timeout) دریافت نشد.") from te
        except httpx.RequestError as re:
            logger.error("Gemini network request error: %s", re)
            raise LLMConnectionError(f"خطای شبکه در ارتباط با Gemini: {str(re)}") from re

    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """
        Invokes OpenAI-compatible Chat Completions REST endpoint.
        """
        url = f"{self.openai_base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error("OpenAI API error (Status %s): %s", response.status_code, response.text)
                raise LLMConnectionError(
                    f"خطا در ارتباط با سرویس OpenAI (کد وضعیت: {response.status_code})."
                )

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMResponseError("پاسخی از سرویس OpenAI دریافت نشد.")

            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content.strip()

        except httpx.TimeoutException as te:
            logger.error("OpenAI API call timed out: %s", te)
            raise LLMConnectionError("پاسخ سرویس هوش مصنوعی OpenAI در مهلت مقرر دریافت نشد.") from te
        except httpx.RequestError as re:
            logger.error("OpenAI network request error: %s", re)
            raise LLMConnectionError(f"خطای شبکه در ارتباط با OpenAI: {str(re)}") from re
