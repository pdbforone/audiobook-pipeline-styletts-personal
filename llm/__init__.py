"""
LLM Backend - Unified interface for local language models.

Provides consistent LLM access across all pipeline phases.
"""

from .llama_backend import run_llama, get_llm_config, LLMConfig

__all__ = ["run_llama", "get_llm_config", "LLMConfig"]
