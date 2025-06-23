#!/usr/bin/env python3
"""
MCP Zero Enhanced Editor Demo

Demonstrates the full power of MCP Zero Editor with:
- Offline-first resilience
- Project memory system
- Advanced LLM code generation
- CLI-based interactive experience
"""

import os
import sys
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional
import readline  # For better CLI input handling

# Add the parent directory to sys.path to allow importing editor modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our enhanced components
from enhanced_project_memory import ProjectMemory, MemoryType
from enhanced_code_generator import CodeGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_zero.demo")

class EnhancedEditorDemo:
    """
    Enhanced editor demo with project memory and code generation.
    Demonstrates offline-first resilience pattern:
    - Starts in offline mode
    - Attempts external connections once
    - Falls back to local processing
    """
    
    def __init__(self):
        # Set up demo project
        self.project_dir = os.path.join(
            os.path.expanduser("~"),
            ".mcp_zero",
            "demo_project"
        )
        os.makedirs(self.project_dir, exist_ok=True)
        
        # Initialize components
        self.init_components()
        
        # Project state
        self.current_file = None
        self.project_files = set()
        
    def init_components(self):
        """Initialize all editor components."""
        print("Initializing project memory...")
        # Start in offline mode by default as per our memory resilience pattern
        self.project_memory = ProjectMemory(
            project_id="demo_project",
            offline_first=True  # Start in offline mode by default
        )
        
        print("Initializing code generator...")
        # Initialize code generator with memory system
        self.code_generator = CodeGenerator(
            project_dir=self.project_dir,
            project_memory=self.project_memory,
            offline_first=True  # Start in offline mode by default
        )
        
        # Store project initialization in memory
        self.project_memory.add_memory(
            MemoryType.ARCHITECTURE,
            "MCP Zero Demo Editor Project",
            metadata={
                "created_at": time.time(),
                "description": "Demo project showcasing MCP Zero Editor capabilities"
            }
        )
        
    def run_cli(self):
        """Run the interactive CLI demo."""
        print("\nMCP Zero Enhanced Editor Demo - Interactive CLI")
        print("Type 'help' for available commands")
        
        running = True
        while running:
            try:
                cmd = input("\nmcp-zero> ").strip()
                
                if cmd == "help":
                    self.show_help()
                elif cmd == "exit" or cmd == "quit":
                    running = False
                elif cmd.startswith("create "):
                    self.handle_create_command(cmd[7:])
                elif cmd.startswith("edit "):
                    self.handle_edit_command(cmd[5:])
                elif cmd == "list":
                    self.list_files()
                elif cmd.startswith("search "):
                    self.search_memory(cmd[7:])
                elif cmd == "status":
                    self.show_status()
                elif cmd.startswith("view "):
                    self.view_file(cmd[5:])
                elif cmd.startswith("memory "):
                    self.show_memory(cmd[7:])
                elif cmd == "":
                    # Empty line, do nothing
                    pass
                else:
                    print(f"Unknown command: {cmd}")
                    self.show_help()
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {str(e)}")
    
    def show_help(self):
        """Show available commands."""
        help_text = """
        Available Commands:
        -----------------
        create <filename>      - Create a new file with code generation
        edit <filename>        - Edit an existing file
        view <filename>        - View file contents
        list                   - List all project files
        search <query>         - Search project memory
        memory <type>          - Show memory items by type (architecture, file, etc)
        status                 - Show component status
        help                   - Show this help
        exit                   - Exit the demo
        """
        print(help_text)
    
    def handle_create_command(self, filename):
        """Handle file creation with code generation."""
        if not filename:
            print("Please specify a filename")
            return
            
        # Ensure file has proper extension
        if not any(filename.endswith(ext) for ext in [".py", ".js", ".java", ".go"]):
            filename += ".py"  # Default to Python
        
        file_path = os.path.join(self.project_dir, filename)
        
        if os.path.exists(file_path):
            print(f"File {filename} already exists")
            return
        
        # Get specification for code generation
        spec = input("Enter code specification: ")
        if not spec:
            print("Canceled code generation")
            return
        
        print(f"Generating code for {filename}...")
        
        # Generate code with offline-first approach
        code = self.code_generator.generate_code(spec, file_path)
        
        # Save generated code
        with open(file_path, 'w') as f:
            f.write(code)
            
        self.project_files.add(filename)
        self.current_file = filename
        
        print(f"Created file {filename} with generated code")
        
    def handle_edit_command(self, filename):
        """Simulate editing a file."""
        if not filename:
            print("Please specify a filename")
            return
            
        file_path = os.path.join(self.project_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"File {filename} does not exist")
            return
        
        # In a full editor, this would open the file for editing
        print(f"Opening {filename} for editing (simulated)")
        self.current_file = filename
        
        # Show file content
        self.view_file(filename)
        
        # For demo purposes, just add a comment
        edit = input("Add a comment to the file (will be added to the top): ")
        
        if edit:
            with open(file_path, 'r') as f:
                content = f.read()
                
            with open(file_path, 'w') as f:
                f.write(f"# {edit}\n{content}")
                
            print(f"Updated {filename} with comment")
            
            # Record edit in project memory
            self.project_memory.add_memory(
                MemoryType.FILE,
                f"Edited {filename}",
                metadata={
                    "file": filename,
                    "edit": "Added comment",
                    "timestamp": time.time()
                }
            )
    
    def view_file(self, filename):
        """View file contents."""
        if not filename:
            print("Please specify a filename")
            return
            
        file_path = os.path.join(self.project_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"File {filename} does not exist")
            return
            
        print(f"\n--- {filename} ---")
        try:
            with open(file_path, 'r') as f:
                print(f.read())
            print(f"--- End of {filename} ---")
        except Exception as e:
            print(f"Error reading file: {str(e)}")
    
    def list_files(self):
        """List all project files."""
        files = []
        for root, _, filenames in os.walk(self.project_dir):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), self.project_dir)
                files.append(rel_path)
                self.project_files.add(rel_path)
                
        if not files:
            print("No files in project yet")
            return
            
        print("\nProject files:")
        for i, filename in enumerate(sorted(files), 1):
            prefix = "* " if filename == self.current_file else "  "
            print(f"{prefix}{i}. {filename}")
            
    def search_memory(self, query):
        """Search project memory."""
        if not query:
            print("Please specify a search query")
            return
            
        print(f"Searching memory for '{query}'...")
        results = self.project_memory.search_memory(query)
        
        if not results:
            print("No results found")
            return
            
        print(f"\nFound {len(results)} results:")
        for i, item in enumerate(results, 1):
            print(f"\n{i}. {item['type'].upper()}: {item['content'][:80]}...")
            print(f"   Created: {time.ctime(item['created_at'])}")
            if item.get('metadata'):
                for key, value in item['metadata'].items():
                    # Format timestamps nicely
                    if key.endswith('_at') and isinstance(value, (int, float)):
                        value = time.ctime(value)
                    print(f"   {key}: {value}")
    
    def show_memory(self, memory_type):
        """Show memory items by type."""
        try:
            # Convert string to enum
            mem_type = MemoryType[memory_type.upper()]
            items = self.project_memory.get_memory_by_type(mem_type)
            
            if not items:
                print(f"No {memory_type} items found")
                return
                
            print(f"\n{memory_type.capitalize()} memory items:")
            for i, item in enumerate(items, 1):
                print(f"\n{i}. {item['content'][:80]}...")
                print(f"   Created: {time.ctime(item['created_at'])}")
                if item.get('metadata'):
                    for key, value in item['metadata'].items():
                        # Format timestamps nicely
                        if key.endswith('_at') and isinstance(value, (int, float)):
                            value = time.ctime(value)
                        print(f"   {key}: {value}")
        except KeyError:
            print(f"Unknown memory type: {memory_type}")
            print("Available types: " + ", ".join([t.name.lower() for t in MemoryType]))
            
    def show_status(self):
        """Show component status."""
        print("\nMCP Zero Editor Status")
        print("-" * 50)
        
        # Project memory status
        print(f"Project Memory: {'OFFLINE' if self.project_memory.offline_mode else 'ONLINE'}")
        print(f"Memory Items: {len(self.project_memory._memory_items)}")
        print(f"Remote Sync Attempted: {self.project_memory._remote_attempt_made}")
        
        # Code generator status
        print(f"\nCode Generator: {'OFFLINE' if self.code_generator.offline_mode else 'ONLINE'}")
        print(f"Remote Generation Attempted: {self.code_generator._remote_attempt_made}")
        
        # Project status
        print(f"\nProject Directory: {self.project_dir}")
        print(f"Project Files: {len(self.project_files)}")
        if self.current_file:
            print(f"Current File: {self.current_file}")


def main():
    """Main entry point for the enhanced editor demo"""
    print("=" * 80)
    print("MCP Zero Enhanced Editor Demo")
    print("=" * 80)
    print("Initializing components...")
    
    # Create and run demo
    try:
        demo = EnhancedEditorDemo()
        demo.run_cli()
    except KeyboardInterrupt:
        print("\nDemo terminated by user")
    except Exception as e:
        logger.exception("Error in demo")
        print(f"\nDemo error: {str(e)}")
    
    print("\nDemo completed!")

if __name__ == "__main__":
    main()
