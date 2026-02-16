"""
LLM Inference — thin Python wrapper for language model calls.

Supports multiple backends:
  1. Mock: deterministic responses for testing (zero dependencies)
  2. Ollama: local LLM inference via HTTP API (no API key needed)
  3. OpenAI: cloud LLM inference (requires OPENAI_API_KEY)

The default is mock — works offline, no GPU, no downloads.
"""

import json
import os
import urllib.request
from typing import Dict, List, Optional


class LLMInference:
    """Thin wrapper for LLM inference calls."""

    def __init__(self, backend: Optional[str] = None):
        self._backend = backend or os.environ.get("MCP_LLM_BACKEND", "mock")
        self._ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        self._ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
        self._openai_key = os.environ.get("OPENAI_API_KEY")
        self._openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def backend(self) -> str:
        return self._backend

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """Generate a completion from the LLM."""
        if self._backend == "ollama":
            return self._generate_ollama(prompt, system, temperature, max_tokens)
        if self._backend == "openai":
            return self._generate_openai(prompt, system, temperature, max_tokens)
        return self._generate_mock(prompt, system)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """Chat-style completion with message history."""
        if self._backend == "ollama":
            return self._chat_ollama(messages, temperature, max_tokens)
        if self._backend == "openai":
            return self._chat_openai(messages, temperature, max_tokens)
        return self._chat_mock(messages)

    # --- Mock backend (deterministic, for testing) ---

    def _generate_mock(self, prompt: str, system: Optional[str] = None) -> str:
        words = prompt.lower().split()
        if any(w in words for w in ["reason", "think", "analyze"]):
            return "Analysis: The input suggests a multi-layered pattern requiring entropic decomposition."
        if any(w in words for w in ["summarize", "summary"]):
            return "Summary: Key patterns identified across the cognitive field."
        if any(w in words for w in ["contradict", "contradiction"]):
            return "Contradiction detected: opposing symbolic vectors require resolution through entropic collapse."
        return f"Processed input with {len(words)} tokens. Cognitive cycle complete."

    def _chat_mock(self, messages: List[Dict[str, str]]) -> str:
        last = messages[-1]["content"] if messages else ""
        return self._generate_mock(last)

    # --- Ollama backend (local LLM) ---

    def _generate_ollama(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int
    ) -> str:
        payload = {
            "model": self._ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            f"{self._ollama_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        return result.get("response", "")

    def _chat_ollama(
        self, messages: List[Dict[str, str]], temperature: float, max_tokens: int
    ) -> str:
        payload = {
            "model": self._ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        req = urllib.request.Request(
            f"{self._ollama_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        return result.get("message", {}).get("content", "")

    # --- OpenAI backend ---

    def _generate_openai(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._chat_openai(messages, temperature, max_tokens)

    def _chat_openai(
        self, messages: List[Dict[str, str]], temperature: float, max_tokens: int
    ) -> str:
        if not self._openai_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        payload = {
            "model": self._openai_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._openai_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]
