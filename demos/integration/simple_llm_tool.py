#!/usr/bin/env python3
"""
Simple LLM Tool - MCP Zero Demo
Prompts for API key and performs LLM-powered code analysis
"""

import os
import sys
import getpass
from typing import Dict, Any, Optional

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our module for code intelligence
from advanced_code_intelligence import CodeIntelligence

class SimpleLLMClient:
    """Minimal LLM client for demo purposes"""
    
    def __init__(self, api_key: str, endpoint: str = "https://api.example.com/v1"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.connected = False
        
        # Try to connect once (offline-first resilience pattern)
        try:
            self._try_connect()
        except Exception as e:
            print(f"Failed to connect to LLM service: {str(e)}")
    
    def _try_connect(self):
        """Try to connect to the LLM service once"""
        print("Attempting to connect to LLM service...")
        # In a real implementation, we would verify connection here
        # For demo, we'll simulate this
        if self.api_key and len(self.api_key) > 10:
            self.connected = True
            print("✓ Connected to LLM service")
            # Set an attribute that CodeIntelligence can check
            self.is_available = True
        else:
            print("✗ Invalid API key")
            self.is_available = False
    
    def generate_completion(self, prompt: str) -> str:
        """Generate completion from LLM"""
        if not self.connected:
            return "[OFFLINE MODE] LLM service not available"
        
        try:
            # In a real implementation, we would call the API here
            # For demo, we'll simulate a response
            print("Generating LLM response...")
            return f"[LLM RESPONSE] Analysis for: {prompt[:30]}..."
        except Exception:
            return "[ERROR] Failed to generate completion"

def main():
    """Entry point for the simple LLM tool"""
    print("\n=== MCP Zero Simple LLM Tool ===")
    
    # Get API key securely
    api_key = getpass.getpass("Enter LLM API Key (input will be hidden): ")
    
    # Create LLM client
    llm_client = SimpleLLMClient(api_key)
    
    # Create project directory
    project_dir = os.path.join(os.path.expanduser("~"), ".mcp_zero", "llm_demo")
    os.makedirs(project_dir, exist_ok=True)
    
    # Create a simple sample file if none exists
    sample_file = os.path.join(project_dir, "sample.py")
    if not os.path.exists(sample_file):
        with open(sample_file, 'w') as f:
            f.write("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
    
class Calculator:
    def __init__(self):
        self.result = 0
        
    def add(self, a, b):
        self.result = a + b
        return self.result
""")
    
    # Initialize code intelligence system with LLM client
    print("\nInitializing code intelligence system...")
    code_intelligence = CodeIntelligence(
        project_dir=project_dir,
        llm_client=llm_client,
        offline_first=False  # Allow online mode with our LLM client
    )
    
    # Show status
    status = code_intelligence.get_status()
    print(f"\nSystem Status: {status['mode']}")
    print(f"LLM Integration: {'Active' if status['mode'] == 'ONLINE' else 'Inactive'}")
    
    # Simple menu
    running = True
    while running:
        print("\n--- Available Actions ---")
        print("1. Analyze file")
        print("2. Get code completions")
        print("3. View system status")
        print("4. Exit")
        
        choice = input("\nSelect action (1-4): ")
        
        if choice == '1':
            # Analyze file
            file_path = sample_file
            print(f"\nAnalyzing {os.path.basename(file_path)}...")
            analysis = code_intelligence.analyze_file(file_path)
            
            print("\nAnalysis Results:")
            print(f"Language: {analysis.get('language', 'unknown')}")
            print(f"Syntax Valid: {analysis.get('syntax_valid', False)}")
            
            if 'structures' in analysis:
                print("\nStructures:")
                for structure in analysis['structures'][:3]:  # Show first 3
                    print(f"- {structure.get('type', '?')}: {structure.get('name', '?')}")
            
        elif choice == '2':
            # Code completion
            prefix = input("\nEnter text to complete: ")
            file_path = sample_file
            
            # Read file for context
            with open(file_path, 'r') as f:
                context_lines = f.read().splitlines()
            
            print("Getting completions...")
            completions = code_intelligence.get_completions(
                file_path=file_path,
                line=len(context_lines) - 1,
                column=0,
                prefix=prefix,
                context_lines=context_lines
            )
            
            print("\nCompletions:")
            if completions:
                for i, completion in enumerate(completions[:5], 1):
                    print(f"{i}. {completion.get('label', '?')}")
            else:
                print("No completions available")
                
        elif choice == '3':
            # System status
            status = code_intelligence.get_status()
            print("\nDetailed System Status:")
            for key, value in status.items():
                print(f"{key}: {value}")
                
        elif choice == '4':
            # Exit
            running = False
        
        else:
            print("Invalid choice. Please try again.")
    
    print("\nExiting LLM Tool. Goodbye!")

if __name__ == "__main__":
    main()
