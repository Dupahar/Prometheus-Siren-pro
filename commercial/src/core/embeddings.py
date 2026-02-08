# src/core/embeddings.py
"""
Embedding Engine using Google Gemini API.
Converts code and text into semantic vectors for Qdrant storage.

Updated to use the new google.genai package (v1.59+).
"""

from typing import Optional
from loguru import logger
from google import genai
from google.genai.types import EmbedContentConfig

from .config import settings


class EmbeddingEngine:
    """
    Generates embeddings using Google Gemini API.
    
    Supports:
    - Text embeddings (for logs, attack patterns)
    - Code embeddings (AST-aware, preserves semantic meaning)
    - Batch processing for efficiency
    """
    
    def __init__(self):
        """Initialize Gemini API client."""
        self._client: Optional[genai.Client] = None
        self._initialized = False
        
    def _ensure_initialized(self) -> None:
        """Lazy initialization of Gemini API client."""
        if not self._initialized:
            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._initialized = True
            logger.info(f"Gemini API initialized with model: {settings.embedding_model}")
    
    @property
    def client(self) -> genai.Client:
        """Get the Gemini client, initializing if needed."""
        self._ensure_initialized()
        return self._client
    
    def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Input text to embed
            task_type: Embedding task type
                - RETRIEVAL_DOCUMENT: For storing documents
                - RETRIEVAL_QUERY: For search queries
                - SEMANTIC_SIMILARITY: For comparing texts
                
        Returns:
            Embedding vector (768 dimensions)
        """
        self._ensure_initialized()
        
        if not text.strip():
            raise ValueError("Cannot embed empty text")
        
        result = self.client.models.embed_content(
            model=settings.embedding_model,
            contents=text,
            config=EmbedContentConfig(task_type=task_type),
        )
        
        return result.embeddings[0].values
    
    def embed_code(
        self,
        code: str,
        context: Optional[str] = None,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[float]:
        """
        Generate embedding for code with optional context.
        
        Uses a code-aware prompt to improve semantic understanding.
        
        Args:
            code: Source code to embed
            context: Optional context (function name, docstring, etc.)
            task_type: Embedding task type
            
        Returns:
            Embedding vector (768 dimensions)
        """
        self._ensure_initialized()
        
        if not code.strip():
            raise ValueError("Cannot embed empty code")
        
        # Build code-aware prompt for better embeddings
        if context:
            prompt = f"""Python code with context:
Context: {context}

```python
{code}
```"""
        else:
            prompt = f"""Python code:

```python
{code}
```"""
        
        result = self.client.models.embed_content(
            model=settings.embedding_model,
            contents=prompt,
            config=EmbedContentConfig(task_type=task_type),
        )
        
        return result.embeddings[0].values
    
    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.
        
        Uses RETRIEVAL_QUERY task type for better search performance.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector (768 dimensions)
        """
        return self.embed_text(query, task_type="RETRIEVAL_QUERY")
    
    def embed_error(self, error: str, stack_trace: str) -> list[float]:
        """
        Generate embedding for an error context.
        
        Combines error message and stack trace for semantic search.
        
        Args:
            error: Error message
            stack_trace: Stack trace text
            
        Returns:
            Embedding vector (768 dimensions)
        """
        prompt = f"""Error Analysis:

Error: {error}

Stack Trace:
{stack_trace}
"""
        return self.embed_text(prompt, task_type="RETRIEVAL_QUERY")
    
    def embed_attack(self, payload: str, attack_type: Optional[str] = None) -> list[float]:
        """
        Generate embedding for an attack payload.
        
        Args:
            payload: Attack payload or command
            attack_type: Optional classification (sql_injection, xss, etc.)
            
        Returns:
            Embedding vector (768 dimensions)
        """
        if attack_type:
            prompt = f"""Security Attack Pattern:

Type: {attack_type}
Payload: {payload}
"""
        else:
            prompt = f"""Security Attack Pattern:

Payload: {payload}
"""
        return self.embed_text(prompt, task_type="RETRIEVAL_DOCUMENT")
    
    def embed_batch(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            task_type: Embedding task type
            
        Returns:
            List of embedding vectors
        """
        self._ensure_initialized()
        
        if not texts:
            return []
        
        # Filter empty texts
        valid_texts = [t for t in texts if t.strip()]
        if len(valid_texts) != len(texts):
            logger.warning(f"Skipped {len(texts) - len(valid_texts)} empty texts in batch")
        
        embeddings = []
        for text in valid_texts:
            embedding = self.embed_text(text, task_type)
            embeddings.append(embedding)
        
        return embeddings


# Singleton instance for easy import
embedding_engine = EmbeddingEngine()
