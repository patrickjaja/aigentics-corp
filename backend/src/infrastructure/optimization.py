"""Database query optimization and connection pooling.

This module provides database optimization features:
- Connection pooling configuration
- Query optimization utilities
- Index management
- Query performance monitoring
- Prepared statement caching

Performance goals:
- <3s API response time
- Efficient connection reuse
- Optimized query execution plans
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from functools import wraps

from sqlalchemy import event, text, Index
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.sql import ClauseElement

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration with optimization settings."""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        echo_pool: bool = False,
    ):
        """Initialize database configuration.

        Args:
            database_url: PostgreSQL connection URL
            pool_size: Number of connections to maintain
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after seconds
            pool_pre_ping: Test connections before use
            echo: Log SQL statements
            echo_pool: Log connection pool events
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
        self.echo_pool = echo_pool


class DatabaseOptimizer:
    """Manages database optimization and connection pooling.

    Features:
    - Connection pooling with configurable size
    - Query performance monitoring
    - Automatic query logging for slow queries
    - Prepared statement management
    - Connection health checks
    """

    def __init__(self, config: DatabaseConfig):
        """Initialize database optimizer.

        Args:
            config: Database configuration
        """
        self.config = config
        self.engine: Optional[AsyncEngine] = None
        self.sessionmaker: Optional[async_sessionmaker] = None
        self._slow_query_threshold_ms: float = 1000.0  # 1 second
        self._query_stats: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize database engine and connection pool."""
        logger.info("Initializing database connection pool...")

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            self.config.database_url,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=self.config.pool_pre_ping,
            echo=self.config.echo,
            echo_pool=self.config.echo_pool,
            # Performance optimizations
            connect_args={
                "server_settings": {
                    "jit": "on",  # Enable JIT compilation
                    "application_name": "ai_offer_agent",
                },
                "command_timeout": 30,
            },
        )

        # Create session factory
        self.sessionmaker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
        )

        # Register event listeners
        self._register_event_listeners()

        # Test connection
        await self._test_connection()

        logger.info(
            f"Database connection pool initialized: "
            f"size={self.config.pool_size}, max_overflow={self.config.max_overflow}"
        )

    def _register_event_listeners(self) -> None:
        """Register SQLAlchemy event listeners for monitoring."""

        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Track query start time."""
            conn.info.setdefault("query_start_time", []).append(time.time())

        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries and collect statistics."""
            total_time = time.time() - conn.info["query_start_time"].pop()
            total_time_ms = total_time * 1000

            # Log slow queries
            if total_time_ms > self._slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected ({total_time_ms:.2f}ms):\n{statement[:200]}"
                )

            # Collect statistics
            query_key = statement[:100]  # First 100 chars as key
            if query_key not in self._query_stats:
                self._query_stats[query_key] = {
                    "count": 0,
                    "total_time_ms": 0,
                    "min_time_ms": float("inf"),
                    "max_time_ms": 0,
                }

            stats = self._query_stats[query_key]
            stats["count"] += 1
            stats["total_time_ms"] += total_time_ms
            stats["min_time_ms"] = min(stats["min_time_ms"], total_time_ms)
            stats["max_time_ms"] = max(stats["max_time_ms"], total_time_ms)

        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            """Configure connection on creation."""
            # Set connection parameters for optimal performance
            cursor = dbapi_conn.cursor()
            cursor.execute("SET statement_timeout = '30s'")  # 30 second timeout
            cursor.execute("SET idle_in_transaction_session_timeout = '60s'")
            cursor.close()

            logger.debug("New database connection established")

        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log connection checkout from pool."""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            """Log connection return to pool."""
            logger.debug("Connection returned to pool")

    async def _test_connection(self) -> None:
        """Test database connection."""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.scalar()
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    @asynccontextmanager
    async def get_session(self):
        """Get database session from pool.

        Yields:
            AsyncSession: Database session

        Example:
            async with optimizer.get_session() as session:
                result = await session.execute(query)
        """
        if not self.sessionmaker:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self.sessionmaker()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        """Close database connections and cleanup."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status.

        Returns:
            Dictionary with pool statistics
        """
        if not self.engine:
            return {"status": "not_initialized"}

        pool = self.engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
        }

    def get_query_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get query performance statistics.

        Returns:
            Dictionary mapping query prefixes to statistics
        """
        # Calculate averages
        stats_with_avg = {}
        for query_key, stats in self._query_stats.items():
            stats_with_avg[query_key] = {
                **stats,
                "avg_time_ms": stats["total_time_ms"] / stats["count"],
            }
        return stats_with_avg

    def reset_query_stats(self) -> None:
        """Reset query statistics."""
        self._query_stats.clear()
        logger.info("Query statistics reset")

    def set_slow_query_threshold(self, threshold_ms: float) -> None:
        """Set threshold for slow query logging.

        Args:
            threshold_ms: Threshold in milliseconds
        """
        self._slow_query_threshold_ms = threshold_ms
        logger.info(f"Slow query threshold set to {threshold_ms}ms")


# Optimization utilities

def monitor_query_performance(threshold_ms: float = 1000.0):
    """Decorator to monitor query performance.

    Args:
        threshold_ms: Log warning if query exceeds this time

    Example:
        @monitor_query_performance(threshold_ms=500)
        async def get_customer(session, customer_id):
            return await session.execute(query)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time_ms = (time.time() - start_time) * 1000

                if execution_time_ms > threshold_ms:
                    logger.warning(
                        f"Slow query in {func.__name__}: "
                        f"{execution_time_ms:.2f}ms (threshold: {threshold_ms}ms)"
                    )

                return result
            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Query error in {func.__name__} after "
                    f"{execution_time_ms:.2f}ms: {e}"
                )
                raise

        return wrapper

    return decorator


class IndexManager:
    """Manage database indexes for optimal query performance."""

    def __init__(self, engine: AsyncEngine):
        """Initialize index manager.

        Args:
            engine: SQLAlchemy async engine
        """
        self.engine = engine

    async def create_recommended_indexes(self) -> None:
        """Create recommended indexes for common query patterns.

        Based on the data model and common access patterns:
        - Customer lookups by email
        - Conversation lookups by customer and status
        - Offer lookups by conversation and status
        - Event sourcing timestamp queries
        - Approval workflow queries
        """
        indexes = [
            # Customer indexes
            "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)",
            "CREATE INDEX IF NOT EXISTS idx_customers_created ON customers(created_at DESC)",

            # Conversation indexes
            "CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_customer_status ON conversations(customer_id, status)",

            # Offer indexes
            "CREATE INDEX IF NOT EXISTS idx_offers_conversation ON offers(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status)",
            "CREATE INDEX IF NOT EXISTS idx_offers_value ON offers(total_value)",
            "CREATE INDEX IF NOT EXISTS idx_offers_created ON offers(created_at DESC)",

            # Event sourcing indexes (TimescaleDB hypertable)
            "CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events(aggregate_id, aggregate_type)",
            "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)",

            # Approval workflow indexes
            "CREATE INDEX IF NOT EXISTS idx_approvals_offer ON approvals(offer_id)",
            "CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status)",
            "CREATE INDEX IF NOT EXISTS idx_approvals_reviewer ON approvals(reviewer_id)",
            "CREATE INDEX IF NOT EXISTS idx_approvals_pending ON approvals(status) WHERE status = 'pending'",

            # API client rate limiting
            "CREATE INDEX IF NOT EXISTS idx_api_clients_key ON api_clients(api_key_hash)",
        ]

        async with self.engine.begin() as conn:
            for index_sql in indexes:
                try:
                    await conn.execute(text(index_sql))
                    logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")

        logger.info(f"Recommended indexes created: {len(indexes)} indexes")

    async def analyze_missing_indexes(self) -> List[Dict[str, Any]]:
        """Analyze query patterns and suggest missing indexes.

        Returns:
            List of suggested indexes with rationale
        """
        # Query PostgreSQL statistics to find sequential scans
        query = text("""
            SELECT
                schemaname,
                tablename,
                seq_scan,
                seq_tup_read,
                idx_scan,
                seq_tup_read / NULLIF(seq_scan, 0) as avg_seq_read
            FROM pg_stat_user_tables
            WHERE seq_scan > 0
            ORDER BY seq_tup_read DESC
            LIMIT 10
        """)

        async with self.engine.begin() as conn:
            result = await conn.execute(query)
            rows = result.fetchall()

            suggestions = []
            for row in rows:
                if row.idx_scan is None or row.seq_scan > row.idx_scan * 2:
                    suggestions.append({
                        "table": f"{row.schemaname}.{row.tablename}",
                        "sequential_scans": row.seq_scan,
                        "rows_read": row.seq_tup_read,
                        "index_scans": row.idx_scan or 0,
                        "recommendation": f"Consider adding index to {row.tablename}",
                    })

            return suggestions


# Global optimizer instance
_optimizer: Optional[DatabaseOptimizer] = None


async def get_database_optimizer(config: DatabaseConfig) -> DatabaseOptimizer:
    """Get or create global database optimizer.

    Args:
        config: Database configuration

    Returns:
        DatabaseOptimizer instance
    """
    global _optimizer
    if _optimizer is None:
        _optimizer = DatabaseOptimizer(config)
        await _optimizer.initialize()
    return _optimizer


async def shutdown_database_optimizer() -> None:
    """Shutdown global database optimizer."""
    global _optimizer
    if _optimizer:
        await _optimizer.close()
        _optimizer = None
