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
    # Then run: ollama pull phi3:mini  (or your preferred model)
"""

from .llama_base import LlamaAgent, LlamaResourceManager, get_agent
from .llama_chunker import LlamaChunker
from .llama_reasoner import LlamaReasoner
from .llama_rewriter import LlamaRewriter
from .llama_metadata import LlamaMetadataGenerator

__all__ = [
    "LlamaAgent",
    "LlamaResourceManager",
    "LlamaChunker",
    "LlamaReasoner",
    "LlamaRewriter",
    "LlamaMetadataGenerator",
    "get_agent",
]
