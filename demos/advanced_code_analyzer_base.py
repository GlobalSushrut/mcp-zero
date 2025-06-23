#!/usr/bin/env python3
"""
Advanced Code Analyzer Base Component for MCP Zero Editor

Features:
- Offline-first code analysis 
- Local AST-based syntax analysis
- Extensible plugin architecture
"""

import os
import logging
import threading
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_zero.code_analyzer")

class AnalysisLevel(Enum):
    """Analysis detail levels"""
    BASIC = "basic"      # Syntax only
    STANDARD = "standard"  # Syntax + basic semantics
    ADVANCED = "advanced"  # Deep semantic analysis

class CodeAnalyzer:
    """
    Base code analyzer with offline-first resilience.
    
    Provides core analysis functionality that works without
    external services and can be enhanced when they're available.
    """
    
    def __init__(
        self,
        offline_first: bool = True,
        llm_client = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize code analyzer.
        
        Args:
            offline_first: Whether to start in offline mode
            llm_client: Optional LLM client for enhanced analysis
            cache_dir: Directory to cache analysis results
        """
        self.offline_mode = offline_first
        self.llm_client = llm_client
        self._remote_attempt_made = False
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.expanduser("~"),
                ".mcp_zero",
                "editor",
                "analysis_cache"
            )
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(f"Code analyzer initialized in {'offline' if self.offline_mode else 'online'} mode")
    
    def analyze_file(
        self, 
        file_path: str, 
        level: AnalysisLevel = AnalysisLevel.STANDARD
    ) -> Dict[str, Any]:
        """
        Analyze a single file.
        
        Args:
            file_path: Path to the file to analyze
            level: Level of analysis detail
            
        Returns:
            Dictionary with analysis results
        """
        # Check file exists and is readable
        if not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}
            
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Determine file type from extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # Perform analysis based on file type
            if ext == '.py':
                return self._analyze_python(content, level)
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                return self._analyze_javascript(content, level)
            else:
                return self._analyze_generic(content, level)
                
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {str(e)}")
            return {"error": str(e)}
            
    def _analyze_python(self, content: str, level: AnalysisLevel) -> Dict[str, Any]:
        """Basic Python code analysis"""
        result = {
            "language": "python",
            "syntax_valid": True,
            "structures": [],
            "imports": [],
            "errors": []
        }
        
        # Try to parse Python code with ast
        try:
            import ast
            tree = ast.parse(content)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        result["imports"].append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        result["imports"].append(node.module)
            
            # Extract basic code structures
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    result["structures"].append({
                        "type": "class",
                        "name": node.name,
                        "line": node.lineno
                    })
                elif isinstance(node, ast.FunctionDef):
                    result["structures"].append({
                        "type": "function",
                        "name": node.name,
                        "line": node.lineno
                    })
        
        except SyntaxError as e:
            result["syntax_valid"] = False
            result["errors"].append({
                "type": "syntax",
                "message": str(e),
                "line": e.lineno if hasattr(e, 'lineno') else 0
            })
        except Exception as e:
            result["errors"].append({
                "type": "analysis",
                "message": str(e)
            })
            
        return result
        
    def _analyze_javascript(self, content: str, level: AnalysisLevel) -> Dict[str, Any]:
        """Basic JavaScript code analysis"""
        # Simple implementation - would be expanded with proper JS parser
        return {
            "language": "javascript",
            "syntax_valid": True,
            "structures": [],
            "imports": [],
            "errors": []
        }
        
    def _analyze_generic(self, content: str, level: AnalysisLevel) -> Dict[str, Any]:
        """Fallback generic code analysis"""
        return {
            "language": "unknown",
            "syntax_valid": True,
            "structures": [],
            "imports": [],
            "errors": []
        }
