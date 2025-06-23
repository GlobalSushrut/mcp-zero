#!/usr/bin/env python3
"""
MCP Zero Code Intelligence Demo

Demonstrates the integration of advanced code intelligence features:
- Code analysis and diagnostics
- Intelligent code completion
- Syntax-aware refactoring
- Project-wide code understanding

All with offline-first resilience pattern.
"""

import os
import sys
import json
import time
import logging
import readline  # For better CLI input handling
from typing import Dict, List, Any, Optional

# Add the parent directory to sys.path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our advanced code intelligence components
from advanced_code_analyzer_base import CodeAnalyzer, AnalysisLevel
from advanced_code_refactor import CodeRefactor, RefactoringOperation
from advanced_code_completion import CodeCompletion, CompletionType
from advanced_code_intelligence import CodeIntelligence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_zero.demo")

class CodeIntelligenceDemo:
    """
    Demo application showcasing MCP Zero's advanced code intelligence.
    Follows offline-first resilience pattern.
    """
    
    def __init__(self):
        # Set up demo project directory
        self.project_dir = os.path.join(
            os.path.expanduser("~"),
            ".mcp_zero",
            "code_intelligence_demo"
        )
        os.makedirs(self.project_dir, exist_ok=True)
        
        # Create example code files if they don't exist
        self._create_example_files()
        
        # Initialize the code intelligence system
        # Following offline-first pattern - start offline and only try once to connect
        print("Initializing code intelligence system...")
        self.code_intelligence = CodeIntelligence(
            project_dir=self.project_dir,
            offline_first=True  # Start in offline mode by default
        )
        
        # Current file being worked on
        self.current_file = None
    
    def _create_example_files(self):
        """Create example code files for the demo"""
        examples = {
            "calculator.py": """#!/usr/bin/env python3
\"\"\"
Simple calculator module
\"\"\"

def add(a, b):
    \"\"\"Add two numbers\"\"\"
    return a + b

def subtract(a, b):
    \"\"\"Subtract b from a\"\"\"
    return a - b

def multiply(a, b):
    \"\"\"Multiply two numbers\"\"\"
    return a * b

def divide(a, b):
    \"\"\"Divide a by b\"\"\"
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

class Calculator:
    \"\"\"Calculator class\"\"\"
    
    def __init__(self):
        self.last_result = 0
    
    def add(self, a, b):
        \"\"\"Add two numbers and store result\"\"\"
        self.last_result = add(a, b)
        return self.last_result
""",
            "utils.py": """#!/usr/bin/env python3
\"\"\"
Utility functions
\"\"\"
import os
import time

def get_timestamp():
    \"\"\"Get current timestamp\"\"\"
    return time.time()

def format_datetime(timestamp=None):
    \"\"\"Format timestamp as datetime string\"\"\"
    if timestamp is None:
        timestamp = get_timestamp()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

class Logger:
    \"\"\"Simple logger class\"\"\"
    
    def __init__(self, name):
        self.name = name
    
    def log(self, message):
        \"\"\"Log a message\"\"\"
        print(f"[{format_datetime()}] {self.name}: {message}")
"""
        }
        
        for filename, content in examples.items():
            file_path = os.path.join(self.project_dir, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"Created example file: {filename}")
    
    def run_cli(self):
        """Run interactive CLI demo"""
        print("\nMCP Zero Code Intelligence Demo")
        print("------------------------------")
        print("Type 'help' for available commands\n")
        
        running = True
        while running:
            try:
                cmd = input("mcp-intel> ").strip()
                
                if cmd == "help":
                    self.show_help()
                elif cmd == "exit" or cmd == "quit":
                    running = False
                elif cmd == "status":
                    self.show_status()
                elif cmd == "files":
                    self.list_files()
                elif cmd.startswith("open "):
                    self.open_file(cmd[5:])
                elif cmd.startswith("analyze "):
                    self.analyze_file(cmd[8:])
                elif cmd == "analyze":
                    # Analyze current file
                    if self.current_file:
                        self.analyze_file(self.current_file)
                    else:
                        print("No file is currently open")
                elif cmd.startswith("complete "):
                    self.show_completions(cmd[9:])
                elif cmd == "diagnostics":
                    self.show_diagnostics()
                elif cmd.startswith("refactor "):
                    self.perform_refactoring(cmd[9:])
                elif cmd.startswith("view "):
                    self.view_file(cmd[5:])
                elif cmd == "view":
                    # View current file
                    if self.current_file:
                        self.view_file(self.current_file)
                    else:
                        print("No file is currently open")
                elif cmd == "":
                    # Empty line, do nothing
                    pass
                else:
                    print(f"Unknown command: {cmd}")
                    self.show_help()
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                logger.error(f"Error processing command: {str(e)}")
                print(f"Error: {str(e)}")
    
    def show_help(self):
        """Show available commands"""
        help_text = """
Available Commands:
------------------
status          - Show code intelligence system status
files           - List project files
open <file>     - Open a file for editing
analyze [file]  - Analyze current file or specified file
view [file]     - View current file or specified file
complete <text> - Show completions for text
diagnostics     - Show diagnostics for current file
refactor <op>   - Perform refactoring operation (rename, etc.)
help            - Show this help text
exit            - Exit the demo
"""
        print(help_text)
    
    def show_status(self):
        """Show status of code intelligence system"""
        status = self.code_intelligence.get_status()
        
        print("\nCode Intelligence Status")
        print("------------------------")
        print(f"Mode: {status['mode']}")
        print(f"Remote attempt made: {status['remote_attempt_made']}")
        print(f"Known files: {status['known_files']}")
        print(f"Analyzed files: {status['analyzed_files']}")
        print(f"Analyzer status: {status['analyzer_status']}")
        print(f"Refactoring status: {status['refactor_status']}")
        print(f"Completion status: {status['completion_status']}")
        
        if self.current_file:
            print(f"\nCurrent file: {self.current_file}")
    
    def list_files(self):
        """List project files"""
        files = []
        for root, _, filenames in os.walk(self.project_dir):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), self.project_dir)
                files.append(rel_path)
        
        if not files:
            print("No files found in project")
            return
        
        print("\nProject Files:")
        for i, file in enumerate(sorted(files), 1):
            marker = "*" if file == self.current_file else " "
            print(f"{marker} {i}. {file}")
    
    def open_file(self, filename):
        """Open a file for editing"""
        if not filename:
            print("Please specify a filename")
            return
        
        file_path = os.path.join(self.project_dir, filename)
        if not os.path.exists(file_path):
            print(f"File not found: {filename}")
            return
        
        self.current_file = filename
        print(f"Opened file: {filename}")
        
        # Analyze the file automatically
        self.analyze_file(filename)
    
    def analyze_file(self, filename):
        """Analyze a file"""
        if not filename:
            print("Please specify a filename")
            return
        
        file_path = os.path.join(self.project_dir, filename)
        if not os.path.exists(file_path):
            print(f"File not found: {filename}")
            return
        
        print(f"Analyzing file: {filename}")
        start_time = time.time()
        
        analysis = self.code_intelligence.analyze_file(file_path)
        
        elapsed = time.time() - start_time
        print(f"Analysis completed in {elapsed:.2f} seconds")
        
        # Show summary of analysis
        print(f"\nLanguage: {analysis.get('language', 'unknown')}")
        print(f"Syntax valid: {analysis.get('syntax_valid', False)}")
        
        if 'structures' in analysis:
            print(f"\nCode structures found: {len(analysis['structures'])}")
            for struct in analysis['structures'][:5]:  # Show first 5
                print(f"  {struct.get('type', '?')}: {struct.get('name', '?')} (line {struct.get('line', '?')})")
            if len(analysis['structures']) > 5:
                print(f"  ... and {len(analysis['structures']) - 5} more")
        
        if 'imports' in analysis:
            print(f"\nImports: {', '.join(analysis['imports'])}")
        
        if 'errors' in analysis and analysis['errors']:
            print(f"\nErrors: {len(analysis['errors'])}")
            for error in analysis['errors']:
                print(f"  {error.get('type', '?')}: {error.get('message', '?')}")
    
    def view_file(self, filename):
        """View file contents"""
        if not filename:
            print("Please specify a filename")
            return
        
        file_path = os.path.join(self.project_dir, filename)
        if not os.path.exists(file_path):
            print(f"File not found: {filename}")
            return
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            print(f"\n--- {filename} ---")
            # Add line numbers
            for i, line in enumerate(content.splitlines(), 1):
                print(f"{i:4d} | {line}")
            print(f"--- End of {filename} ---")
        except Exception as e:
            print(f"Error reading file: {str(e)}")
    
    def show_completions(self, prefix):
        """Show code completions for prefix"""
        if not self.current_file:
            print("No file is currently open")
            return
        
        if not prefix:
            print("Please specify text to complete")
            return
            
        file_path = os.path.join(self.project_dir, self.current_file)
        
        # Get some context lines from the file
        context_lines = []
        try:
            with open(file_path, 'r') as f:
                context_lines = f.read().splitlines()[-10:]  # Last 10 lines
        except Exception:
            pass
            
        # Get completions
        completions = self.code_intelligence.get_completions(
            file_path=file_path,
            line=len(context_lines) - 1,
            column=len(prefix),
            prefix=prefix,
            context_lines=context_lines
        )
        
        if not completions:
            print(f"No completions found for '{prefix}'")
            return
            
        print(f"\nCompletions for '{prefix}':")
        for i, completion in enumerate(completions[:10], 1):  # Show top 10
            label = completion.get('label', '')
            detail = completion.get('detail', '')
            print(f"{i:2d}. {label} ({detail})")
            
        if len(completions) > 10:
            print(f"... and {len(completions) - 10} more")
    
    def show_diagnostics(self):
        """Show diagnostics for current file"""
        if not self.current_file:
            print("No file is currently open")
            return
            
        file_path = os.path.join(self.project_dir, self.current_file)
        diagnostics = self.code_intelligence.get_diagnostics(file_path)
        
        if not diagnostics:
            print("No diagnostics found (file is clean)")
            return
            
        print(f"\nDiagnostics for {self.current_file}:")
        for i, diag in enumerate(diagnostics, 1):
            severity = diag.get('severity', 'info').upper()
            message = diag.get('message', 'Unknown issue')
            line = diag.get('line', 0)
            print(f"{i}. {severity} at line {line}: {message}")
    
    def perform_refactoring(self, args):
        """Perform refactoring operation"""
        if not self.current_file:
            print("No file is currently open")
            return
            
        if not args:
            print("Usage: refactor <operation> [parameters]")
            print("Available operations: rename, optimize_imports")
            return
            
        parts = args.split(maxsplit=1)
        operation = parts[0].upper()
        
        file_path = os.path.join(self.project_dir, self.current_file)
        
        if operation == "RENAME":
            if len(parts) < 2:
                print("Usage: refactor rename old_name:new_name")
                return
                
            try:
                old_name, new_name = parts[1].split(":", 1)
                parameters = {
                    "old_name": old_name,
                    "new_name": new_name
                }
                
                print(f"Renaming '{old_name}' to '{new_name}'...")
                result = self.code_intelligence.perform_refactoring(
                    file_path=file_path,
                    operation_name="RENAME",
                    parameters=parameters
                )
                
                if result.get('success', False):
                    print(f"Success: {result.get('message', 'Refactoring completed')}")
                    
                    # Show diff or updated code if available
                    if 'changes' in result and 'new_code' in result['changes']:
                        print("\nUpdated code:")
                        for i, line in enumerate(result['changes']['new_code'].splitlines()[:10], 1):
                            print(f"{i:4d} | {line}")
                        
                        # Write changes to file
                        try:
                            with open(file_path, 'w') as f:
                                f.write(result['changes']['new_code'])
                            print(f"\nWritten changes to {self.current_file}")
                        except Exception as e:
                            print(f"Error writing changes: {str(e)}")
                else:
                    print(f"Error: {result.get('message', 'Unknown error')}")
                
            except ValueError:
                print("Invalid format. Use: refactor rename old_name:new_name")
                
        elif operation == "OPTIMIZE_IMPORTS":
            print("Optimizing imports...")
            result = self.code_intelligence.perform_refactoring(
                file_path=file_path,
                operation_name="OPTIMIZE_IMPORTS",
                parameters={}
            )
            
            if result.get('success', False):
                print(f"Success: {result.get('message', 'Imports optimized')}")
            else:
                print(f"Error: {result.get('message', 'Unknown error')}")
        else:
            print(f"Unknown refactoring operation: {operation}")
            print("Available operations: rename, optimize_imports")

def main():
    """Main entry point for the demo"""
    print("=" * 60)
    print("MCP Zero Code Intelligence Demo")
    print("=" * 60)
    
    try:
        demo = CodeIntelligenceDemo()
        demo.run_cli()
    except KeyboardInterrupt:
        print("\nDemo terminated by user")
    except Exception as e:
        logger.exception("Error in demo")
        print(f"\nDemo error: {str(e)}")
    
    print("\nDemo completed!")

if __name__ == "__main__":
    main()
