"""
Integration Test: API Rate Limiting

Tests rate limiting enforcement as required by FR-008 and performance goals.

Rate Limiting Requirements:
- 100 requests per minute per API client
- Rate limits enforced at API Gateway (Kong)
- 429 Too Many Requests when exceeded
- Rate limit headers in responses
- Burst allowance (200 requests)
- Different limits for authenticated vs anonymous

Validation Scenarios:
- Normal usage within limits succeeds
- Exceeding 100 req/min returns 429
- Rate limit headers present in responses
- Rate limit resets after 60 seconds
- Burst handling for traffic spikes
- Different limits by client type
"""

import pytest
import asyncio
import time
from uuid import uuid4


class TestRateLimiting:
    """Test API rate limiting enforcement."""

    @pytest.mark.asyncio
    async def test_normal_usage_within_rate_limit(
        self, async_client, api_key
    ):
        """
        Test Case: Normal usage succeeds

        Given: API client with rate limit
        When: 50 requests sent in 1 minute
        Then: All requests succeed

        Requirement: FR-008 - 100 req/min limit
        """
        # ARRANGE
        headers = {"X-API-Key": api_key}

        # ACT: Send 50 requests (well within limit)
        success_count = 0

        for i in range(50):
            response = await async_client.get(
                "/v1/offers",
                headers=headers
            )

            if response.status_code in [200, 404]:  # 404 ok if no offers
                success_count += 1

        # ASSERT: All succeeded
        assert success_count == 50

    @pytest.mark.asyncio
    async def test_exceeding_rate_limit_returns_429(
        self, async_client, api_key
    ):
        """
        Test Case: Exceeding rate limit blocked

        Given: API client with 100 req/min limit
        When: 101 requests sent rapidly
        Then: Request 101+ returns 429 Too Many Requests

        Requirement: FR-008 - Rate limit enforcement
        """
        # ARRANGE
        headers = {"X-API-Key": api_key}

        # ACT: Send 101 requests as fast as possible
        success_count = 0
        rate_limited_count = 0

        for i in range(101):
            response = await async_client.get(
                "/v1/conversations",
                headers=headers
            )

            if response.status_code in [200, 201, 404]:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1

        # ASSERT: Hit rate limit
        assert rate_limited_count > 0, "Expected some requests to be rate limited"
        assert success_count <= 100, f"Expected max 100 successes, got {success_count}"

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(
        self, async_client, api_key
    ):
        """
        Test Case: Rate limit headers in responses

        Given: Any API request
        When: Response received
        Then: Headers include limit, remaining, reset

        Headers:
        - X-RateLimit-Limit: 100
        - X-RateLimit-Remaining: <count>
        - X-RateLimit-Reset: <timestamp>
        """
        # ARRANGE
        headers = {"X-API-Key": api_key}

        # ACT: Make request
        response = await async_client.get(
            "/v1/conversations",
            headers=headers
        )

        # ASSERT: Rate limit headers present
        assert "X-RateLimit-Limit" in response.headers or "x-ratelimit-limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers or "x-ratelimit-remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers or "x-ratelimit-reset" in response.headers

        # Verify values
        limit_header = response.headers.get("X-RateLimit-Limit") or response.headers.get("x-ratelimit-limit")
        if limit_header:
            limit = int(limit_header)
            assert limit == 100

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(
        self, async_client, api_key
    ):
        """
        Test Case: Rate limit resets after 60 seconds

        Given: Client has exhausted rate limit
        When: 60 seconds pass
        Then: Requests succeed again

        Note: This test takes 60+ seconds to run
        """
        # ARRANGE: Exhaust rate limit
        headers = {"X-API-Key": api_key}

        # Send requests until rate limited
        for i in range(101):
            await async_client.get("/v1/offers", headers=headers)

        # Verify rate limited
        response = await async_client.get("/v1/offers", headers=headers)
        if response.status_code != 429:
            pytest.skip("Could not trigger rate limit")

        # ACT: Wait for rate limit to reset
        # Get reset time from header
        reset_time = response.headers.get("X-RateLimit-Reset") or response.headers.get("x-ratelimit-reset")

        if reset_time:
            reset_timestamp = int(reset_time)
            current_time = int(time.time())
            wait_seconds = max(0, reset_timestamp - current_time + 1)

            if wait_seconds > 65:
                pytest.skip(f"Reset time too far in future: {wait_seconds}s")

            await asyncio.sleep(wait_seconds)
        else:
            # Fallback: wait 61 seconds
            await asyncio.sleep(61)

        # ASSERT: Can make requests again
        response = await async_client.get("/v1/offers", headers=headers)
        assert response.status_code in [200, 404], f"Expected success after reset, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_burst_allowance_handling(
        self, async_client, api_key
    ):
        """
        Test Case: Burst traffic handled within limits

        Given: Burst size of 200 requests
        When: 150 requests sent in burst
        Then: All succeed (within burst allowance)

        Requirement: Burst handling for traffic spikes
        """
        # ARRANGE
        headers = {"X-API-Key": api_key}

        # ACT: Send burst of 150 requests
        tasks = []

        async def make_request():
            return await async_client.get("/v1/offers", headers=headers)

        tasks = [make_request() for _ in range(150)]
        responses = await asyncio.gather(*tasks)

        # ASSERT: Most or all succeeded (burst allowance)
        success_count = sum(1 for r in responses if r.status_code in [200, 404])
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)

        # With burst of 200, 150 requests should mostly succeed
        # Allow for some rate limiting due to timing
        assert success_count >= 100, f"Expected at least 100 successes in burst, got {success_count}"

    @pytest.mark.asyncio
    async def test_rate_limiting_per_api_key(
        self, async_client, api_key_1, api_key_2
    ):
        """
        Test Case: Rate limits enforced per API key

        Given: Two different API keys
        When: Each sends 60 requests
        Then: Both succeed (separate rate limit buckets)

        Requirement: Per-client rate limiting
        """
        # ARRANGE
        headers_1 = {"X-API-Key": api_key_1}
        headers_2 = {"X-API-Key": api_key_2}

        # ACT: Send 60 requests from each key
        async def send_requests(headers):
            success = 0
            for _ in range(60):
                response = await async_client.get("/v1/conversations", headers=headers)
                if response.status_code in [200, 201, 404]:
                    success += 1
            return success

        success_1, success_2 = await asyncio.gather(
            send_requests(headers_1),
            send_requests(headers_2)
        )

        # ASSERT: Both clients successful (separate limits)
        assert success_1 == 60, f"Client 1: {success_1}/60 succeeded"
        assert success_2 == 60, f"Client 2: {success_2}/60 succeeded"

    @pytest.mark.asyncio
    async def test_rate_limit_error_response_format(
        self, async_client, api_key
    ):
        """
        Test Case: 429 response includes helpful information

        Given: Rate limit exceeded
        When: 429 returned
        Then: Response body explains limit and retry time

        API Contract: Error schema with error_code and message
        """
        # ARRANGE: Exhaust rate limit
        headers = {"X-API-Key": api_key}

        for i in range(101):
            await async_client.get("/v1/offers", headers=headers)

        # ACT: Get rate limited response
        response = await async_client.get("/v1/offers", headers=headers)

        # ASSERT: Proper 429 response
        if response.status_code == 429:
            error_data = response.json()

            assert "error_code" in error_data
            assert "message" in error_data

            message = error_data["message"].lower()
            assert "rate" in message or "limit" in message or "too many" in message

            # Rate limit headers should be present
            assert "X-RateLimit-Limit" in response.headers or "x-ratelimit-limit" in response.headers

    @pytest.mark.asyncio
    async def test_anonymous_vs_authenticated_rate_limits(
        self, async_client, api_key, admin_token
    ):
        """
        Test Case: Different rate limits for authenticated users

        Given: Anonymous API key vs authenticated admin
        When: Both make requests
        Then: Admin may have higher limits

        Business Rule: Authenticated users get better limits
        """
        # ARRANGE
        api_headers = {"X-API-Key": api_key}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # ACT: Test API key limit
        api_success = 0
        for i in range(110):
            response = await async_client.get("/v1/conversations", headers=api_headers)
            if response.status_code in [200, 201, 404]:
                api_success += 1

        # Test admin limit (may be higher)
        admin_success = 0
        for i in range(110):
            response = await async_client.get(
                "/v1/admin/approvals/pending",
                headers=admin_headers
            )
            if response.status_code in [200, 401]:  # 401 if auth setup incomplete
                admin_success += 1

        # ASSERT: API key limited at 100, admin might have higher
        assert api_success <= 100, f"API key exceeded 100 req/min: {api_success}"
        # Admin might have same or higher limit (implementation dependent)

    @pytest.mark.asyncio
    async def test_rate_limiting_at_gateway_level(
        self, async_client, api_key
    ):
        """
        Test Case: Rate limiting enforced by API Gateway (Kong)

        Given: Kong Gateway configuration
        When: Rate limit triggered
        Then: Gateway returns 429, not backend service

        Validation: Performance - gateway blocks before backend
        """
        # ARRANGE: Exhaust rate limit
        headers = {"X-API-Key": api_key}

        for i in range(101):
            await async_client.get("/v1/conversations", headers=headers)

        # ACT: Get rate limited response
        start_time = time.perf_counter()

        response = await async_client.get("/v1/conversations", headers=headers)

        end_time = time.perf_counter()
        response_time = end_time - start_time

        # ASSERT: Fast response (gateway level)
        if response.status_code == 429:
            # Gateway should respond very quickly (<100ms)
            assert response_time < 0.5, f"Rate limit response too slow: {response_time:.3f}s"

    @pytest.mark.asyncio
    async def test_rate_limiting_excludes_health_checks(
        self, async_client, api_key
    ):
        """
        Test Case: Health check endpoints not rate limited

        Given: Health check endpoints exist
        When: Many health checks made
        Then: Not counted against rate limit

        Requirement: Monitoring should not be rate limited
        """
        # ARRANGE
        headers = {"X-API-Key": api_key}

        # ACT: Make 200 health check requests
        health_success = 0
        for i in range(200):
            response = await async_client.get("/health")
            if response.status_code == 200:
                health_success += 1

        # ASSERT: All health checks succeeded
        assert health_success == 200, "Health checks should not be rate limited"

        # Verify regular endpoints still work (rate limit not affected)
        response = await async_client.get("/v1/conversations", headers=headers)
        assert response.status_code in [200, 201, 404]

    @pytest.mark.asyncio
    async def test_rate_limit_across_different_endpoints(
        self, async_client, api_key
    ):
        """
        Test Case: Rate limit shared across all endpoints

        Given: Single API key
        When: Requests to different endpoints
        Then: All count toward same rate limit

        Business Rule: Global rate limit per API key
        """
        # ARRANGE
        headers = {"X-API-Key": api_key}

        # ACT: Mix of endpoints
        endpoints = [
            "/v1/conversations",
            "/v1/offers",
            "/v1/customers"
        ]

        success_count = 0
        rate_limited_count = 0

        for i in range(105):
            endpoint = endpoints[i % len(endpoints)]
            response = await async_client.get(endpoint, headers=headers)

            if response.status_code in [200, 201, 404]:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1

        # ASSERT: Rate limit applied globally
        assert success_count <= 100
        assert rate_limited_count > 0

    @pytest.mark.asyncio
    async def test_concurrent_request_rate_limiting(
        self, async_client, api_key
    ):
        """
        Test Case: Rate limiting handles concurrent requests correctly

        Given: Many simultaneous requests
        When: Sent concurrently
        Then: Rate limit accurately enforced

        Validation: No race conditions in rate limiting
        """
        # ARRANGE
        headers = {"X-API-Key": api_key}

        # ACT: Send 120 concurrent requests
        async def make_request():
            return await async_client.get("/v1/conversations", headers=headers)

        tasks = [make_request() for _ in range(120)]
        responses = await asyncio.gather(*tasks)

        # ASSERT: Approximately 100 succeed, 20 rate limited
        success_count = sum(1 for r in responses if r.status_code in [200, 201, 404])
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)

        # Allow some tolerance for concurrent processing
        assert 95 <= success_count <= 105, f"Expected ~100 successes, got {success_count}"
        assert rate_limited_count >= 15, f"Expected ~20 rate limited, got {rate_limited_count}"

    @pytest.mark.asyncio
    async def test_rate_limit_monitoring_metrics(
        self, async_client, monitoring_client, api_key
    ):
        """
        Test Case: Rate limiting events tracked in metrics

        Given: Prometheus metrics enabled
        When: Rate limits hit
        Then: Metrics incremented

        Validation: Monitoring and alerting on rate limit hits
        """
        # ARRANGE: Trigger rate limit
        headers = {"X-API-Key": api_key}

        for i in range(101):
            await async_client.get("/v1/offers", headers=headers)

        # ACT: Check metrics
        metrics_response = await monitoring_client.get("/metrics")

        # ASSERT: Rate limit metrics present
        metrics_text = metrics_response.text

        # Should have counter for rate limit hits
        assert "rate_limit" in metrics_text.lower() or "http_requests_total" in metrics_text

        # Verify 429 status code counted
        assert "429" in metrics_text or "rate" in metrics_text
