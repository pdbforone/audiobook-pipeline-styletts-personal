"""
Llama Backend - Unified LLM interface using Ollama.

This module provides a centralized function for all LLM queries across the pipeline.
All phases (chunking, agents, autonomy, UI) should use this unified interface.

Default Model: Llama 3.1 8B Instruct (llama3.1:8b-instruct-q4_K_M)
- 4.9GB quantized model
- Excellent instruction following
- Strong reasoning capabilities
- CPU-friendly with 16GB RAM
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MODEL = "llama3.1:8b-instruct-q4_K_M"
DEFAULT_PROVIDER = "ollama"


@dataclass
class LLMConfig:
    """Configuration for LLM backend."""

    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout_seconds: int = 120


def get_llm_config(config_override: Optional[Dict[str, Any]] = None) -> LLMConfig:
    """
    Get LLM configuration from environment or override.

    Priority:
    1. config_override parameter
    2. Environment variables (LLAMA_MODEL, LLAMA_PROVIDER)
    3. Default values

    Args:
        config_override: Optional dict with provider, model, etc.

    Returns:
        LLMConfig instance
    """
    config_override = config_override or {}

    return LLMConfig(
        provider=config_override.get("provider", os.getenv("LLAMA_PROVIDER", DEFAULT_PROVIDER)),
        model=config_override.get("model", os.getenv("LLAMA_MODEL", DEFAULT_MODEL)),
        max_tokens=config_override.get("max_tokens", 2048),
        temperature=config_override.get("temperature", 0.7),
        timeout_seconds=config_override.get("timeout_seconds", 120),
    )


def run_llama(
    prompt: str,
    system_prompt: Optional[str] = None,
    config: Optional[LLMConfig] = None,
    **kwargs
) -> str:
    """
    Execute LLM query using Ollama.

    This is the unified LLM interface for all pipeline phases.

    Args:
        prompt: The user prompt/query
        system_prompt: Optional system message for context
        config: Optional LLMConfig override
        **kwargs: Additional parameters (max_tokens, temperature, etc.)

    Returns:
        LLM response text

    Raises:
        RuntimeError: If Ollama unavailable or query fails

    Example:
        >>> response = run_llama("Summarize this text: ...")
        >>> print(response)
    """
    # Get configuration
    llm_config = config or get_llm_config()

    # Override config with kwargs
    max_tokens = kwargs.get("max_tokens", llm_config.max_tokens)
    temperature = kwargs.get("temperature", llm_config.temperature)

    try:
        import ollama
    except ImportError:
        raise RuntimeError(
            "Ollama Python client not installed. Install with: pip install ollama"
        )

    # Build messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Execute query
    try:
        logger.debug(f"Querying {llm_config.model} with prompt length: {len(prompt)}")
        start_time = time.time()

        response = ollama.chat(
            model=llm_config.model,
            messages=messages,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        )

        duration = time.time() - start_time
        content = response["message"]["content"]
        tokens = response.get("eval_count", 0)

        logger.debug(
            f"LLM response: {len(content)} chars, {tokens} tokens, {duration:.2f}s"
        )

        return content

    except Exception as e:
        error_msg = f"LLM query failed: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def is_llm_available(model: Optional[str] = None) -> bool:
    """
    Check if LLM is available for queries.

    Args:
        model: Optional model name to check (defaults to config model)

    Returns:
        True if LLM is available and model exists
    """
    try:
        import ollama

        # Get model to check
        llm_config = get_llm_config()
        check_model = model or llm_config.model

        # List available models
        models_response = ollama.list()
        available_models = [m["name"] for m in models_response.get("models", [])]

        # Check if our model is available
        # Handle both "llama3.1:8b-instruct-q4_K_M" and "llama3.1" formats
        model_base = check_model.split(":")[0]
        return any(
            m.startswith(model_base) or m == check_model
            for m in available_models
        )

    except Exception as e:
        logger.warning(f"LLM availability check failed: {e}")
        return False


def get_available_models() -> list[str]:
    """
    Get list of available Ollama models.

    Returns:
        List of model names
    """
    try:
        import ollama
        response = ollama.list()
        return [m["name"] for m in response.get("models", [])]
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return []
