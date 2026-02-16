"""
Cognitive Orchestrator — thin Python layer that connects LLM inference
to the Rust cognitive engine.

Architecture:
  Python (this file) → LLM inference + embedding generation
  Rust (kernel)      → ALL vector math, reasoning, entropy, symbols, knowledge

The orchestrator:
  1. Takes natural language input
  2. Generates embeddings (Python)
  3. Sends vectors to Rust for cognitive processing
  4. Gets symbolic results back from Rust
  5. Constructs prompts from symbolic state
  6. Calls LLM for natural language output (Python)
  7. Feeds LLM output back into Rust cognitive cycle
"""

from typing import Dict, List, Optional

from .kernel_client import KernelClient
from .embeddings import EmbeddingEngine
from .inference import LLMInference


class CognitiveOrchestrator:
    """Orchestrates the Rust cognitive engine with Python LLM inference."""

    def __init__(
        self,
        kernel_socket: Optional[str] = None,
        embed_backend: Optional[str] = None,
        llm_backend: Optional[str] = None,
    ):
        self.kernel = KernelClient(kernel_socket)
        self.embedder = EmbeddingEngine(backend=embed_backend)
        self.llm = LLMInference(backend=llm_backend)

    def think(self, input_text: str) -> Dict:
        """
        Full cognitive cycle:
          1. Embed input text → vector (Python)
          2. Run cognitive cycle with vector (Rust)
          3. Ground result to symbols (Rust)
          4. Build prompt from symbols + state
          5. Generate LLM response (Python)
          6. Return combined result
        """
        # 1. Embed input
        input_vec = self.embedder.embed(input_text)

        # 2. Run cognitive cycle in Rust
        cycle_result = self.kernel.cog_cycle(input_vec)

        # 3. Ground current field to symbols
        state = cycle_result.get("state", {})
        field = state.get("field", {}).get("data", input_vec)
        grounding = self.kernel.cog_ground(field)

        # 4. Build prompt from cognitive state
        prompt = self._build_prompt(input_text, state, grounding)

        # 5. Generate LLM response
        system_prompt = (
            "You are a cognitive reasoning engine. You process information through "
            "entropic intent fields and symbolic grounding. Respond concisely and "
            "analytically based on the cognitive state provided."
        )
        llm_response = self.llm.generate(prompt, system=system_prompt)

        return {
            "input": input_text,
            "cognitive_state": state,
            "grounding": grounding,
            "response": llm_response,
            "cycle": state.get("cycle", 0),
            "backends": {
                "embeddings": self.embedder.backend,
                "llm": self.llm.backend,
            },
        }

    def learn(self, text: str) -> Dict:
        """
        Add a fact to the Rust knowledge store:
          1. Generate embedding (Python)
          2. Store fact + embedding in Rust
        """
        embedding = self.embedder.embed(text)
        result = self.kernel.cog_add_fact(text, embedding)
        return {"text": text, "fact_id": result.get("id")}

    def recall(self, query: str, top_k: int = 5) -> Dict:
        """
        Search the Rust knowledge store:
          1. Generate query embedding (Python)
          2. Search by cosine similarity in Rust
        """
        query_vec = self.embedder.embed(query)
        result = self.kernel.cog_search(query_vec, top_k)
        return result

    def set_intention(self, name: str, priority: float = 0.5) -> Dict:
        """Register and activate a cognitive intention in Rust."""
        reg = self.kernel.cog_register_intention(name, priority)
        act = self.kernel.cog_activate_intention(name)
        return {"registered": reg.get("ok"), "activated": act.get("ok")}

    def define_symbol(
        self, domain: str, symbol: str, description: Optional[str] = None
    ) -> Dict:
        """
        Define a symbol in the Rust cognitive engine:
          1. Optionally embed the description (Python)
          2. Register symbol with vector in Rust
        """
        vector = None
        if description:
            vector = self.embedder.embed(description)
        result = self.kernel.cog_register_symbol(domain, symbol, vector)
        return {"domain": domain, "symbol": symbol, "ok": result.get("ok")}

    def contradict(self, statement: str) -> Dict:
        """
        Process a contradiction:
          1. Embed the contradictory statement (Python)
          2. Process contradiction vector in Rust
          3. Get updated cognitive state
        """
        vec = self.embedder.embed(statement)
        state = self.kernel.cog_contradiction(vec)
        return {
            "statement": statement,
            "contradiction_level": state.get("contradiction_level", 0),
            "state": state,
        }

    def state(self) -> Dict:
        """Get current cognitive state from Rust."""
        return self.kernel.cog_state()

    def _build_prompt(self, input_text: str, state: Dict, grounding: Dict) -> str:
        """Build an LLM prompt from cognitive state."""
        parts = [f"Input: {input_text}"]

        # Add symbolic grounding
        symbols = grounding.get("top_symbols", [])
        if symbols:
            sym_str = ", ".join(
                f"{s[0]}({s[1]:.2f})" if isinstance(s, list) else str(s)
                for s in symbols[:5]
            )
            parts.append(f"Active symbols: {sym_str}")

        # Add cognitive metrics
        parts.append(f"Contradiction level: {state.get('contradiction_level', 0):.3f}")
        parts.append(f"Cycle: {state.get('cycle', 0)}")

        active = state.get("active_intentions", [])
        if active:
            parts.append(f"Active intentions: {', '.join(active)}")

        coherence = grounding.get("coherence", 0)
        parts.append(f"Symbol coherence: {coherence:.3f}")

        if grounding.get("emerged"):
            parts.append("NOTE: New symbol emergence detected.")

        parts.append("\nProvide analysis based on the above cognitive state.")
        return "\n".join(parts)
