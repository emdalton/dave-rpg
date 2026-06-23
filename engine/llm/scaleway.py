"""
engine/llm/scaleway.py — DAVE RPG Engine Scaleway Backend

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Implements LLMClient using Scaleway's Generative APIs, which expose an
OpenAI-compatible REST endpoint. Any model available in the Scaleway console
can be selected via the DAVE_SCALEWAY_MODEL environment variable.

This backend is the intended cloud production target for DAVE's web-hosted
deployment. It uses the openai Python package pointed at Scaleway's base URL,
so the same interface works for any Scaleway-hosted model without code changes.

Default model: mistral-small-3.2-24b-instruct-2506
  Pricing (as of 2026-06): €0.15/M input tokens, €0.35/M output tokens

Alternative models (set DAVE_SCALEWAY_MODEL):
  qwen3.5-397b-a17b-instruct-fp8   — larger MoE model, better quality,
                                      €0.60/M input, €3.60/M output

Configuration (all from engine.config / environment variables):
    DAVE_SCALEWAY_API_KEY   — Scaleway IAM API key (falls back to SCW_SECRET_KEY)
    DAVE_SCALEWAY_BASE_URL  — API base URL (default: https://api.scaleway.ai/v1)
    DAVE_SCALEWAY_MODEL     — Model slug as shown in the Scaleway console
    DAVE_SCALEWAY_MAX_TOKENS — Maximum tokens to generate per call (default: 2048)
    DAVE_SCALEWAY_TIMEOUT   — Request timeout in seconds (default: 60)

Dependencies:
    pip install openai

The openai package is imported lazily inside __init__ so that the module can
be imported without it installed, as long as the Scaleway backend is not
actually selected.
"""

import logging

from engine import config
from engine.llm.base import LLMClient, LLMError, LLMTimeoutError

logger = logging.getLogger(__name__)


class ScalewayLLMClient(LLMClient):
    """
    LLMClient implementation backed by Scaleway's Generative APIs.

    Uses the openai Python package with a custom base_url pointing at
    Scaleway's OpenAI-compatible endpoint. One client instance is created
    at engine startup and reused for all three passes.

    Prompts are sent as a single user message with no system message —
    the same pattern used by the Claude and Ollama backends. All
    pass-specific instructions are embedded in the prompt itself.

    Configuration (all from engine.config / environment variables):
        SCALEWAY_API_KEY     — Scaleway IAM API key
        SCALEWAY_BASE_URL    — API base URL
        SCALEWAY_MODEL       — Model slug
        SCALEWAY_MAX_TOKENS  — Max tokens per call
        SCALEWAY_TIMEOUT     — Request timeout in seconds
    """

    def __init__(self) -> None:
        """
        Initialise the OpenAI client pointed at Scaleway's endpoint.
        Raises ImportError if the openai package is not installed, or
        LLMError if the API key is missing.
        """
        try:
            from openai import OpenAI as _OpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for the Scaleway backend. "
                "Install it with: pip install openai"
            ) from exc

        if not config.SCALEWAY_API_KEY:
            raise LLMError(
                "Scaleway API key is not set. Export your key as SCW_SECRET_KEY "
                "(or DAVE_SCALEWAY_API_KEY) before starting the engine."
            )

        self._model = config.SCALEWAY_MODEL
        self._max_tokens = config.SCALEWAY_MAX_TOKENS
        self._timeout = config.SCALEWAY_TIMEOUT

        # The openai package accepts any base_url, making it straightforward
        # to target Scaleway's OpenAI-compatible endpoint.
        self._client = _OpenAI(
            api_key=config.SCALEWAY_API_KEY,
            base_url=config.SCALEWAY_BASE_URL,
            timeout=self._timeout,
        )

        logger.info(
            "ScalewayLLMClient initialised: model=%s base_url=%s max_tokens=%d timeout=%ds",
            self._model,
            config.SCALEWAY_BASE_URL,
            self._max_tokens,
            self._timeout,
        )

    def call(self, prompt: str) -> str:
        """
        Send prompt to Scaleway and return the model's response text.

        The prompt is delivered as a single user message. No system message
        is set here — pass-specific instructions are embedded in the prompt
        string itself, consistent with the Claude and Ollama backends.

        Args:
            prompt: The complete prompt string for this pass.

        Returns:
            The model's response text, whitespace-stripped.

        Raises:
            LLMTimeoutError: If the request exceeds SCALEWAY_TIMEOUT seconds.
            LLMError: On authentication failures, quota errors, or other
                      non-retryable API errors.
        """
        # Import here so we can reference the exception classes without
        # requiring the openai package to be installed at module import time.
        import openai

        logger.debug(
            "Scaleway call: model=%s prompt_len=%d",
            self._model,
            len(prompt),
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self._max_tokens,
            )
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError(
                f"Scaleway request timed out after {self._timeout}s. "
                f"Consider increasing DAVE_SCALEWAY_TIMEOUT."
            ) from exc
        except openai.AuthenticationError as exc:
            raise LLMError(
                "Scaleway authentication failed. Check that SCW_SECRET_KEY "
                "(or DAVE_SCALEWAY_API_KEY) is set correctly."
            ) from exc
        except openai.RateLimitError as exc:
            raise LLMError(
                f"Scaleway rate limit or quota exceeded: {exc}"
            ) from exc
        except openai.APIError as exc:
            # Catches connection errors, server errors, and any other openai
            # API exceptions not handled by the more specific clauses above.
            raise LLMError(f"Scaleway API error: {exc}") from exc

        # Extract the response text. The choices list should always have at
        # least one entry for a non-streaming call, but guard defensively.
        if not response.choices:
            raise LLMError(
                f"Scaleway returned an empty choices list. "
                f"Full response: {response}"
            )

        content = response.choices[0].message.content or ""

        # Log token usage at INFO level so it is visible in play sessions
        # without enabling full debug output — matching the Claude backend's
        # behaviour and making cost tracking straightforward.
        usage = response.usage
        if usage:
            logger.info(
                "Scaleway tokens: input=%d output=%d total=%d",
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )

        return content.strip()
