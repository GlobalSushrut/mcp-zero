"""
Thin JSON-RPC client for the Rust kernel's cognitive endpoints.

Communicates over Unix domain socket with newline-delimited JSON-RPC 2.0.
Zero external dependencies — uses only stdlib.
"""

import json
import socket
import os
from typing import Any, Dict, List, Optional

DEFAULT_SOCKET = "/tmp/mcp-kernel.sock"


class KernelClient:
    """Synchronous JSON-RPC client to the Rust MCP kernel."""

    def __init__(self, socket_path: Optional[str] = None):
        self.socket_path = socket_path or os.environ.get(
            "MCP_KERNEL_SOCKET", DEFAULT_SOCKET
        )
        self._next_id = 0

    def _call(self, method: str, params: Any = None) -> Any:
        """Send a JSON-RPC 2.0 request and return the result."""
        self._next_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._next_id,
        }

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_path)
            payload = json.dumps(request) + "\n"
            sock.sendall(payload.encode("utf-8"))

            # Read response (single newline-delimited JSON line)
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk

            response = json.loads(buf.decode("utf-8").strip())
            if "error" in response and response["error"] is not None:
                err = response["error"]
                raise RuntimeError(
                    f"Kernel error {err.get('code', -1)}: {err.get('message', 'unknown')}"
                )
            return response.get("result")
        finally:
            sock.close()

    # --- Cognitive API ---

    def cog_state(self) -> Dict:
        """Get current cognitive state."""
        return self._call("cog.state")

    def cog_cycle(self, input_vec: Optional[List[float]] = None) -> Dict:
        """Run one cognitive cycle with optional input vector."""
        params = {}
        if input_vec is not None:
            params["input"] = input_vec
        return self._call("cog.cycle", params)

    def cog_register_intention(self, name: str, priority: float = 0.5) -> Dict:
        """Register a cognitive intention."""
        return self._call("cog.register_intention", {
            "name": name,
            "priority": priority,
        })

    def cog_activate_intention(self, name: str) -> Dict:
        """Activate a cognitive intention."""
        return self._call("cog.activate_intention", {"name": name})

    def cog_contradiction(self, vector: List[float]) -> Dict:
        """Process a contradiction vector."""
        return self._call("cog.process_contradiction", {"vector": vector})

    def cog_add_fact(self, text: str, embedding: List[float]) -> Dict:
        """Add a fact to the knowledge store."""
        return self._call("cog.add_fact", {
            "text": text,
            "embedding": embedding,
        })

    def cog_search(self, query: List[float], top_k: int = 5) -> Dict:
        """Search the knowledge store by embedding similarity."""
        return self._call("cog.search", {"query": query, "top_k": top_k})

    def cog_register_symbol(
        self, domain: str, symbol: str, vector: Optional[List[float]] = None
    ) -> Dict:
        """Register a symbol in a domain."""
        params = {"domain": domain, "symbol": symbol}
        if vector is not None:
            params["vector"] = vector
        return self._call("cog.register_symbol", params)

    def cog_ground(self, vector: List[float]) -> Dict:
        """Ground a vector to symbolic representations."""
        return self._call("cog.ground", {"vector": vector})

    # --- Kernel API ---

    def status(self) -> Dict:
        """Get kernel status."""
        return self._call("kernel.status")
