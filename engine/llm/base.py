"""
engine/llm/base.py — DAVE RPG Engine LLM Abstract Base Class

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Defines the LLMClient interface that all backend implementations must satisfy.
The engine only ever calls methods defined here; it does not import concrete
implementations directly. This makes backend replacement a configuration change,
not a code change.

Backend implementations live in sibling modules:
    engine/llm/claude.py   — Anthropic Claude via the anthropic SDK
    engine/llm/ollama.py   — Local model via Ollama HTTP API

To add a new backend, subclass LLMClient, implement call(), and add a branch
to engine/llm/__init__.py:get_llm_client().
"""

import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """
    Abstract base class for DAVE LLM backends.

    All three engine passes call llm.call() with a prompt string and expect
    either a raw string response (Pass 3 prose) or a JSON-parseable string
    (Pass 1 intent, Pass 2 adjudication). The engine layer handles JSON parsing
    and retry logic via call_json(); backends only need to implement call().
    """

    @abstractmethod
    def call(self, prompt: str) -> str:
        """
        Send prompt to the LLM and return the model's raw text response.

        Implementations should:
        - Send prompt as a single user message (no system message is set here;
          pass-specific instructions are embedded in the prompt itself)
        - Return the full text of the model's response, stripped of any
          wrapping whitespace
        - Raise LLMError on non-retryable failures (auth, quota, model not found)
        - Raise LLMTimeoutError on timeout (allows the engine to retry)

        Args:
            prompt: The complete prompt string, including embedded JSON context
                    and any pass-specific instructions.

        Returns:
            The model's response as a plain string.

        Raises:
            LLMError: On non-retryable backend failures.
            LLMTimeoutError: If the backend times out.
        """

    def call_json(self, prompt: str, max_retries: int | None = None) -> dict:
        """
        Call the LLM and parse the response as JSON. Retries on malformed JSON.

        Pass 1 and Pass 2 both expect structured JSON back from the model. This
        method wraps call() with retry logic so the engine doesn't need to
        duplicate it.

        If the model returns a code-fenced JSON block (```json ... ```), the
        fences are stripped before parsing. This handles models that add
        markdown formatting despite being instructed not to.

        Args:
            prompt: The complete prompt string.
            max_retries: Maximum number of attempts before giving up. Defaults
                         to config.LLM_MAX_RETRIES.

        Returns:
            The parsed JSON as a Python dict.

        Raises:
            LLMJSONError: If the model returns malformed JSON after all retries.
            LLMError: On non-retryable backend failures.
        """
        from engine import config  # local import avoids circular dependency

        retries = max_retries if max_retries is not None else config.LLM_MAX_RETRIES
        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            raw = self.call(prompt)

            # Strip markdown code fences if present (```json ... ``` or ``` ... ```).
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # Remove opening fence (with optional language tag) and closing fence.
                lines = cleaned.splitlines()
                # Drop first line (``` or ```json) and last line (```).
                inner_lines = lines[1:] if lines[-1].strip() == "```" else lines[1:]
                if inner_lines and inner_lines[-1].strip() == "```":
                    inner_lines = inner_lines[:-1]
                cleaned = "\n".join(inner_lines).strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as exc:
                last_error = exc
                logger.warning(
                    "LLM returned malformed JSON (attempt %d/%d): %s — raw: %.200s",
                    attempt,
                    retries,
                    exc,
                    raw,
                )
                # On subsequent attempts the same prompt is re-sent. In practice,
                # LLMs with good instruction-following rarely need more than one retry.

        raise LLMJSONError(
            f"LLM returned malformed JSON after {retries} attempt(s). "
            f"Last error: {last_error}"
        )


# =============================================================================
# Exceptions
# =============================================================================

class LLMError(Exception):
    """
    Base class for all LLM backend errors.
    Raised on non-retryable failures (auth errors, quota exceeded, model not found).
    """


class LLMTimeoutError(LLMError):
    """
    Raised when the LLM backend does not respond within the configured timeout.
    The engine may choose to retry on timeout.
    """


class LLMJSONError(LLMError):
    """
    Raised when the LLM returns a response that cannot be parsed as JSON after
    all retry attempts are exhausted. Indicates a prompt engineering problem or
    an unusually poor model response.
    """
