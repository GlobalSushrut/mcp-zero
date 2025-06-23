"""
Search Utility for MCP Zero Editor

Provides fast text search capabilities with offline-first resilience.
"""

import os
import re
import logging
import threading
import time
from typing import Dict, List, Set, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize logger
logger = logging.getLogger("mcp_zero.editor.utils.search")

class SearchEngine:
    """
    Lightweight search engine for code and text files.
    
    Follows offline-first resilience pattern:
    - Always works in fully offline mode
    - Optional acceleration via external service attempted only once
    - Falls back permanently to local search if service unavailable
    """
    
    def __init__(self, cache_dir: Optional[str] = None, max_workers: int = 4):
        """
        Initialize search engine.
        
        Args:
            cache_dir: Directory for search cache
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        
        # Set up cache directory
        self.cache_dir = cache_dir or os.path.join(
            os.path.expanduser("~"),
            ".mcp_zero",
            "editor",
            "search_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Status tracking
        self._lock = threading.RLock()
        self._failed_service_attempt = False
        self._indexing = False
        self._index_cache: Dict[str, Dict] = {}
        
        logger.info(f"Search engine initialized with cache at {self.cache_dir}")
    
    def search_directory(
        self, 
        directory: str, 
        query: str, 
        file_patterns: Optional[List[str]] = None,
        case_sensitive: bool = False,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for text in files within a directory.
        
        Args:
            directory: Directory to search
            query: Text to search for
            file_patterns: Optional list of file patterns to include (e.g., ["*.py"])
            case_sensitive: Whether search is case sensitive
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with match information
        """
        # Validate directory
        if not os.path.exists(directory) or not os.path.isdir(directory):
            logger.error(f"Invalid directory for search: {directory}")
            return []
            
        # Try acceleration service first, but only once
        # Following the offline-first resilience pattern used in Traffic Agent
        if not self._failed_service_attempt:
            try:
                logger.debug("Attempting to use search acceleration service")
                results = self._try_accelerated_search(directory, query, file_patterns, case_sensitive)
                if results is not None:
                    # Successful acceleration, return results
                    return results[:max_results]
                    
                # Service unavailable or failed, mark as failed to avoid future attempts
                with self._lock:
                    self._failed_service_attempt = True
                logger.info("Search acceleration unavailable, using local search engine")
                    
            except Exception as e:
                # Service error, mark as failed to avoid future attempts
                with self._lock:
                    self._failed_service_attempt = True
                logger.info(f"Search acceleration error: {str(e)}, using local search")
                
        # Fall back to local search
        return self._local_search(directory, query, file_patterns, case_sensitive, max_results)
    
    def _try_accelerated_search(
        self, 
        directory: str, 
        query: str, 
        file_patterns: Optional[List[str]], 
        case_sensitive: bool
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Try to use search acceleration service.
        
        This would normally connect to an external service for faster indexing/searching,
        but in this implementation we'll just simulate service unavailability.
        
        Args:
            directory: Directory to search
            query: Text to search for
            file_patterns: Optional list of file patterns to include
            case_sensitive: Whether search is case sensitive
            
        Returns:
            List of results or None if service unavailable
        """
        # In a real implementation, this would connect to an acceleration service
        # Following Traffic Agent pattern - only attempting connection once
        # For this demo, always simulate service unavailability
        return None
    
    def _local_search(
        self, 
        directory: str, 
        query: str, 
        file_patterns: Optional[List[str]], 
        case_sensitive: bool,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Perform local search without external services.
        
        Args:
            directory: Directory to search
            query: Text to search for
            file_patterns: Optional list of file patterns to include
            case_sensitive: Whether search is case sensitive
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with match information
        """
        start_time = time.time()
        results = []
        file_count = 0
        
        # Compile regex for query
        try:
            if case_sensitive:
                pattern = re.compile(re.escape(query))
            else:
                pattern = re.compile(re.escape(query), re.IGNORECASE)
        except Exception as e:
            logger.error(f"Invalid search pattern: {str(e)}")
            return []
        
        # Compile file pattern regex if provided
        file_regex = None
        if file_patterns:
            pattern_parts = []
            for fp in file_patterns:
                # Convert glob pattern to regex
                regex_part = fp.replace(".", "\\.").replace("*", ".*").replace("?", ".")
                pattern_parts.append(f"({regex_part}$)")
            file_regex = re.compile("|".join(pattern_parts))
        
        # Get list of files to search
        files_to_search = []
        for root, _, files in os.walk(directory):
            for filename in files:
                if file_regex:
                    if not file_regex.match(filename):
                        continue
                
                # Skip binary and very large files
                filepath = os.path.join(root, filename)
                try:
                    if os.path.getsize(filepath) > 5 * 1024 * 1024:  # Skip files > 5MB
                        continue
                        
                    # Quick check for binary files
                    with open(filepath, 'rb') as f:
                        chunk = f.read(1024)
                        if b'\x00' in chunk:  # Binary file check
                            continue
                except Exception:
                    continue
                
                files_to_search.append(filepath)
                
        # Use thread pool to search files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._search_file, f, pattern): f 
                for f in files_to_search
            }
            
            for future in as_completed(future_to_file):
                filepath = future_to_file[future]
                file_count += 1
                
                try:
                    file_matches = future.result()
                    if file_matches:
                        results.extend(file_matches)
                        if len(results) >= max_results:
                            # Reached max results, stop processing
                            break
                except Exception as e:
                    logger.error(f"Error searching file {filepath}: {str(e)}")
        
        duration = time.time() - start_time
        logger.info(f"Local search complete: {file_count} files searched in {duration:.2f}s, {len(results)} matches")
        
        # Sort results by relevance (for now, just by filename)
        results.sort(key=lambda x: x['filepath'])
        
        return results[:max_results]
    
    def _search_file(self, filepath: str, pattern: re.Pattern) -> List[Dict[str, Any]]:
        """
        Search a single file for pattern matches.
        
        Args:
            filepath: Path to file
            pattern: Compiled regex pattern
            
        Returns:
            List of match dictionaries
        """
        matches = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            rel_path = os.path.relpath(filepath, os.getcwd())
            
            # Find all matches with line context
            lines = content.split('\n')
            for i, line in enumerate(lines):
                for match in pattern.finditer(line):
                    line_number = i + 1
                    
                    # Get context (a few lines before and after)
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 3)
                    context_lines = lines[context_start:context_end]
                    
                    matches.append({
                        'filepath': filepath,
                        'relative_path': rel_path,
                        'line_number': line_number,
                        'line_content': line,
                        'match_start': match.start(),
                        'match_end': match.end(),
                        'context': '\n'.join(context_lines)
                    })
        except Exception as e:
            logger.error(f"Error searching {filepath}: {str(e)}")
            
        return matches
    
    def build_index(self, directories: List[str]) -> bool:
        """
        Build search index for faster repeat searches.
        
        This follows the offline-first pattern:
        - Always works in offline mode
        - Doesn't depend on external services
        
        Args:
            directories: List of directories to index
            
        Returns:
            True if indexing started successfully
        """
        with self._lock:
            if self._indexing:
                logger.warning("Indexing already in progress")
                return False
            
            self._indexing = True
            
        # Start indexing in background thread
        threading.Thread(target=self._index_directories, args=(directories,), daemon=True).start()
        return True
    
    def _index_directories(self, directories: List[str]) -> None:
        """
        Index directories in the background.
        
        Args:
            directories: List of directories to index
        """
        try:
            # In a real implementation, this would build a proper index
            # For this demo, just collect file stats
            for directory in directories:
                if not os.path.exists(directory) or not os.path.isdir(directory):
                    continue
                    
                self._index_cache[directory] = {
                    'last_update': time.time(),
                    'files': []
                }
                
                for root, _, files in os.walk(directory):
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        try:
                            stats = os.stat(filepath)
                            self._index_cache[directory]['files'].append({
                                'path': filepath,
                                'size': stats.st_size,
                                'mtime': stats.st_mtime
                            })
                        except Exception:
                            pass
            
            logger.info(f"Indexed {sum(len(d['files']) for d in self._index_cache.values())} files")
        except Exception as e:
            logger.error(f"Error during indexing: {str(e)}")
        finally:
            with self._lock:
                self._indexing = False
    
    def is_indexing(self) -> bool:
        """Check if indexing is currently in progress."""
        with self._lock:
            return self._indexing
