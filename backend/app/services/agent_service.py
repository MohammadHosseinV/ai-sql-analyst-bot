"""
Autonomous Analyst Agent Orchestrator Module
Coordinates 3-Stage Structured RAG workflow: SQL generation, self-correction loop,
and executive Persian synthesis.
"""

import time
import logging
from typing import List
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.payload import (
    AnalyzeResponse,
    CorrectionAttempt,
)
from app.services.prompts import (
    build_sql_generation_prompt,
    build_sql_correction_prompt,
    build_data_to_text_prompt,
)
from app.services.llm_client import LLMClient, clean_sql_output
from app.services.sql_executor import (
    SQLExecutor,
    DatabaseExecutionError,
    UnsafeSQLError,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# AGENT EXCEPTIONS
# =============================================================================

class SQLMaxRetriesExceededError(Exception):
    """
    Raised when the agent fails to produce executable SQL after exceeding MAX_SQL_RETRIES.
    """
    def __init__(self, message: str, history: List[CorrectionAttempt]):
        super().__init__(message)
        self.history = history


# =============================================================================
# AUTONOMOUS AGENT ORCHESTRATOR
# =============================================================================

class AutonomousAnalystAgent:
    """
    State-of-the-art Structured RAG Agent managing prompt assembly, LLM communication,
    SQL validation, execution, multi-turn self-correction, and Persian interpretation.
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()
        self.sql_executor = SQLExecutor()
        self.max_retries = settings.MAX_SQL_RETRIES
        self.max_result_rows = settings.MAX_RESULT_ROWS

    def analyze(self, user_query: str, readonly_db: Session) -> AnalyzeResponse:
        """
        Executes end-to-end analytical workflow for an inbound user query.
        """
        start_time = time.time()
        logger.info("Initiating analysis for query: '%s'", user_query)

        # ---------------------------------------------------------------------
        # STAGE 1: INITIAL SQL GENERATION
        # ---------------------------------------------------------------------
        gen_sys_prompt, gen_user_prompt = build_sql_generation_prompt(user_query)
        raw_sql_response = self.llm_client.generate(
            system_prompt=gen_sys_prompt,
            user_prompt=gen_user_prompt,
            temperature=0.0,
        )
        current_sql = clean_sql_output(raw_sql_response)
        logger.info("Initial SQL generated: %s", current_sql)

        # ---------------------------------------------------------------------
        # STAGE 2: EXECUTION & MULTI-TURN SELF-CORRECTION LOOP
        # ---------------------------------------------------------------------
        rows = []
        total_rows = 0
        correction_history: List[CorrectionAttempt] = []
        retries_used = 0

        for attempt in range(self.max_retries + 1):
            try:
                logger.info("Executing SQL (Attempt %d/%d): %s", attempt + 1, self.max_retries + 1, current_sql)
                rows, total_rows = self.sql_executor.execute_query(
                    db=readonly_db,
                    sql=current_sql,
                    max_rows=self.max_result_rows,
                )
                retries_used = attempt
                logger.info("SQL executed successfully. Returned %d rows.", total_rows)
                break  # Successful execution, proceed to Stage 3

            except (DatabaseExecutionError, UnsafeSQLError) as err:
                error_msg = str(err)
                logger.warning(
                    "[Self-Correction Attempt %d/%d] SQL execution failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    error_msg,
                )

                correction_history.append(
                    CorrectionAttempt(
                        attempt_number=attempt + 1,
                        failed_sql=current_sql,
                        error_message=error_msg,
                    )
                )

                # Check if retries are exhausted
                if attempt >= self.max_retries:
                    logger.error("Maximum SQL retries (%d) exceeded for query: %s", self.max_retries, user_query)
                    raise SQLMaxRetriesExceededError(
                        message=f"سیستم پس از {self.max_retries} بار تلاش متوالی موفق به اصلاح کوئری دیتابیس نشد.",
                        history=correction_history,
                    ) from err

                # Request self-correction from LLM
                corr_sys_prompt, corr_user_prompt = build_sql_correction_prompt(
                    user_query=user_query,
                    failed_sql=current_sql,
                    db_error=error_msg,
                    attempt=attempt + 1,
                )

                fixed_sql_response = self.llm_client.generate(
                    system_prompt=corr_sys_prompt,
                    user_prompt=corr_user_prompt,
                    temperature=0.0,
                )
                current_sql = clean_sql_output(fixed_sql_response)
                logger.info("Received corrected SQL candidate: %s", current_sql)

        # ---------------------------------------------------------------------
        # STAGE 3: DATA-TO-TEXT NATURAL LANGUAGE SYNTHESIS (PERSIAN)
        # ---------------------------------------------------------------------
        synth_sys_prompt, synth_user_prompt = build_data_to_text_prompt(
            user_query=user_query,
            executed_sql=current_sql,
            rows=rows,
            row_count=total_rows,
        )

        persian_answer = self.llm_client.generate(
            system_prompt=synth_sys_prompt,
            user_prompt=synth_user_prompt,
            temperature=0.2,
        )

        total_elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info("Analysis completed in %d ms with %d retries.", total_elapsed_ms, retries_used)

        return AnalyzeResponse(
            answer=persian_answer,
            sql_query=current_sql,
            execution_time_ms=total_elapsed_ms,
            retries_count=retries_used,
            row_count=total_rows,
            raw_data_preview=rows[:10],
            correction_history=correction_history,
        )
