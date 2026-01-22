# src/core/ast_parser.py
"""
AST Parser for Python Code Chunking.
Splits Python files into semantic units (functions, classes, methods).
This ensures embeddings represent complete, executable logic units.
"""

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from loguru import logger


@dataclass
class CodeChunk:
    """
    Represents a chunk of code (function, class, or method).
    
    Attributes:
        name: Name of the code unit (function/class/method name)
        code: Full source code of the chunk
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        chunk_type: Type of chunk (function, class, method)
        parent: Parent class name for methods
        docstring: Extracted docstring if available
        file_path: Source file path
        content_hash: SHA256 hash for change detection
    """
    name: str
    code: str
    start_line: int
    end_line: int
    chunk_type: str  # "function", "class", "method"
    parent: Optional[str] = None
    docstring: Optional[str] = None
    file_path: Optional[str] = None
    content_hash: str = field(default="")
    
    def __post_init__(self):
        """Calculate content hash after initialization."""
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.code.encode()).hexdigest()[:16]
    
    @property
    def qualified_name(self) -> str:
        """Get fully qualified name (e.g., 'ClassName.method_name')."""
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name
    
    @property
    def context_string(self) -> str:
        """Generate context string for embedding."""
        parts = [f"{self.chunk_type}: {self.qualified_name}"]
        if self.docstring:
            parts.append(f"Description: {self.docstring[:200]}")
        return " | ".join(parts)


class ASTParser:
    """
    Parses Python files into semantic code chunks using AST.
    
    Benefits of AST-aware chunking:
    - Each chunk is a complete, executable unit
    - No arbitrary line splits that break logic
    - Better semantic meaning in embeddings
    - Preserves docstrings and context
    """
    
    def parse_file(self, file_path: str | Path) -> list[CodeChunk]:
        """
        Parse a Python file into code chunks.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of CodeChunk objects
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.suffix == ".py":
            raise ValueError(f"Not a Python file: {file_path}")
        
        try:
            source = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(f"Failed to read {file_path} as UTF-8, trying latin-1")
            source = file_path.read_text(encoding="latin-1")
        
        return self.parse_source(source, str(file_path))
    
    def parse_source(self, source: str, file_path: str = "<unknown>") -> list[CodeChunk]:
        """
        Parse Python source code into code chunks.
        
        Args:
            source: Python source code
            file_path: Optional file path for metadata
            
        Returns:
            List of CodeChunk objects
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return []
        
        lines = source.splitlines()
        chunks = []
        
        for node in ast.walk(tree):
            chunk = self._node_to_chunk(node, lines, file_path)
            if chunk:
                chunks.append(chunk)
        
        # Sort by line number
        chunks.sort(key=lambda c: c.start_line)
        
        logger.debug(f"Parsed {len(chunks)} chunks from {file_path}")
        return chunks
    
    def _node_to_chunk(
        self,
        node: ast.AST,
        lines: list[str],
        file_path: str,
    ) -> Optional[CodeChunk]:
        """Convert an AST node to a CodeChunk if applicable."""
        
        # Handle top-level functions
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Check if it's a method (has a class parent)
            # We'll handle methods separately when parsing classes
            # This catches only top-level functions
            return self._create_function_chunk(node, lines, file_path, parent=None)
        
        # Handle classes (including their methods)
        if isinstance(node, ast.ClassDef):
            return self._create_class_chunk(node, lines, file_path)
        
        return None
    
    def _create_function_chunk(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
        file_path: str,
        parent: Optional[str] = None,
    ) -> CodeChunk:
        """Create a CodeChunk from a function/method node."""
        start_line = node.lineno
        end_line = self._get_end_line(node)
        
        # Extract the code
        code = "\n".join(lines[start_line - 1:end_line])
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        chunk_type = "method" if parent else "function"
        
        return CodeChunk(
            name=node.name,
            code=code,
            start_line=start_line,
            end_line=end_line,
            chunk_type=chunk_type,
            parent=parent,
            docstring=docstring,
            file_path=file_path,
        )
    
    def _create_class_chunk(
        self,
        node: ast.ClassDef,
        lines: list[str],
        file_path: str,
    ) -> CodeChunk:
        """Create a CodeChunk from a class node."""
        start_line = node.lineno
        end_line = self._get_end_line(node)
        
        # Extract the full class code
        code = "\n".join(lines[start_line - 1:end_line])
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        return CodeChunk(
            name=node.name,
            code=code,
            start_line=start_line,
            end_line=end_line,
            chunk_type="class",
            docstring=docstring,
            file_path=file_path,
        )
    
    def _get_end_line(self, node: ast.AST) -> int:
        """Get the end line of an AST node."""
        # Python 3.8+ has end_lineno
        if hasattr(node, "end_lineno") and node.end_lineno:
            return node.end_lineno
        
        # Fallback: find max line in children
        max_line = getattr(node, "lineno", 1)
        for child in ast.walk(node):
            child_line = getattr(child, "lineno", 0)
            child_end = getattr(child, "end_lineno", child_line)
            max_line = max(max_line, child_line, child_end)
        
        return max_line
    
    def get_methods_from_class(
        self,
        class_node: ast.ClassDef,
        lines: list[str],
        file_path: str,
    ) -> list[CodeChunk]:
        """
        Extract method chunks from a class.
        
        Useful when you want methods as separate chunks for finer-grained search.
        """
        methods = []
        
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk = self._create_function_chunk(
                    node, lines, file_path, parent=class_node.name
                )
                methods.append(chunk)
        
        return methods
    
    def parse_file_with_methods(self, file_path: str | Path) -> list[CodeChunk]:
        """
        Parse a file and extract methods as separate chunks.
        
        This provides finer-grained search at the method level.
        """
        file_path = Path(file_path)
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()
        
        chunks = []
        
        for node in ast.iter_child_nodes(tree):
            # Top-level functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk = self._create_function_chunk(node, lines, str(file_path))
                chunks.append(chunk)
            
            # Classes - extract both class and methods
            elif isinstance(node, ast.ClassDef):
                # Add the class itself
                class_chunk = self._create_class_chunk(node, lines, str(file_path))
                chunks.append(class_chunk)
                
                # Add individual methods
                method_chunks = self.get_methods_from_class(node, lines, str(file_path))
                chunks.extend(method_chunks)
        
        chunks.sort(key=lambda c: c.start_line)
        return chunks


# Singleton instance for easy import
ast_parser = ASTParser()
