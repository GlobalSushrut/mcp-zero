#!/usr/bin/env python3
"""
Advanced Code Intelligence System for MCP Zero Editor

Integrates all advanced code features into a unified system:
- Code analysis
- Code completion
- Code refactoring
- Project understanding
"""

import os
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple, Set

# Import our components
from advanced_code_analyzer_base import CodeAnalyzer, AnalysisLevel
from advanced_code_refactor import CodeRefactor, RefactoringOperation
from advanced_code_completion import CodeCompletion, CompletionType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_zero.intelligence")

class CodeIntelligence:
    """
    Advanced code intelligence system with offline-first resilience.
    
    Integrates all code understanding capabilities into a unified
    system that works offline by default with optional enhancements
    when remote services are available.
    """
    
    def __init__(
        self,
        project_dir: str,
        llm_client = None,
        db_client = None,
        offline_first: bool = True
    ):
        """
        Initialize code intelligence system.
        
        Args:
            project_dir: Path to the project directory
            llm_client: Optional LLM client for enhanced features
            db_client: Optional DB client for persistent storage
            offline_first: Whether to start in offline mode
        """
        self.project_dir = project_dir
        self.llm_client = llm_client
        self.db_client = db_client
        self.offline_mode = offline_first
        self._remote_attempt_made = False
        
        # Initialize components
        logger.info("Initializing code analyzer...")
        self.analyzer = CodeAnalyzer(offline_first=offline_first, llm_client=llm_client)
        
        logger.info("Initializing code refactoring...")
        self.refactor = CodeRefactor(
            analyzer=self.analyzer, 
            llm_client=llm_client,
            offline_first=offline_first
        )
        
        logger.info("Initializing code completion...")
        self.completion = CodeCompletion(
            analyzer=self.analyzer,
            llm_client=llm_client,
            offline_first=offline_first
        )
        
        # Last analyzed files cache
        self.file_analyses = {}
        self._analyze_count = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Project files
        self._known_files = set()
        self._scan_project_files()
        
        logger.info(f"Code intelligence initialized in {'offline' if self.offline_mode else 'online'} mode")
        
    def _scan_project_files(self):
        """Scan project directory for code files"""
        try:
            extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go'}
            
            for root, _, files in os.walk(self.project_dir):
                for filename in files:
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in extensions:
                        full_path = os.path.join(root, filename)
                        self._known_files.add(full_path)
            
            logger.info(f"Found {len(self._known_files)} code files in project")
        except Exception as e:
            logger.error(f"Error scanning project files: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of the code intelligence system"""
        return {
            "mode": "OFFLINE" if self.offline_mode else "ONLINE",
            "remote_attempt_made": self._remote_attempt_made,
            "known_files": len(self._known_files),
            "analyzed_files": len(self.file_analyses),
            "analyzer_status": "OFFLINE" if self.analyzer.offline_mode else "ONLINE",
            "refactor_status": "OFFLINE" if self.refactor.offline_mode else "ONLINE",
            "completion_status": "OFFLINE" if self.completion.offline_mode else "ONLINE"
        }
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a file and return detailed information.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Analysis results
        """
        with self._lock:
            self._analyze_count += 1
            
            # Check if we have a recent analysis
            if file_path in self.file_analyses:
                last_analysis = self.file_analyses[file_path]
                file_mtime = os.path.getmtime(file_path)
                
                if last_analysis.get('mtime') >= file_mtime:
                    logger.debug(f"Using cached analysis for {file_path}")
                    return last_analysis
            
            # Perform analysis
            analysis = self.analyzer.analyze_file(file_path)
            
            # Add file metadata
            try:
                stat = os.stat(file_path)
                analysis['mtime'] = stat.st_mtime
                analysis['size'] = stat.st_size
            except Exception:
                pass
                
            # Store analysis
            self.file_analyses[file_path] = analysis
            
            return analysis
    
    def get_completions(
        self,
        file_path: str,
        line: int,
        column: int,
        prefix: str,
        context_lines: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get code completions for the current location.
        
        Args:
            file_path: Path to the current file
            line: Current line number (0-indexed)
            column: Current column number
            prefix: Text immediately before the cursor
            context_lines: A few lines around the current line
            
        Returns:
            List of completion suggestions
        """
        return self.completion.get_completions(
            file_path=file_path,
            line=line,
            column=column,
            prefix=prefix,
            context_lines=context_lines
        )
    
    def perform_refactoring(
        self,
        file_path: str,
        operation_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform a refactoring operation.
        
        Args:
            file_path: Path to the file to refactor
            operation_name: Name of the refactoring operation
            parameters: Operation-specific parameters
            
        Returns:
            Refactoring results
        """
        try:
            # Convert operation name to enum
            operation = RefactoringOperation[operation_name.upper()]
            
            # Perform refactoring
            result = self.refactor.refactor(
                file_path=file_path,
                operation=operation,
                parameters=parameters
            )
            
            # If successful, update file analysis
            if result.get('success', False) and 'changes' in result:
                if file_path in self.file_analyses:
                    del self.file_analyses[file_path]
            
            return result
            
        except KeyError:
            return {
                "success": False,
                "message": f"Unknown refactoring operation: {operation_name}"
            }
        except Exception as e:
            logger.error(f"Error in refactoring operation: {str(e)}")
            return {
                "success": False,
                "message": f"Refactoring error: {str(e)}"
            }
    
    def get_diagnostics(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get diagnostics (errors, warnings) for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of diagnostic items
        """
        analysis = self.analyze_file(file_path)
        
        diagnostics = []
        
        # Extract errors from analysis
        if 'errors' in analysis:
            for error in analysis['errors']:
                diagnostics.append({
                    "severity": "error",
                    "message": error.get('message', 'Unknown error'),
                    "line": error.get('line', 0),
                    "column": error.get('column', 0),
                    "source": "mcp-zero-analyzer"
                })
        
        # Add warnings
        if not analysis.get('syntax_valid', True):
            diagnostics.append({
                "severity": "error",
                "message": "Syntax error detected",
                "line": 0,
                "column": 0,
                "source": "mcp-zero-analyzer"
            })
        
        # In a full implementation, we would include:
        # - Import optimization suggestions
        # - Style issues
        # - Performance warnings
        # - Security concerns
        
        return diagnostics
    
    def suggest_code_improvements(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Suggest code improvements for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of improvement suggestions
        """
        # This is where we would integrate more advanced code
        # improvement suggestions based on the analysis
        
        # For now, return a simple example
        return [{
            "type": "improvement",
            "message": "Consider adding docstrings to functions",
            "priority": "medium"
        }]
