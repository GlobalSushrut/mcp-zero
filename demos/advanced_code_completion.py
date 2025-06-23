#!/usr/bin/env python3
"""
Advanced Code Completion System for MCP Zero Editor

Features:
- Offline-first code completion
- Context-aware suggestions
- Multi-language support
- Local fallback mechanisms
"""

import os
import re
import json
import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

# Import our components
from advanced_code_analyzer_base import CodeAnalyzer, AnalysisLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_zero.completion")

class CompletionType(Enum):
    """Types of code completions"""
    SYMBOL = "symbol"         # Variable/function/class names
    SNIPPET = "snippet"       # Code snippets
    STATEMENT = "statement"   # Full statement
    IMPORT = "import"         # Import statements
    PARAMETER = "parameter"   # Function parameters

class CodeCompletion:
    """
    Advanced code completion with offline-first resilience.
    
    Provides intelligent code suggestions that work offline
    with enhanced capabilities when remote services available.
    """
    
    def __init__(
        self,
        analyzer: Optional[CodeAnalyzer] = None,
        llm_client = None,
        offline_first: bool = True,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize code completion system.
        
        Args:
            analyzer: Code analyzer to use (creates one if None)
            llm_client: Optional LLM client for enhanced completion
            offline_first: Whether to start in offline mode
            cache_dir: Directory to cache completions
        """
        # Create analyzer if not provided
        self.analyzer = analyzer or CodeAnalyzer(offline_first=offline_first)
        self.llm_client = llm_client
        self.offline_mode = offline_first
        self._remote_attempt_made = False
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.expanduser("~"),
                ".mcp_zero",
                "editor",
                "completion_cache"
            )
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Build local completion database
        self._language_snippets = {
            'python': self._load_snippets('python'),
            'javascript': self._load_snippets('javascript'),
            'java': self._load_snippets('java'),
            'go': self._load_snippets('go')
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(f"Code completion initialized in {'offline' if self.offline_mode else 'online'} mode")
    
    def _load_snippets(self, language: str) -> Dict[str, Any]:
        """Load snippets for a language from local storage"""
        # In a real implementation, we'd load from files
        # For demo purposes, we'll return predefined snippets
        
        if language == 'python':
            return {
                'if': 'if ${1:condition}:\n    ${0:pass}',
                'for': 'for ${1:item} in ${2:iterable}:\n    ${0:pass}',
                'def': 'def ${1:function_name}(${2:parameters}):\n    """${3:docstring}"""\n    ${0:pass}',
                'class': 'class ${1:ClassName}:\n    """${2:docstring}"""\n    \n    def __init__(self${3:, parameters}):\n        ${0:pass}',
                'import': 'import ${0:module}',
                'try': 'try:\n    ${1:pass}\nexcept ${2:Exception} as ${3:e}:\n    ${0:pass}'
            }
        elif language == 'javascript':
            return {
                'if': 'if (${1:condition}) {\n    ${0}\n}',
                'for': 'for (let ${1:i} = 0; ${1:i} < ${2:array}.length; ${1:i}++) {\n    ${0}\n}',
                'function': 'function ${1:name}(${2:parameters}) {\n    ${0}\n}',
                'class': 'class ${1:Name} {\n    constructor(${2:parameters}) {\n        ${0}\n    }\n}',
                'import': 'import { ${1:module} } from "${0:package}";',
                'try': 'try {\n    ${1}\n} catch (${2:error}) {\n    ${0}\n}'
            }
        else:
            return {}
    
    def get_completions(
        self, 
        file_path: str,
        line: int,
        column: int,
        prefix: str,
        context_lines: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get code completions for the current position.
        
        Args:
            file_path: Path to the current file
            line: Current line number (0-indexed)
            column: Current column number
            prefix: Text immediately before the cursor
            context_lines: A few lines around the current line
            
        Returns:
            List of completion suggestions
        """
        # Try online completion if available
        if not self.offline_mode and self.llm_client and not self._remote_attempt_made:
            try:
                # Try to use remote service for more intelligent completions
                logger.info(f"Attempting enhanced completions via remote service")
                
                # Mark that we've attempted to use the service
                self._remote_attempt_made = True
                
                # This would use the actual LLM for advanced completions
                # In a real implementation, this would call the LLM service
                
                # Simulate failure for demonstration
                if True:  # Set to False to simulate success
                    raise Exception("Simulated remote service unavailable")
                
                # Code that would execute if service available
                return [{
                    "type": CompletionType.SNIPPET.value,
                    "label": "Advanced completion",
                    "detail": "Generated by AI service",
                    "insertText": "# This would be AI-generated code"
                }]
                
            except Exception as e:
                logger.warning(f"Enhanced completions failed: {str(e)}")
                logger.info("Switching to offline mode permanently")
                self.offline_mode = True
        
        # Fall back to local completions
        return self._get_local_completions(file_path, line, column, prefix, context_lines)
    
    def _get_local_completions(
        self, 
        file_path: str,
        line: int,
        column: int,
        prefix: str,
        context_lines: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate completions using local analysis"""
        # Determine file language
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.py':
            language = 'python'
        elif ext in ['.js', '.jsx']:
            language = 'javascript'
        elif ext in ['.ts', '.tsx']:
            language = 'typescript'
        elif ext == '.java':
            language = 'java'
        elif ext == '.go':
            language = 'go'
        else:
            language = 'unknown'
            
        # Get language-specific completions
        completions = []
        
        # Add snippet completions
        snippets = self._language_snippets.get(language, {})
        for keyword, snippet in snippets.items():
            if keyword.startswith(prefix):
                completions.append({
                    "type": CompletionType.SNIPPET.value,
                    "label": keyword,
                    "detail": "Snippet",
                    "insertText": snippet
                })
        
        # Add symbol completions from context
        symbols = self._extract_symbols_from_context(context_lines, language)
        for symbol in symbols:
            if symbol.startswith(prefix):
                completions.append({
                    "type": CompletionType.SYMBOL.value,
                    "label": symbol,
                    "detail": "From context",
                    "insertText": symbol
                })
        
        # Add common imports based on language
        if prefix.startswith('imp') and language == 'python':
            completions.append({
                "type": CompletionType.IMPORT.value,
                "label": "import",
                "detail": "Import statement",
                "insertText": "import "
            })
        
        # Add language-specific keywords
        keywords = self._get_language_keywords(language)
        for keyword in keywords:
            if keyword.startswith(prefix):
                completions.append({
                    "type": CompletionType.STATEMENT.value,
                    "label": keyword,
                    "detail": "Keyword",
                    "insertText": keyword
                })
        
        # Sort completions by relevance
        return sorted(completions, key=lambda c: self._calculate_relevance(c, prefix))
    
    def _extract_symbols_from_context(
        self, 
        context_lines: List[str],
        language: str
    ) -> List[str]:
        """Extract variable and function names from context lines"""
        symbols = set()
        
        # Simple pattern matching for symbols
        # A real implementation would use language-specific parsing
        
        if language == 'python':
            # Match variable assignments and function definitions
            var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*='
            func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*'
            
            for line in context_lines:
                for pattern in [var_pattern, func_pattern, class_pattern]:
                    matches = re.findall(pattern, line)
                    symbols.update(matches)
        
        elif language in ['javascript', 'typescript']:
            # Match variable assignments and function definitions
            var_pattern = r'\b(let|var|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            func_pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            
            for line in context_lines:
                var_matches = re.findall(var_pattern, line)
                for match in var_matches:
                    if len(match) > 1:
                        symbols.add(match[1])  # Add the variable name
                        
                func_matches = re.findall(func_pattern, line)
                symbols.update(func_matches)
                
        return list(symbols)
    
    def _get_language_keywords(self, language: str) -> List[str]:
        """Get keywords for the specified language"""
        if language == 'python':
            return [
                'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
                'def', 'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
                'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
                'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True', 'try',
                'while', 'with', 'yield'
            ]
        elif language == 'javascript':
            return [
                'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
                'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends',
                'false', 'finally', 'for', 'function', 'if', 'import', 'in',
                'instanceof', 'let', 'new', 'null', 'return', 'super', 'switch',
                'this', 'throw', 'true', 'try', 'typeof', 'var', 'void', 'while',
                'with', 'yield'
            ]
        else:
            return []
    
    def _calculate_relevance(self, completion: Dict[str, Any], prefix: str) -> float:
        """Calculate relevance score for sorting completions"""
        label = completion.get('label', '')
        
        # Exact prefix match gets highest score
        if label == prefix:
            return 1.0
            
        # Starts with prefix gets high score
        if label.startswith(prefix):
            return 0.9 - (len(label) - len(prefix)) * 0.01  # Shorter suggestions ranked higher
            
        # Contains prefix gets medium score
        if prefix in label:
            return 0.5
            
        # Default low score
        return 0.1
