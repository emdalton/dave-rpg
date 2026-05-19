"""
engine/llm/ollama.py — DAVE RPG Engine Ollama Backend

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Implements LLMClient using the Ollama HTTP API. This is the Phase 2 target
backend, intended for local inference with Mistral 7B (or any other model
served by Ollama). Swapping from Claude to Ollama requires only changing the
DAVE_LLM_BACKEND environment variable to "ollama" — no engine code changes.

Ollama must be running and the target model must be pulled before the engine
starts. See: https://ollama.com/

Configuration (all from engine.config / environment variables):
    DAVE_OLLAMA_BASE_URL — Base URL for Ollama HTTP API (default: http://localhost:11434)
    DAVE_OLLAMA_MODEL    — Model name as known to Ollama (default: "mistral")
    DAVE_OLLAMA_TIMEOUT  — Request timeout in seconds (default: 120)

Dependencies:
    pip install requests

The requests package is part of most Python environments but is not in the
standard library. An ImportError with a clear message is raised if it is
missing when this backend is actually used.

Phase 2 note: This implementation uses the Ollama /api/generate endpoint with
stream=False, which blocks until the full response is available. For interactive
play this may be acceptable given local inference speeds, but a streaming
implementation could be added later if needed without changing the LLMClient
interface.
"""

import logging

from engine import config
from engine.llm.base import LLMClient, LLMError, LLMTimeoutError

logger = logging.getLogger(__name__)


class OllamaLLMClient(LLMClient):
    """
    LLMClient implementation backed by a locally-running Ollama instance.

    Uses the Ollama REST API (/api/generate) with stream=False. The model
    must already be pulled in Ollama before the engine starts.

    Configuration (all from engine.config / environment variables):
        OLLAMA_BASE_URL  — Ollama API base URL
        OLLAMA_MODEL     — Model name registered in Ollama
        OLLAMA_TIMEOUT   — Request timeout in seconds
    """

    def __init__(self) -> None:
        """
        Validate configuration and confirm requests is available.
        Does not make a network call — connection is tested on first call().
        """
        try:
            import requests as _requests  # noqa: F401 — confirm availability
        except ImportError as exc:
            raise ImportError(
                "The 'requests' package is required for the Ollama backend. "
                "Install it with: pip install requests"
            ) from exc

        self._base_url = config.OLLAMA_BASE_URL.rstrip("/")
        self._model = config.OLLAMA_MODEL
        self._timeout = config.OLLAMA_TIMEOUT
        self._generate_url = f"{self._base_url}/api/generate"

        logger.info(
            "OllamaLLMClient initialised: model=%s base_url=%s timeout=%ds",
            self._model,
            self._base_url,
            self._timeout,
        )

    def call(self, prompt: str) -> str:
        """
        Send prompt to Ollama and return the model's response text.

        Uses the /api/generate endpoint with stream=False so the full response
        arrives in a single JSON object. The response field in Ollama's reply
        contains the generated text.

        Args:
            prompt: The complete prompt string for this pass.

        Returns:
            The model's response text, whitespace-stripped.

        Raises:
            LLMTimeoutError: If the request exceeds OLLAMA_TIMEOUT seconds.
            LLMError: On connection errors or non-200 HTTP responses.
        """
        import requests  # already confirmed available in __init__

        logger.debug(
            "Ollama call: model=%s url=%s prompt_len=%d",
            self._model,
            self._generate_url,
            len(prompt),
        )

        payload = {
            "model": self._model,
            "prompt": prompt,
            # stream=False means Ollama waits for the full response before
            # returning, giving us a single JSON object to parse.
            "stream": False,
        }

        try:
            response = requests.post(
                self._generate_url,
                json=payload,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(
                f"Ollama request timed out after {self._timeout}s. "
                f"Consider increasing DAVE_OLLAMA_TIMEOUT for slower hardware."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Could not connect to Ollama at {self._base_url}. "
                f"Make sure Ollama is running. Details: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

        if response.status_code != 200:
            raise LLMError(
                f"Ollama returned HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError(
                f"Ollama returned non-JSON response: {response.text[:500]}"
            ) from exc

        # The Ollama /api/generate response has a 'response' key containing
        # the generated text when stream=False.
        response_text = data.get("response", "")
        if not response_text:
            raise LLMError(
                f"Ollama response missing 'response' field. Full response: {data}"
            )

        logger.debug(
            "Ollama response: done=%s response_len=%d",
            data.get("done"),
            len(response_text),
        )
        return response_text.strip()
