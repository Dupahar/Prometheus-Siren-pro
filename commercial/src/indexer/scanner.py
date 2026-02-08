# src/indexer/scanner.py
"""
File System Scanner for Python Projects.
Recursively finds Python files while respecting common ignore patterns.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from loguru import logger


@dataclass
class FileInfo:
    """Information about a scanned file."""
    path: Path
    size: int
    mtime: float  # Modification time
    
    @property
    def relative_path(self) -> str:
        """Get the file path as a string."""
        return str(self.path)


class FileScanner:
    """
    Scans directories for Python files.
    
    Respects common ignore patterns:
    - __pycache__
    - .git
    - venv / .venv / env
    - node_modules
    - .egg-info directories
    """
    
    # Default directories to ignore
    DEFAULT_IGNORE_DIRS = {
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        "venv",
        ".venv",
        "env",
        ".env",
        "node_modules",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        ".eggs",
        "*.egg-info",
        ".idea",
        ".vscode",
    }
    
    # Default file patterns to ignore
    DEFAULT_IGNORE_FILES = {
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
    }
    
    def __init__(
        self,
        ignore_dirs: set[str] | None = None,
        ignore_files: set[str] | None = None,
    ):
        """
        Initialize the scanner.
        
        Args:
            ignore_dirs: Additional directories to ignore
            ignore_files: Additional file patterns to ignore
        """
        self.ignore_dirs = self.DEFAULT_IGNORE_DIRS.copy()
        if ignore_dirs:
            self.ignore_dirs.update(ignore_dirs)
        
        self.ignore_files = self.DEFAULT_IGNORE_FILES.copy()
        if ignore_files:
            self.ignore_files.update(ignore_files)
    
    def scan(self, root: str | Path) -> list[FileInfo]:
        """
        Scan a directory for Python files.
        
        Args:
            root: Root directory to scan
            
        Returns:
            List of FileInfo objects
        """
        root = Path(root).resolve()
        
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root}")
        
        if not root.is_dir():
            raise ValueError(f"Not a directory: {root}")
        
        files = list(self._scan_recursive(root))
        logger.info(f"Scanned {len(files)} Python files in {root}")
        
        return files
    
    def _scan_recursive(self, directory: Path) -> Iterator[FileInfo]:
        """Recursively scan a directory."""
        try:
            for entry in directory.iterdir():
                # Skip ignored directories
                if entry.is_dir():
                    if self._should_ignore_dir(entry.name):
                        continue
                    yield from self._scan_recursive(entry)
                
                # Process Python files
                elif entry.is_file() and entry.suffix == ".py":
                    if not self._should_ignore_file(entry.name):
                        try:
                            stat = entry.stat()
                            yield FileInfo(
                                path=entry,
                                size=stat.st_size,
                                mtime=stat.st_mtime,
                            )
                        except OSError as e:
                            logger.warning(f"Failed to stat {entry}: {e}")
        
        except PermissionError:
            logger.warning(f"Permission denied: {directory}")
    
    def _should_ignore_dir(self, name: str) -> bool:
        """Check if a directory should be ignored."""
        # Exact match
        if name in self.ignore_dirs:
            return True
        
        # Pattern match (for *.egg-info)
        for pattern in self.ignore_dirs:
            if pattern.startswith("*") and name.endswith(pattern[1:]):
                return True
        
        return False
    
    def _should_ignore_file(self, name: str) -> bool:
        """Check if a file should be ignored."""
        for pattern in self.ignore_files:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        
        return False


# Singleton instance
file_scanner = FileScanner()
