# src/core/__init__.py
"""Core foundation: Qdrant client, Gemini embeddings, AST parsing"""

from .config import settings
from .qdrant_client import QdrantManager
from .embeddings import EmbeddingEngine

__all__ = ["settings", "QdrantManager", "EmbeddingEngine"]
