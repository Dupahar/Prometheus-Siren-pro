# src/indexer/search.py
"""
Semantic Code Search: Find code by meaning, not just text matching.
This is the heart of Prometheus's debugging capability.
"""

from dataclasses import dataclass
from typing import Optional
from loguru import logger

from src.core.config import settings
from src.core.qdrant_client import qdrant_manager
from src.core.embeddings import embedding_engine


@dataclass
class SearchResult:
    """A code search result with relevance information."""
    file_path: str
    function_name: str
    qualified_name: str
    chunk_type: str
    start_line: int
    end_line: int
    score: float
    code_preview: str
    docstring: str
    
    @property
    def location(self) -> str:
        """Human-readable location string."""
        return f"{self.file_path}:{self.start_line}-{self.end_line}"
    
    def __str__(self) -> str:
        return f"[{self.score:.3f}] {self.qualified_name} @ {self.location}"


class CodeSearcher:
    """
    Semantic search over indexed codebases.
    
    Capabilities:
    - Natural language queries
    - Error-based search
    - Filtered search by file/type
    """
    
    def __init__(self, collection_name: Optional[str] = None):
        """Initialize the searcher."""
        self.collection_name = collection_name or settings.qdrant_code_collection
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        file_filter: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Search for code matching a natural language query.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
            file_filter: Filter by file path substring
            chunk_type: Filter by chunk type (function, class, method)
            
        Returns:
            List of SearchResult objects
        """
        # Generate query embedding
        query_vector = embedding_engine.embed_query(query)
        
        # Build filters
        filters = {}
        if chunk_type:
            filters["chunk_type"] = chunk_type
        
        # Search Qdrant
        results = qdrant_manager.search_similar(
            collection_name=self.collection_name,
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=min_score if min_score > 0 else None,
            filters=filters if filters else None,
        )
        
        # Convert to SearchResult objects
        search_results = []
        for hit in results:
            payload = hit["payload"]
            
            # Apply file filter if specified
            if file_filter and file_filter not in payload.get("file_path", ""):
                continue
            
            search_results.append(SearchResult(
                file_path=payload.get("file_path", ""),
                function_name=payload.get("function_name", ""),
                qualified_name=payload.get("qualified_name", ""),
                chunk_type=payload.get("chunk_type", ""),
                start_line=payload.get("start_line", 0),
                end_line=payload.get("end_line", 0),
                score=hit["score"],
                code_preview=payload.get("code_preview", ""),
                docstring=payload.get("docstring", ""),
            ))
        
        logger.debug(f"Search '{query[:50]}...' returned {len(search_results)} results")
        return search_results
    
    def search_by_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Search for code related to an error.
        
        This is the core of Prometheus's debugging capability.
        
        Args:
            error_type: Exception type (e.g., "ZeroDivisionError")
            error_message: Error message
            stack_trace: Full stack trace
            top_k: Number of results
            
        Returns:
            List of SearchResult objects ranked by relevance
        """
        # Build error-aware query
        query = f"""
Error debugging query:
Type: {error_type}
Message: {error_message}

Stack trace indicates:
{stack_trace[:1000]}
"""
        
        # Generate embedding using error-specific method
        query_vector = embedding_engine.embed_error(
            error=f"{error_type}: {error_message}",
            stack_trace=stack_trace,
        )
        
        # Search
        results = qdrant_manager.search_similar(
            collection_name=self.collection_name,
            query_vector=query_vector,
            top_k=top_k,
        )
        
        # Convert to SearchResult
        search_results = [
            SearchResult(
                file_path=hit["payload"].get("file_path", ""),
                function_name=hit["payload"].get("function_name", ""),
                qualified_name=hit["payload"].get("qualified_name", ""),
                chunk_type=hit["payload"].get("chunk_type", ""),
                start_line=hit["payload"].get("start_line", 0),
                end_line=hit["payload"].get("end_line", 0),
                score=hit["score"],
                code_preview=hit["payload"].get("code_preview", ""),
                docstring=hit["payload"].get("docstring", ""),
            )
            for hit in results
        ]
        
        logger.info(f"Error search for '{error_type}' returned {len(search_results)} results")
        return search_results
    
    def search_similar_functions(
        self,
        code: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Find functions similar to a given code snippet.
        
        Useful for:
        - Finding duplicate code
        - Finding related implementations
        - Code review assistance
        
        Args:
            code: Code snippet to find similar functions to
            top_k: Number of results
            
        Returns:
            List of similar code chunks
        """
        # Generate code embedding
        query_vector = embedding_engine.embed_code(code)
        
        # Search
        results = qdrant_manager.search_similar(
            collection_name=self.collection_name,
            query_vector=query_vector,
            top_k=top_k,
        )
        
        return [
            SearchResult(
                file_path=hit["payload"].get("file_path", ""),
                function_name=hit["payload"].get("function_name", ""),
                qualified_name=hit["payload"].get("qualified_name", ""),
                chunk_type=hit["payload"].get("chunk_type", ""),
                start_line=hit["payload"].get("start_line", 0),
                end_line=hit["payload"].get("end_line", 0),
                score=hit["score"],
                code_preview=hit["payload"].get("code_preview", ""),
                docstring=hit["payload"].get("docstring", ""),
            )
            for hit in results
        ]
    
    def get_full_code(self, result: SearchResult) -> str:
        """
        Get the full source code for a search result.
        
        Reads the actual file to get the complete, current code.
        """
        try:
            with open(result.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Extract the relevant lines (1-indexed to 0-indexed)
            start = max(0, result.start_line - 1)
            end = min(len(lines), result.end_line)
            
            return "".join(lines[start:end])
        except Exception as e:
            logger.error(f"Failed to read {result.file_path}: {e}")
            return result.code_preview


# Singleton instance
code_searcher = CodeSearcher()
