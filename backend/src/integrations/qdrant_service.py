"""Qdrant vector search integration for requirement similarity.

This module provides vector search capabilities using Qdrant for:
- Finding similar requirements from historical projects
- Semantic search across project descriptions
- Clustering related work packages
- Recommendation of relevant past offers
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from ..infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)


@dataclass
class QdrantConfig:
    """Configuration for Qdrant service."""

    host: str = "localhost"
    port: int = 6333
    api_key: Optional[str] = None
    timeout: float = 30.0
    collection_name: str = "requirements"
    vector_size: int = 1536  # OpenAI embedding size
    distance_metric: str = "Cosine"
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


@dataclass
class SearchResult:
    """Result from vector search."""

    id: str
    score: float
    payload: Dict[str, Any]


class QdrantService:
    """Service for vector search operations with Qdrant.

    This service manages all interactions with Qdrant vector database,
    including:
    - Collection management
    - Vector indexing
    - Similarity search
    - Filtering and faceting
    """

    def __init__(self, config: QdrantConfig):
        """Initialize Qdrant service.

        Args:
            config: Qdrant configuration
        """
        self.config = config
        self.client = AsyncQdrantClient(
            host=config.host,
            port=config.port,
            api_key=config.api_key,
            timeout=config.timeout,
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout,
            name="qdrant",
        )

    async def ensure_collection(self) -> None:
        """Ensure the collection exists with proper schema.

        Creates the collection if it doesn't exist, with the configured
        vector size and distance metric.
        """
        try:
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for Qdrant")

            # Check if collection exists
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.config.collection_name not in collection_names:
                logger.info(
                    f"Creating Qdrant collection: {self.config.collection_name}"
                )

                await self.client.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.config.vector_size,
                        distance=models.Distance[self.config.distance_metric.upper()],
                    ),
                )

                # Create payload indexes for filtering
                await self._create_payload_indexes()

            await self.circuit_breaker.record_success()

        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.error(f"Failed to ensure Qdrant collection: {e}", exc_info=True)
            raise

    async def _create_payload_indexes(self) -> None:
        """Create indexes on payload fields for efficient filtering."""
        indexes = [
            ("project_type", models.PayloadSchemaType.KEYWORD),
            ("customer_id", models.PayloadSchemaType.KEYWORD),
            ("status", models.PayloadSchemaType.KEYWORD),
            ("created_at", models.PayloadSchemaType.DATETIME),
        ]

        for field_name, schema_type in indexes:
            try:
                await self.client.create_payload_index(
                    collection_name=self.config.collection_name,
                    field_name=field_name,
                    field_schema=schema_type,
                )
                logger.info(f"Created payload index on {field_name}")
            except UnexpectedResponse as e:
                # Index might already exist
                logger.debug(f"Payload index {field_name} may already exist: {e}")

    async def index_requirement(
        self,
        requirement_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Index a requirement with its embedding vector.

        Args:
            requirement_id: Unique ID for the requirement
            embedding: Vector embedding of the requirement text
            metadata: Additional metadata (project type, customer, etc.)
        """
        try:
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for Qdrant")

            point = models.PointStruct(
                id=requirement_id,
                vector=embedding,
                payload=metadata,
            )

            await self.client.upsert(
                collection_name=self.config.collection_name,
                points=[point],
            )

            logger.debug(f"Indexed requirement: {requirement_id}")
            await self.circuit_breaker.record_success()

        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.error(
                f"Failed to index requirement {requirement_id}: {e}",
                exc_info=True,
            )
            raise

    async def index_batch(
        self,
        requirements: List[tuple[str, List[float], Dict[str, Any]]],
    ) -> None:
        """Index multiple requirements in a batch.

        Args:
            requirements: List of (id, embedding, metadata) tuples
        """
        try:
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for Qdrant")

            points = [
                models.PointStruct(
                    id=req_id,
                    vector=embedding,
                    payload=metadata,
                )
                for req_id, embedding, metadata in requirements
            ]

            await self.client.upsert(
                collection_name=self.config.collection_name,
                points=points,
            )

            logger.info(f"Indexed batch of {len(requirements)} requirements")
            await self.circuit_breaker.record_success()

        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.error(f"Failed to index batch: {e}", exc_info=True)
            raise

    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar requirements.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filters: Optional filters on payload fields

        Returns:
            List of SearchResult objects
        """
        try:
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for Qdrant")

            # Build filter conditions
            query_filter = None
            if filters:
                conditions = []
                for field, value in filters.items():
                    conditions.append(
                        models.FieldCondition(
                            key=field,
                            match=models.MatchValue(value=value),
                        )
                    )
                query_filter = models.Filter(must=conditions)

            # Execute search
            results = await self.client.search(
                collection_name=self.config.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            await self.circuit_breaker.record_success()

            # Convert to SearchResult objects
            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload or {},
                )
                for result in results
            ]

        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.error(f"Vector search failed: {e}", exc_info=True)
            raise

    async def find_similar_requirements(
        self,
        requirement_text_embedding: List[float],
        project_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[SearchResult]:
        """Find similar requirements from historical projects.

        Args:
            requirement_text_embedding: Embedding of the requirement
            project_type: Optional filter by project type
            limit: Maximum results to return

        Returns:
            List of similar requirements
        """
        filters = {}
        if project_type:
            filters["project_type"] = project_type

        return await self.search_similar(
            query_vector=requirement_text_embedding,
            limit=limit,
            score_threshold=0.7,  # 70% similarity threshold
            filters=filters if filters else None,
        )

    async def recommend_work_packages(
        self,
        requirement_embeddings: List[List[float]],
        limit: int = 10,
    ) -> List[SearchResult]:
        """Recommend work packages based on multiple requirements.

        Args:
            requirement_embeddings: List of requirement embeddings
            limit: Maximum recommendations

        Returns:
            Recommended work packages from similar projects
        """
        # Average the embeddings to create a composite query
        if not requirement_embeddings:
            return []

        avg_embedding = [
            sum(emb[i] for emb in requirement_embeddings)
            / len(requirement_embeddings)
            for i in range(len(requirement_embeddings[0]))
        ]

        return await self.search_similar(
            query_vector=avg_embedding,
            limit=limit,
            score_threshold=0.6,
            filters={"status": "completed"},
        )

    async def delete_requirement(self, requirement_id: str) -> None:
        """Delete a requirement from the index.

        Args:
            requirement_id: ID of requirement to delete
        """
        try:
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for Qdrant")

            await self.client.delete(
                collection_name=self.config.collection_name,
                points_selector=models.PointIdsList(
                    points=[requirement_id],
                ),
            )

            logger.info(f"Deleted requirement: {requirement_id}")
            await self.circuit_breaker.record_success()

        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.error(
                f"Failed to delete requirement {requirement_id}: {e}",
                exc_info=True,
            )
            raise

    async def delete_by_customer(self, customer_id: str) -> None:
        """Delete all requirements for a customer (GDPR compliance).

        Args:
            customer_id: Customer ID
        """
        try:
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for Qdrant")

            await self.client.delete(
                collection_name=self.config.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="customer_id",
                                match=models.MatchValue(value=customer_id),
                            )
                        ]
                    )
                ),
            )

            logger.info(f"Deleted all requirements for customer: {customer_id}")
            await self.circuit_breaker.record_success()

        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.error(
                f"Failed to delete requirements for customer {customer_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for Qdrant")

            info = await self.client.get_collection(
                collection_name=self.config.collection_name
            )

            await self.circuit_breaker.record_success()

            return {
                "name": info.config.name,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "segments_count": info.segments_count,
                "status": info.status,
            }

        except Exception as e:
            await self.circuit_breaker.record_failure()
            logger.error(f"Failed to get collection stats: {e}", exc_info=True)
            raise

    async def health_check(self) -> bool:
        """Check if Qdrant service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to list collections
            await self.client.get_collections()
            return True

        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        await self.client.close()
