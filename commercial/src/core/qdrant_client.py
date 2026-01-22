# src/core/qdrant_client.py
"""
Qdrant Vector Database Manager.
Handles connection, collection management, and vector operations.
This is the BRAIN of Prometheus-Siren.
"""

from typing import Any, Optional
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)

from .config import settings


class QdrantManager:
    """
    Manages Qdrant vector database operations.
    
    Responsibilities:
    - Connection management
    - Collection creation (code_base, attack_memory)
    - Vector CRUD operations
    - Semantic search
    """
    
    def __init__(self):
        """Initialize Qdrant client with configured settings."""
        self._client: Optional[QdrantClient] = None
        
    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client (lazy initialization)."""
        if self._client is None:
            # Try cloud connection first, fall back to in-memory
            if settings.qdrant_has_api_key and settings.qdrant_url:
                try:
                    logger.info(f"Connecting to Qdrant Cloud...")
                    self._client = QdrantClient(
                        url=settings.qdrant_url,
                        api_key=settings.qdrant_api_key,
                        timeout=10,
                    )
                    # Test connection
                    self._client.get_collections()
                    logger.success("Connected to Qdrant Cloud successfully")
                except Exception as e:
                    logger.warning(f"Qdrant Cloud connection failed: {e}")
                    logger.info("Falling back to in-memory Qdrant...")
                    self._client = QdrantClient(":memory:")
                    logger.success("Using in-memory Qdrant (demo mode)")
            elif settings.qdrant_url and not settings.qdrant_url.startswith(":"):
                try:
                    logger.info(f"Connecting to Qdrant at {settings.qdrant_url}")
                    self._client = QdrantClient(url=settings.qdrant_url)
                    self._client.get_collections()
                    logger.success("Connected to Qdrant successfully")
                except Exception as e:
                    logger.warning(f"Qdrant connection failed: {e}")
                    self._client = QdrantClient(":memory:")
                    logger.success("Using in-memory Qdrant (demo mode)")
            else:
                # Default to in-memory for demo
                logger.info("Using in-memory Qdrant...")
                self._client = QdrantClient(":memory:")
                logger.success("In-memory Qdrant ready")
            
        return self._client
    
    def ensure_collections(self) -> None:
        """
        Ensure required collections exist with proper schemas.
        Creates them if they don't exist.
        """
        self._ensure_code_collection()
        self._ensure_attack_collection()
        logger.success("All collections verified/created")
    
    def _ensure_code_collection(self) -> None:
        """Create the code_base collection if it doesn't exist."""
        collection_name = settings.qdrant_code_collection
        
        if self._collection_exists(collection_name):
            logger.debug(f"Collection '{collection_name}' already exists")
            return
            
        logger.info(f"Creating collection: {collection_name}")
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        
        # Create payload indexes for efficient filtering
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="file_path",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="function_name",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="language",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        logger.success(f"Created collection: {collection_name}")
    
    def _ensure_attack_collection(self) -> None:
        """Create the attack_memory collection if it doesn't exist."""
        collection_name = settings.qdrant_attack_collection
        
        if self._collection_exists(collection_name):
            logger.debug(f"Collection '{collection_name}' already exists")
            return
            
        logger.info(f"Creating collection: {collection_name}")
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        
        # Create payload indexes for attack filtering
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="attack_type",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="threat_level",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="session_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        logger.success(f"Created collection: {collection_name}")
    
    def _collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        try:
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False
    
    # ==========================================
    # VECTOR OPERATIONS
    # ==========================================
    
    def upsert_vectors(
        self,
        collection_name: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> None:
        """
        Insert or update vectors in a collection.
        
        Args:
            collection_name: Target collection
            ids: Unique identifiers for each vector
            vectors: Embedding vectors
            payloads: Metadata for each vector
        """
        if len(ids) != len(vectors) or len(ids) != len(payloads):
            raise ValueError("ids, vectors, and payloads must have the same length")
        
        points = [
            PointStruct(
                id=id_,
                vector=vector,
                payload=payload,
            )
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]
        
        self.client.upsert(
            collection_name=collection_name,
            points=points,
        )
        
        logger.debug(f"Upserted {len(points)} vectors to '{collection_name}'")
    
    def search_similar(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of matches with id, score, and payload
        """
        # Build filter if provided
        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
                for key, value in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)
        
        try:
            # Try newer API (qdrant-client >= 1.7)
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
            ).points
        except AttributeError:
            # Fallback to older API
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
            )
        
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]
    
    def delete_vectors(
        self,
        collection_name: str,
        ids: list[str],
    ) -> None:
        """Delete vectors by ID."""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=ids),
        )
        logger.debug(f"Deleted {len(ids)} vectors from '{collection_name}'")
    
    def delete_by_filter(
        self,
        collection_name: str,
        field: str,
        value: Any,
    ) -> None:
        """Delete vectors matching a filter."""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=value),
                        )
                    ]
                )
            ),
        )
        logger.debug(f"Deleted vectors where {field}={value} from '{collection_name}'")
    
    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(collection_name)
            # Handle different qdrant-client versions
            vectors_count = getattr(info, 'vectors_count', 0) or 0
            points_count = getattr(info, 'points_count', 0) or 0
            status = getattr(info, 'status', 'unknown')
            return {
                "name": collection_name,
                "vectors_count": vectors_count,
                "points_count": points_count,
                "status": str(status),
            }
        except Exception as e:
            logger.warning(f"Could not get collection info: {e}")
            return {
                "name": collection_name,
                "vectors_count": 0,
                "points_count": 0,
                "status": "unknown",
            }
    
    def close(self) -> None:
        """Close the Qdrant connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Qdrant connection closed")


# Singleton instance for easy import
qdrant_manager = QdrantManager()
