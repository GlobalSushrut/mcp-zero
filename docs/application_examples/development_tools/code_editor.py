"""
Example: Code Editor with Offline-First Intelligence
Application Category: Development Tools & Environments
"""

import os
import sys
from typing import Optional, Dict, List

# Import MCP Zero components
from mcp_zero.editor.core import EditorCore
from mcp_zero.intelligence.code_analyzer import CodeAnalyzer
from mcp_zero.intelligence.completion import CompletionEngine
from mcp_zero.connectivity import ConnectionManager


class OfflineFirstCodeEditor:
    """Code editor implementing the offline-first resilience pattern."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None
    ):
        # Initialize in offline mode by default
        self.mode = "OFFLINE"
        self.editor_core = EditorCore()
        
        # Initialize offline-capable intelligence components
        self.analyzer = CodeAnalyzer(offline_first=True)
        self.completion = CompletionEngine(offline_first=True)
        
        # Initialize connection manager
        self.connection_manager = ConnectionManager(
            api_key=api_key,
            api_endpoint=api_endpoint,
            max_connection_attempts=1  # Critical: Only try once
        )
        
        # Try to connect just once at initialization
        if api_key:
            self.try_connect_once()
    
    def try_connect_once(self) -> None:
        """
        Attempt to connect to remote services exactly once.
        If connection fails, remains permanently in offline mode.
        """
        try:
            # Attempt connection with timeout
            connected = self.connection_manager.connect(timeout_seconds=2)
            if connected:
                self.mode = "ONLINE"
                print("Connected to remote intelligence services")
            else:
                print("Failed to connect to remote services, using offline intelligence")
        except Exception as e:
            print(f"Connection error: {e}. Using offline intelligence.")
            # No retry attempts - remain in offline mode
    
    def analyze_code(self, code: str) -> Dict:
        """
        Analyze code with offline resilience.
        Uses online if available, otherwise falls back to offline.
        """
        if self.mode == "ONLINE":
            try:
                return self.analyzer.analyze_online(code)
            except Exception as e:
                # Fall back permanently to offline mode
                print(f"Online analysis failed: {e}")
                self.mode = "OFFLINE"
                
        # Use offline analysis (either as default or after fallback)
        return self.analyzer.analyze_offline(code)
    
    def get_completion(self, context: str, cursor_position: int) -> str:
        """
        Get code completion with offline resilience.
        Uses online if available, otherwise falls back to offline.
        """
        if self.mode == "ONLINE":
            try:
                return self.completion.complete_online(context, cursor_position)
            except Exception:
                # Fall back permanently to offline mode
                self.mode = "OFFLINE"
                
        # Use offline completion (either as default or after fallback)
        return self.completion.complete_offline(context, cursor_position)


# Example usage
if __name__ == "__main__":
    # Create editor with optional API key from environment
    editor = OfflineFirstCodeEditor(
        api_key=os.environ.get("MCP_API_KEY"),
        api_endpoint=os.environ.get("MCP_ENDPOINT")
    )
    
    # Always works, regardless of connectivity
    code = "def hello_world():\n    print('Hello World')\n"
    analysis = editor.analyze_code(code)
    completion = editor.get_completion(code, len(code))
    
    print("Analysis result:", analysis)
    print("Completion suggestion:", completion)
