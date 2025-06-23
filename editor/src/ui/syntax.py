"""
Syntax Highlighting for MCP Zero Editor

Provides lightweight syntax highlighting for code with offline-first capability.
"""

import re
import time
import threading
from enum import Enum
import tkinter as tk
import logging
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("mcp_zero.editor.syntax")

class SyntaxHighlighter:
    """
    Lightweight syntax highlighter for code editor.
    
    Follows the same offline-first approach as our other components:
    - Works with minimal resources in offline mode
    - No external dependencies required
    - Graceful performance adjustments based on file size
    """
    
    def __init__(self, text_widget: tk.Text):
        """
        Initialize syntax highlighter.
        
        Args:
            text_widget: Text widget to highlight
        """
        self.text = text_widget
        self.delay_ms = 100  # Delay for highlighting to prevent UI freezes
        self.max_chars = 100000  # Max file size for full highlighting
        
        # Configure tags for syntax highlighting
        self._configure_tags()
        
        # Track changes in a way that won't overload the editor
        self._setup_change_detection()
        
        # Background thread control
        self._lock = threading.RLock()
        self._pending_highlight = False
        
        logger.debug("Syntax highlighter initialized")
    
    def _configure_tags(self):
        """Configure text tags for syntax highlighting."""
        # Python syntax highlighting
        self.text.tag_configure("keyword", foreground="blue")
        self.text.tag_configure("builtin", foreground="dark blue")
        self.text.tag_configure("comment", foreground="grey")
        self.text.tag_configure("string", foreground="green")
        self.text.tag_configure("function", foreground="purple")
        self.text.tag_configure("class", foreground="dark red")
        self.text.tag_configure("number", foreground="dark orange")
    
    def _setup_change_detection(self):
        """Set up detection of text changes for highlighting."""
        # Start with full highlight
        self.text.bind("<<Modified>>", self._schedule_highlight)
        self.text.bind("<KeyRelease>", self._on_key)
        
    def _on_key(self, event):
        """Handle key press events for targeted highlighting."""
        if event.char.strip() or event.keysym in ('BackSpace', 'Delete', 'Return'):
            self._schedule_highlight()
    
    def _schedule_highlight(self, event=None):
        """Schedule highlighting without blocking UI."""
        # Reset modified flag if this was triggered by <<Modified>> event
        if event and str(event.type) == "36":  # Modified event type
            self.text.edit_modified(False)
        
        # Check if text is too large
        if len(self.text.get("1.0", tk.END)) > self.max_chars:
            logger.info(f"File too large for full syntax highlighting (>{self.max_chars} chars)")
            # Just highlight a portion around cursor
            self.text.after(self.delay_ms, self._highlight_visible_area)
        else:
            # Full highlight with delay
            with self._lock:
                # Only schedule if not already pending
                if not self._pending_highlight:
                    self._pending_highlight = True
                    self.text.after(self.delay_ms, self._highlight_all)
    
    def _highlight_all(self):
        """Apply syntax highlighting to entire text."""
        try:
            # Clear all existing tags
            for tag in ["keyword", "builtin", "comment", "string", "function", "class", "number"]:
                self.text.tag_remove(tag, "1.0", tk.END)
            
            # Get text content
            content = self.text.get("1.0", tk.END)
            
            # Apply syntax highlighting based on file type
            if self.text.winfo_toplevel().current_file:
                if self.text.winfo_toplevel().current_file.endswith(".py"):
                    self._highlight_python(content)
                # Add more language support here
            else:
                # Default to Python
                self._highlight_python(content)
                
        except Exception as e:
            logger.error(f"Error during syntax highlighting: {str(e)}")
        finally:
            # Reset pending flag
            with self._lock:
                self._pending_highlight = False
    
    def _highlight_visible_area(self):
        """Highlight only the visible portion of text."""
        try:
            # Get visible area
            visible_start = self.text.index("@0,0")
            visible_end = self.text.index(f"@0,{self.text.winfo_height()}")
            
            # Add some context lines
            start_line = max(1, int(visible_start.split('.')[0]) - 10)
            end_line = int(visible_end.split('.')[0]) + 10
            
            highlight_start = f"{start_line}.0"
            highlight_end = f"{end_line}.end"
            
            # Clear tags in visible area
            for tag in ["keyword", "builtin", "comment", "string", "function", "class", "number"]:
                self.text.tag_remove(tag, highlight_start, highlight_end)
            
            # Get visible content
            content = self.text.get(highlight_start, highlight_end)
            
            # Highlight Python syntax
            if self.text.winfo_toplevel().current_file:
                if self.text.winfo_toplevel().current_file.endswith(".py"):
                    self._highlight_python_region(content, highlight_start)
                # Add more language support here
            else:
                # Default to Python
                self._highlight_python_region(content, highlight_start)
                
        except Exception as e:
            logger.error(f"Error during visible area highlighting: {str(e)}")
        finally:
            # Reset pending flag
            with self._lock:
                self._pending_highlight = False
    
    def _highlight_python(self, content: str):
        """Apply Python syntax highlighting to entire content."""
        # Python keywords
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "None", "nonlocal", "not", "or", "pass", "raise", "return",
            "True", "try", "while", "with", "yield"
        ]
        
        # Python builtins
        builtins = [
            "abs", "all", "any", "bool", "dict", "dir", "enumerate", "filter",
            "float", "format", "id", "int", "isinstance", "len", "list", "map",
            "max", "min", "open", "print", "range", "set", "str", "sum", "tuple", 
            "type", "zip"
        ]
        
        # Apply highlighting using regular expressions
        
        # Comments
        self._apply_regex(r"#.*$", "comment", content)
        
        # Strings (triple-quoted)
        self._apply_regex(r'""".*?"""', "string", content, re.DOTALL)
        self._apply_regex(r"'''.*?'''", "string", content, re.DOTALL)
        
        # Strings (single and double quotes)
        self._apply_regex(r'"[^"\\]*(?:\\.[^"\\]*)*"', "string", content)
        self._apply_regex(r"'[^'\\]*(?:\\.[^'\\]*)*'", "string", content)
        
        # Keywords
        for keyword in keywords:
            self._apply_regex(r'\b' + keyword + r'\b', "keyword", content)
        
        # Builtins
        for builtin in builtins:
            self._apply_regex(r'\b' + builtin + r'\b', "builtin", content)
        
        # Class definitions
        self._apply_regex(r'class\s+([A-Za-z_][A-Za-z0-9_]*)', "class", content)
        
        # Function definitions
        self._apply_regex(r'def\s+([A-Za-z_][A-Za-z0-9_]*)', "function", content)
        
        # Numbers
        self._apply_regex(r'\b\d+\b', "number", content)
    
    def _highlight_python_region(self, content: str, start_index: str):
        """Apply Python syntax highlighting to a region of text."""
        # Convert content line/col offsets to tkinter positions
        lines = content.split('\n')
        start_line = int(start_index.split('.')[0])
        
        # Python keywords
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "None", "nonlocal", "not", "or", "pass", "raise", "return",
            "True", "try", "while", "with", "yield"
        ]
        
        # Python builtins
        builtins = [
            "abs", "all", "any", "bool", "dict", "dir", "enumerate", "filter",
            "float", "format", "id", "int", "isinstance", "len", "list", "map",
            "max", "min", "open", "print", "range", "set", "str", "sum", "tuple", 
            "type", "zip"
        ]
        
        # Process each line
        for i, line in enumerate(lines):
            line_num = start_line + i
            line_start = f"{line_num}.0"
            
            # Comments
            self._highlight_line_matches(line, line_num, r"#.*$", "comment")
            
            # Strings
            self._highlight_line_matches(line, line_num, r'"[^"\\]*(?:\\.[^"\\]*)*"', "string")
            self._highlight_line_matches(line, line_num, r"'[^'\\]*(?:\\.[^'\\]*)*'", "string")
            
            # Keywords
            for keyword in keywords:
                self._highlight_line_matches(line, line_num, r'\b' + keyword + r'\b', "keyword")
            
            # Builtins
            for builtin in builtins:
                self._highlight_line_matches(line, line_num, r'\b' + builtin + r'\b', "builtin")
            
            # Class and function definitions
            self._highlight_line_matches(line, line_num, r'class\s+([A-Za-z_][A-Za-z0-9_]*)', "class")
            self._highlight_line_matches(line, line_num, r'def\s+([A-Za-z_][A-Za-z0-9_]*)', "function")
            
            # Numbers
            self._highlight_line_matches(line, line_num, r'\b\d+\b', "number")
    
    def _apply_regex(self, pattern: str, tag: str, content: str, flags: int = 0):
        """Apply regex pattern to content and tag matches."""
        try:
            for match in re.finditer(pattern, content, flags):
                start, end = match.span()
                # Convert character position to line.column
                start_line = content[:start].count('\n') + 1
                end_line = content[:end].count('\n') + 1
                
                # Calculate column positions
                if start_line == 1:
                    start_col = start
                else:
                    start_col = start - content[:start].rindex('\n') - 1
                    
                if end_line == 1:
                    end_col = end
                else:
                    end_col = end - content[:end].rindex('\n') - 1
                
                # Apply tag
                self.text.tag_add(tag, f"{start_line}.{start_col}", f"{end_line}.{end_col}")
                
        except Exception as e:
            logger.error(f"Error in regex highlight: {str(e)}")
    
    def _highlight_line_matches(self, line: str, line_num: int, pattern: str, tag: str):
        """Apply regex highlighting to a single line."""
        try:
            for match in re.finditer(pattern, line):
                start, end = match.span()
                self.text.tag_add(tag, f"{line_num}.{start}", f"{line_num}.{end}")
        except Exception as e:
            logger.error(f"Error in line highlight: {str(e)}")


def apply_to_editor(editor_widget: tk.Text) -> SyntaxHighlighter:
    """
    Apply syntax highlighting to an editor widget.
    
    Args:
        editor_widget: Text widget to apply highlighting to
        
    Returns:
        The highlighter instance
    """
    highlighter = SyntaxHighlighter(editor_widget)
    return highlighter
