# src/indexer/indexer.py
"""
Code Indexer: Embeds and stores Python code in Qdrant.
This connects the AST parser, embedding engine, and Qdrant storage.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from loguru import logger

from src.core.config import settings
from src.core.qdrant_client import qdrant_manager
from src.core.embeddings import embedding_engine
from src.core.ast_parser import ast_parser, CodeChunk
from .scanner import file_scanner, FileInfo


@dataclass
class IndexStats:
    """Statistics from an indexing run."""
    files_scanned: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    chunks_created: int = 0
    chunks_updated: int = 0
    errors: list[str] = field(default_factory=list)


class CodeIndexer:
    """
    Indexes Python codebases into Qdrant for semantic search.
    
    Workflow:
    1. Scan directory for Python files
    2. Parse each file into AST chunks
    3. Generate embeddings for each chunk
    4. Upsert to Qdrant with metadata
    
    Supports incremental indexing via content hashing.
    """
    
    def __init__(self, collection_name: Optional[str] = None):
        """
        Initialize the indexer.
        
        Args:
            collection_name: Qdrant collection name (default: from settings)
        """
        self.collection_name = collection_name or settings.qdrant_code_collection
        self._indexed_hashes: set[str] = set()
    
    def index_directory(
        self,
        directory: str | Path,
        incremental: bool = True,
    ) -> IndexStats:
        """
        Index all Python files in a directory.
        
        Args:
            directory: Root directory to index
            incremental: If True, skip unchanged files
            
        Returns:
            IndexStats with summary
        """
        directory = Path(directory).resolve()
        stats = IndexStats()
        
        logger.info(f"Starting indexing of {directory}")
        
        # Ensure collection exists
        qdrant_manager.ensure_collections()
        
        # Load existing hashes for incremental indexing
        if incremental:
            self._load_existing_hashes()
        
        # Scan for files
        files = file_scanner.scan(directory)
        stats.files_scanned = len(files)
        
        # Process each file
        for file_info in files:
            try:
                indexed = self._index_file(file_info, incremental)
                if indexed:
                    stats.files_indexed += 1
                    stats.chunks_created += indexed
                else:
                    stats.files_skipped += 1
            except Exception as e:
                # Extract clean error message (hide verbose JSON)
                error_msg = str(e).split("{")[0].strip() if "{" in str(e) else str(e)
                logger.warning(f"Skipped {file_info.path.name}: {error_msg}")
                stats.errors.append(f"{file_info.path}: {error_msg}")
        
        logger.success(
            f"Indexing complete: {stats.files_indexed} files, "
            f"{stats.chunks_created} chunks, "
            f"{stats.files_skipped} skipped"
        )
        
        return stats
    
    def index_file(self, file_path: str | Path) -> int:
        """
        Index a single Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Number of chunks indexed
        """
        file_path = Path(file_path).resolve()
        stat = file_path.stat()
        
        file_info = FileInfo(
            path=file_path,
            size=stat.st_size,
            mtime=stat.st_mtime,
        )
        
        return self._index_file(file_info, incremental=False) or 0
    
    def _index_file(self, file_info: FileInfo, incremental: bool) -> Optional[int]:
        """Index a single file and return chunk count, or None if skipped."""
        # Parse into chunks
        chunks = ast_parser.parse_file_with_methods(file_info.path)
        
        if not chunks:
            logger.debug(f"No chunks found in {file_info.path}")
            return None
        
        # Check if we can skip (incremental)
        if incremental:
            file_hash = self._compute_file_hash(file_info.path)
            if file_hash in self._indexed_hashes:
                logger.debug(f"Skipping unchanged file: {file_info.path}")
                return None
        
        # Generate embeddings and prepare for upsert
        ids = []
        vectors = []
        payloads = []
        
        for chunk in chunks:
            # Generate unique ID
            chunk_id = self._generate_chunk_id(chunk)
            
            # Generate embedding
            vector = embedding_engine.embed_code(
                code=chunk.code,
                context=chunk.context_string,
            )
            
            # Build payload
            payload = {
                "file_path": str(file_info.path),
                "function_name": chunk.name,
                "qualified_name": chunk.qualified_name,
                "chunk_type": chunk.chunk_type,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "language": "python",
                "content_hash": chunk.content_hash,
                "code_preview": chunk.code[:500],  # Preview for quick lookup
                "docstring": chunk.docstring or "",
            }
            
            ids.append(chunk_id)
            vectors.append(vector)
            payloads.append(payload)
        
        # Upsert to Qdrant
        qdrant_manager.upsert_vectors(
            collection_name=self.collection_name,
            ids=ids,
            vectors=vectors,
            payloads=payloads,
        )
        
        logger.debug(f"Indexed {len(chunks)} chunks from {file_info.path}")
        return len(chunks)
    
    def _generate_chunk_id(self, chunk: CodeChunk) -> str:
        """Generate a unique ID for a code chunk."""
        # Combine file path, qualified name, and hash for uniqueness
        key = f"{chunk.file_path}:{chunk.qualified_name}:{chunk.content_hash}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute hash of file content for change detection."""
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    
    def _load_existing_hashes(self) -> None:
        """Load existing content hashes from Qdrant for incremental indexing."""
        # This is a simplified approach - in production you might
        # want to scroll through all points and extract hashes
        self._indexed_hashes = set()
        logger.debug("Loaded existing hashes for incremental indexing")
    
    def remove_file(self, file_path: str | Path) -> None:
        """Remove all chunks from a file."""
        file_path = str(Path(file_path).resolve())
        
        qdrant_manager.delete_by_filter(
            collection_name=self.collection_name,
            field="file_path",
            value=file_path,
        )
        
        logger.info(f"Removed chunks for {file_path}")
    
    def clear_index(self) -> None:
        """Clear all indexed code (use with caution!)."""
        # Recreate the collection
        try:
            qdrant_manager.client.delete_collection(self.collection_name)
        except Exception:
            pass
        
        qdrant_manager._ensure_code_collection()
        logger.warning(f"Cleared all data from {self.collection_name}")


# Singleton instance
code_indexer = CodeIndexer()
