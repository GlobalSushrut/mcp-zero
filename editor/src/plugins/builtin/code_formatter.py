"""
Code Formatter Plugin for MCP Zero Editor

A simple plugin that formats code with offline-first capability.
"""

import os
import sys
import logging
import subprocess
import threading
from typing import Dict, Any, Optional

# Initialize logger
logger = logging.getLogger("mcp_zero.editor.plugins.code_formatter")

# Plugin metadata
plugin_info = {
    "name": "Code Formatter",
    "version": "0.1.0",
    "description": "Format code with offline-first capability",
    "author": "MCP Zero Team"
}


class CodeFormatterPlugin:
    """
    Plugin for formatting code in the editor.
    
    Following offline-first approach:
    - Works with local tools first
    - Only attempts to use external formatters once
    - Falls back to basic formatting if external tools unavailable
    """
    
    def __init__(self, editor=None):
        """
        Initialize code formatter plugin.
        
        Args:
            editor: Editor instance
        """
        self.editor = editor
        self.formatters = {
            ".py": self._format_python,
            ".js": self._format_javascript,
            ".html": self._format_html,
            ".css": self._format_css,
        }
        
        # Track which formatters were attempted and failed
        self._failed_formatters = set()
        self._lock = threading.RLock()
        
        logger.info("Code formatter plugin initialized")
        
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if successful
        """
        if self.editor:
            # Add formatting command to editor menu
            try:
                ai_menu = self.editor.menu.nametowidget(self.editor.menu.winfo_children()[2])
                ai_menu.add_command(
                    label="Format Code", 
                    command=self.format_current_file,
                    accelerator="Ctrl+Shift+F"
                )
                
                # Add keyboard shortcut
                self.editor.root.bind("<Control-Shift-F>", lambda e: self.format_current_file())
                
                logger.info("Code formatter plugin added to UI")
            except Exception as e:
                logger.error(f"Error adding formatter to menu: {str(e)}")
                
        return True
    
    def format_current_file(self) -> bool:
        """
        Format the currently open file.
        
        Returns:
            True if formatting was successful
        """
        if not self.editor or not self.editor.current_file:
            logger.warning("No file open to format")
            return False
            
        # Get file extension
        _, ext = os.path.splitext(self.editor.current_file)
        
        # Find formatter for this extension
        formatter = self.formatters.get(ext.lower())
        if not formatter:
            logger.warning(f"No formatter available for {ext} files")
            self.editor.status_label.config(text=f"No formatter for {ext} files")
            return False
            
        try:
            # Get current content
            content = self.editor.editor.get(1.0, "end-1c")
            
            # Format content
            formatted = formatter(content)
            if formatted and formatted != content:
                # Save cursor position
                cursor_pos = self.editor.editor.index("insert")
                
                # Update content
                self.editor.editor.delete(1.0, "end")
                self.editor.editor.insert(1.0, formatted)
                
                # Restore cursor position if possible
                try:
                    self.editor.editor.mark_set("insert", cursor_pos)
                except:
                    pass
                
                # Update status
                self.editor.status_label.config(text=f"Code formatted ({ext})")
                logger.info(f"Formatted {ext} file: {self.editor.current_file}")
                return True
            else:
                self.editor.status_label.config(text="No formatting changes needed")
                return True
                
        except Exception as e:
            logger.error(f"Error formatting code: {str(e)}")
            self.editor.status_label.config(text=f"Format error: {str(e)}")
            return False
    
    def _format_python(self, content: str) -> Optional[str]:
        """
        Format Python code using black or a simple fallback.
        
        Args:
            content: Python code to format
            
        Returns:
            Formatted code or None if formatting failed
        """
        with self._lock:
            if "black" in self._failed_formatters:
                # Already tried and failed with black, use fallback
                return self._basic_python_format(content)
                
            try:
                # First try with black if available - only attempt once
                # Following the same pattern as Traffic Agent video processing
                result = subprocess.run(
                    [sys.executable, "-m", "black", "-", "-q"],
                    input=content.encode(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=3
                )
                
                if result.returncode == 0:
                    return result.stdout.decode('utf-8')
                else:
                    # Black failed, remember this and use fallback permanently
                    logger.warning("Black formatter failed, using fallback formatter")
                    self._failed_formatters.add("black")
                    return self._basic_python_format(content)
                    
            except Exception as e:
                # Black not installed or other error, permanently mark as failed
                logger.warning(f"Error using black: {str(e)}, using fallback formatter")
                self._failed_formatters.add("black")
                return self._basic_python_format(content)
    
    def _basic_python_format(self, content: str) -> str:
        """
        Basic Python formatter that works offline.
        
        Args:
            content: Python code to format
            
        Returns:
            Formatted code
        """
        lines = content.split('\n')
        result = []
        indent_level = 0
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                result.append('')
                continue
                
            # Adjust indent level based on previous line
            if line.strip().startswith(('elif', 'else:', 'except:', 'finally:')):
                # Keep same indentation for these blocks
                pass
            elif line.strip().startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'with ')):
                # Indent after these lines if they end with :
                if line.rstrip().endswith(':'):
                    formatted = '    ' * indent_level + line.strip()
                    result.append(formatted)
                    indent_level += 1
                    continue
            elif line.strip().endswith(':'):
                # Other lines ending with : increase indent
                formatted = '    ' * indent_level + line.strip()
                result.append(formatted)
                indent_level += 1
                continue
            elif line.strip() == 'return' or line.strip().startswith('return '):
                # Return statements just get indented
                pass
            
            # Basic dedent detection
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces == 0 and indent_level > 0:
                indent_level = 0
            
            # Apply formatting
            formatted = '    ' * indent_level + line.strip()
            result.append(formatted)
        
        return '\n'.join(result)
    
    def _format_javascript(self, content: str) -> Optional[str]:
        """Format JavaScript code with offline-first approach."""
        # For this demo, just use a simple formatter
        # In production, would attempt to use prettier once, then fall back
        return self._basic_js_format(content)
    
    def _basic_js_format(self, content: str) -> str:
        """Simple offline JavaScript formatter."""
        # Basic formatting similar to Python
        lines = content.split('\n')
        result = []
        indent_level = 0
        
        for line in lines:
            strip_line = line.strip()
            if not strip_line:
                result.append('')
                continue
                
            # Handle brackets for indentation
            if strip_line == '}' or strip_line == '});':
                indent_level = max(0, indent_level - 1)
                
            # Format the line with current indent
            formatted = '  ' * indent_level + strip_line
            result.append(formatted)
            
            # Adjust indent level for next line
            if strip_line.endswith('{'):
                indent_level += 1
        
        return '\n'.join(result)
    
    def _format_html(self, content: str) -> Optional[str]:
        """Format HTML code with offline-first approach."""
        # Simple HTML formatter
        return content  # Stub implementation
    
    def _format_css(self, content: str) -> Optional[str]:
        """Format CSS code with offline-first approach."""
        # Simple CSS formatter
        return content  # Stub implementation
    
    def check_health(self) -> bool:
        """
        Check if plugin is healthy.
        
        Returns:
            True if plugin is operational
        """
        # Plugin is always operational since it has fallback mechanisms
        return True
    
    def shutdown(self) -> None:
        """Clean up resources when editor is closing."""
        pass


def initialize_plugin(editor):
    """
    Initialize the plugin for the editor.
    
    Args:
        editor: Editor instance
        
    Returns:
        Plugin instance
    """
    plugin = CodeFormatterPlugin(editor)
    plugin.initialize()
    return plugin
