"""
engine/llm/__init__.py — DAVE RPG Engine LLM Package

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Exports get_llm_client(), which returns the appropriate LLMClient implementation
based on the DAVE_LLM_BACKEND environment variable (or the default in config.py).
All engine code should call this factory rather than importing a concrete
implementation directly — that's what makes it easy to swap backends.

Usage:

    from engine.llm import get_llm_client

    llm = get_llm_client()
    response = llm.call(prompt_text)
"""

from engine import config
from engine.llm.base import LLMClient


def get_llm_client() -> LLMClient:
    """
    Factory function: return the configured LLM client instance.

    Reads LLM_BACKEND from engine.config (which in turn reads DAVE_LLM_BACKEND
    from the environment). No other code in the engine needs to know which
    backend is in use.

    Returns:
        A concrete LLMClient implementation (ClaudeLLMClient, OllamaLLMClient,
        or ScalewayLLMClient).

    Raises:
        ValueError: If LLM_BACKEND is set to an unrecognised value. This should
                    be caught by config.validate() at startup, so reaching this
                    point indicates a configuration change after startup.
    """
    if config.LLM_BACKEND == "claude":
        from engine.llm.claude import ClaudeLLMClient
        return ClaudeLLMClient()

    if config.LLM_BACKEND == "ollama":
        from engine.llm.ollama import OllamaLLMClient
        return OllamaLLMClient()

    if config.LLM_BACKEND == "scaleway":
        from engine.llm.scaleway import ScalewayLLMClient
        return ScalewayLLMClient()

    raise ValueError(
        f"Unknown LLM_BACKEND: {config.LLM_BACKEND!r}. "
        f"Valid values are 'claude', 'ollama', and 'scaleway'."
    )


__all__ = ["LLMClient", "get_llm_client"]
