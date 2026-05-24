"""
engine/llm/claude.py — DAVE RPG Engine Claude Backend

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Implements LLMClient using the Anthropic Claude API. This is the Phase 1
backend, used for prototyping and ground-truth generation. All model and
API configuration is read from engine.config (which in turn reads environment
variables at startup — the API key is never hardcoded).

Dependencies:
    pip install anthropic

The anthropic package is imported lazily inside __init__ so that the module
can be imported even if the package is not installed, as long as the ollama
backend is selected. An ImportError with a clear message is raised if the
package is missing when this backend is actually used.
"""

import logging

from engine import config
from engine.llm.base import LLMClient, LLMError, LLMTimeoutError

logger = logging.getLogger(__name__)


class ClaudeLLMClient(LLMClient):
    """
    LLMClient implementation backed by the Anthropic Claude API.

    One client instance is created at engine startup and reused for all three
    passes. The anthropic.Anthropic() client manages connection pooling
    internally, so creating a new client per call is not necessary.

    Configuration (all from engine.config / environment variables):
        CLAUDE_API_KEY   — Anthropic API key (required)
        CLAUDE_MODEL     — Model string, e.g. "claude-sonnet-4-6"
        CLAUDE_MAX_TOKENS — Maximum tokens the model may generate per call
    """

    def __init__(self) -> None:
        """
        Initialise the Anthropic client. Raises ImportError if the anthropic
        package is not installed, or LLMError if the API key is missing.
        """
        try:
            import anthropic as _anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for the Claude backend. "
                "Install it with: pip install anthropic"
            ) from exc

        if not config.CLAUDE_API_KEY:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. Export the key as an environment "
                "variable before starting the engine."
            )

        self._client = _anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)
        self._model = config.CLAUDE_MODEL
        self._max_tokens = config.CLAUDE_MAX_TOKENS

        # Session-level token accumulators. Updated after every API call.
        # Exposed via token_totals() for end-of-session reporting.
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

        logger.info("ClaudeLLMClient initialised: model=%s max_tokens=%d",
                    self._model, self._max_tokens)

    def call(self, prompt: str) -> str:
        """
        Send prompt to Claude and return the text of the first content block.

        The entire prompt (including embedded JSON context) is sent as a single
        user message. No persistent system prompt is set here — pass-specific
        instructions are embedded in the prompt string by the engine.

        Args:
            prompt: The complete prompt string for this pass.

        Returns:
            The model's response text, whitespace-stripped.

        Raises:
            LLMTimeoutError: On connection timeout.
            LLMError: On API errors (auth, rate limit, server error, etc.).
        """
        import anthropic  # already imported in __init__; re-import for exception classes

        logger.debug("Claude call: model=%s prompt_len=%d", self._model, len(prompt))

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError(f"Claude API request timed out: {exc}") from exc
        except anthropic.AuthenticationError as exc:
            raise LLMError(
                f"Claude API authentication failed. Check ANTHROPIC_API_KEY. Details: {exc}"
            ) from exc
        except anthropic.RateLimitError as exc:
            raise LLMError(f"Claude API rate limit exceeded: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMError(f"Claude API error: {exc}") from exc

        # message.content is a list of content blocks; take the first text block.
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text = block.text
                break

        # Extract and accumulate token usage. The usage object is present on
        # every non-streaming response from the Anthropic API.
        in_tok = getattr(message.usage, "input_tokens", 0) or 0
        out_tok = getattr(message.usage, "output_tokens", 0) or 0
        self._total_input_tokens += in_tok
        self._total_output_tokens += out_tok

        logger.debug(
            "Claude response: stop_reason=%s response_len=%d "
            "tokens=in:%d/out:%d  session_total=in:%d/out:%d",
            message.stop_reason,
            len(response_text),
            in_tok,
            out_tok,
            self._total_input_tokens,
            self._total_output_tokens,
        )
        return response_text.strip()

    # Anthropic API pricing per million tokens (USD), keyed by model name prefix.
    # Prefix matching is used because model strings carry version/date suffixes
    # (e.g. "claude-haiku-4-5-20251001"). The longest matching prefix wins.
    # Last verified: 2026-05-22. Check https://www.anthropic.com/pricing when
    # updating models; prices change and this table will drift.
    # Suggested update cadence: quarterly, or whenever a new model is added.
    # Not every session, but not just at module creation either — somewhere
    # in between, driven by calendar rather than game events.
    _PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
        # (input $/MTok, output $/MTok)
        "claude-haiku-4-5":  (0.80,  4.00),
        "claude-haiku-3":    (0.25,  1.25),
        "claude-sonnet-4":   (3.00, 15.00),
        "claude-sonnet-3-7": (3.00, 15.00),
        "claude-sonnet-3-5": (3.00, 15.00),
        "claude-opus-4":    (15.00, 75.00),
        "claude-opus-3":    (15.00, 75.00),
    }

    def _cost_usd(self) -> float | None:
        """
        Compute estimated session cost in USD from accumulated token counts.

        Returns None if the model is not in the pricing table, so callers
        can distinguish "cost unknown" from "cost is zero".
        """
        # Find the longest prefix in _PRICING_PER_MTOK that matches self._model.
        model_lower = self._model.lower()
        match = None
        for prefix, rates in self._PRICING_PER_MTOK.items():
            if model_lower.startswith(prefix):
                if match is None or len(prefix) > len(match[0]):
                    match = (prefix, rates)
        if match is None:
            return None
        input_rate, output_rate = match[1]
        return (
            self._total_input_tokens  * input_rate  / 1_000_000
            + self._total_output_tokens * output_rate / 1_000_000
        )

    def token_totals(self) -> dict:
        """
        Return session-level token usage and estimated cost.

        Keys: 'input_tokens', 'output_tokens', 'total', 'cost_usd'.
        'cost_usd' is a float if the model is in the pricing table, or None
        if the model is unknown. Intended for end-of-session reporting.
        Resets are not supported — create a new client instance for a fresh count.
        """
        return {
            "input_tokens":  self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total":         self._total_input_tokens + self._total_output_tokens,
            "cost_usd":      self._cost_usd(),
        }
