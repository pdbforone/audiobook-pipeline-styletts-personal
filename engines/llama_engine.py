"""
LLaMA engine stub.

This wrapper is intentionally disabled by default and not wired into
any engine registry. It provides a minimal interface compatible with a
future llama.cpp/Ollama/local deployment without impacting current TTS
engines.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class LlamaEngine:
    """Lightweight, opt-in wrapper for local LLaMA inference."""

    def __init__(self, model_path: Optional[str] = None, *, enabled: bool = False, **kwargs: Any) -> None:
        self.model_path = model_path
        self.enabled = enabled
        self.options: Dict[str, Any] = kwargs
        self._client = None

    def load(self) -> None:
        """Best-effort loader for a local LLaMA backend (stubbed)."""
        if not self.enabled:
            return
        try:
            import ollama  # type: ignore

            self._client = ollama
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(f"LLaMA backend unavailable: {exc}") from exc

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text locally if enabled; otherwise raise to avoid silent use."""
        if not self.enabled:
            raise RuntimeError("LlamaEngine is disabled by default.")
        if self._client is None:
            self.load()
        if self._client is None:
            raise RuntimeError("LLaMA backend not loaded.")

        model = self.options.get("model") or (self.model_path or "llama")
        try:
            response = self._client.generate(model=model, prompt=prompt, options=kwargs)
            return response.get("response", "") if isinstance(response, dict) else str(response)
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"LLaMA generation failed: {exc}") from exc

    def shutdown(self) -> None:
        """Release resources if any were allocated."""
        self._client = None
