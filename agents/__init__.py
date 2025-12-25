"""
Agents Module - Local LLM-powered intelligence layer.

This module provides AI agents for:
- Semantic chunk boundary detection (LlamaChunker)
- Pipeline failure analysis (LlamaReasoner)
- Text rewriting for TTS compatibility (LlamaRewriter)
- Metadata generation (LlamaMetadataGenerator)

All agents use local Ollama for inference - no external APIs.

Requirements:
    pip install ollama
    # Then run: ollama pull llama3.1:8b-instruct-q4_K_M

Default Model: Llama 3.1 8B Instruct (4.9GB quantized)
"""

from .llama_base import LlamaAgent, LlamaResourceManager, get_agent
from .llama_chunker import LlamaChunker
from .llama_reasoner import LlamaReasoner
from .llama_rewriter import LlamaRewriter
from .llama_metadata import LlamaMetadataGenerator
from .llama_pre_validator import LlamaPreValidator
from .llama_self_review import LlamaSelfReview
from .llama_diagnostics import LlamaDiagnostics
from .llama_voice_matcher import LlamaVoiceMatcher

__all__ = [
    "LlamaAgent",
    "LlamaResourceManager",
    "LlamaChunker",
    "LlamaReasoner",
    "LlamaRewriter",
    "LlamaMetadataGenerator",
    "LlamaPreValidator",
    "LlamaSelfReview",
    "LlamaDiagnostics",
    "LlamaVoiceMatcher",
    "get_agent",
]
