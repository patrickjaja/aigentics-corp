#!/usr/bin/env python3
"""Test connectivity to all infrastructure services."""

import asyncio
import sys


async def test_postgres():
    """Test PostgreSQL connection."""
    try:
        import asyncpg
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="offer_agent",
            password="secure_password",
            database="offer_agent"
        )
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        print("✓ PostgreSQL: Connected")
        print(f"  Version: {version.split(',')[0]}")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL: Failed - {e}")
        return False


async def test_redis():
    """Test Redis connection."""
    try:
        from redis.asyncio import Redis
        redis = Redis(host="localhost", port=6379, password="redis_password", decode_responses=True)
        pong = await redis.ping()
        info = await redis.info("server")
        await redis.aclose()
        print("✓ Redis: Connected")
        print(f"  Version: {info.get('redis_version', 'unknown')}")
        return True
    except Exception as e:
        print(f"✗ Redis: Failed - {e}")
        return False


def test_qdrant():
    """Test Qdrant connection."""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()
        print("✓ Qdrant: Connected")
        print(f"  Collections: {len(collections.collections)}")
        return True
    except Exception as e:
        print(f"✗ Qdrant: Failed - {e}")
        return False


async def main():
    """Run all connectivity tests."""
    print("Testing infrastructure connectivity...\n")
    
    results = await asyncio.gather(
        test_postgres(),
        test_redis(),
        return_exceptions=True
    )
    
    qdrant_result = test_qdrant()
    
    all_results = list(results) + [qdrant_result]
    
    print("\n" + "="*50)
    if all(all_results):
        print("✓ All services connected successfully!")
        return 0
    else:
        print("✗ Some services failed to connect")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
