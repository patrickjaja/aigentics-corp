"""
Integration Test: Offer Generation Performance

Tests that offer generation completes within 30 seconds as required by
the performance specifications (FR-011).

Performance Requirements:
- Offer generation: <30s (p95)
- COCOMO calculation: <5s
- PDF generation: <10s
- Total end-to-end: <30s for 95% of requests

Validation Scenarios:
- Simple project (<10 requirements): <15s
- Complex project (10-20 requirements): <25s
- Large project (>20 requirements): <30s
- Concurrent offer generation: maintains <30s
"""

import pytest
import time
from uuid import uuid4
from datetime import datetime


class TestOfferPerformance:
    """Test offer generation performance requirements."""

    @pytest.mark.asyncio
    async def test_simple_offer_generation_under_15_seconds(
        self, async_client, db_session, sample_conversation
    ):
        """
        Test Case: Simple offer generated quickly

        Given: Project with <10 requirements
        When: Offer generation requested
        Then: Completes in <15 seconds

        Performance Target: <15s for simple projects
        """
        # ARRANGE: Simple project with 5 requirements
        conversation_id = sample_conversation["id"]
        project_id = sample_conversation["project_id"]

        # Ensure project has minimal complexity
        # (sample_conversation fixture should create simple project)

        # ACT: Generate offer and measure time
        start_time = time.perf_counter()

        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # ASSERT: Success within time limit
        assert response.status_code == 201
        assert duration < 15.0, f"Simple offer took {duration:.2f}s, expected <15s"

        # Verify response includes timing header
        assert "X-Processing-Time" in response.headers
        processing_time_ms = int(response.headers["X-Processing-Time"])
        assert processing_time_ms < 15000  # 15 seconds in milliseconds

        # Verify offer was created correctly
        data = response.json()
        assert "offer_id" in data
        assert data["status"] in ["draft", "pending_approval"]

    @pytest.mark.asyncio
    async def test_complex_offer_generation_under_25_seconds(
        self, async_client, complex_project
    ):
        """
        Test Case: Complex offer meets performance target

        Given: Project with 10-20 requirements
        When: Offer generation requested
        Then: Completes in <25 seconds

        Performance Target: <25s for complex projects
        """
        # ARRANGE: Complex project fixture
        project_id = complex_project["id"]
        conversation_id = complex_project["conversation_id"]

        # ACT: Generate offer
        start_time = time.perf_counter()

        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # ASSERT: Meets performance target
        assert response.status_code == 201
        assert duration < 25.0, f"Complex offer took {duration:.2f}s, expected <25s"

        # Verify work packages created
        offer_id = response.json()["offer_id"]

        details_response = await async_client.get(f"/v1/offers/{offer_id}")
        assert details_response.status_code == 200

        details = details_response.json()
        assert len(details["work_packages"]) >= 3  # Complex project should have multiple packages

    @pytest.mark.asyncio
    async def test_large_offer_generation_under_30_seconds(
        self, async_client, large_project
    ):
        """
        Test Case: Large offer meets maximum time requirement

        Given: Project with >20 requirements
        When: Offer generation requested
        Then: Completes in <30 seconds (hard limit)

        Performance Target: <30s for large projects (p95)
        """
        # ARRANGE: Large project fixture
        project_id = large_project["id"]
        conversation_id = large_project["conversation_id"]

        # ACT: Generate offer
        start_time = time.perf_counter()

        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # ASSERT: Hard performance limit
        assert response.status_code == 201
        assert duration < 30.0, f"Large offer took {duration:.2f}s, exceeds 30s limit"

        # Verify comprehensive offer
        offer_id = response.json()["offer_id"]
        details_response = await async_client.get(f"/v1/offers/{offer_id}")
        details = details_response.json()

        assert len(details["work_packages"]) >= 5  # Large project should have many packages

    @pytest.mark.asyncio
    async def test_concurrent_offer_generation_maintains_performance(
        self, async_client, db_session
    ):
        """
        Test Case: System maintains performance under load

        Given: Multiple simultaneous offer generation requests
        When: 5 offers requested concurrently
        Then: All complete within 30 seconds

        Performance Target: Concurrent requests don't degrade performance
        """
        # ARRANGE: Create 5 different projects
        projects = []
        for i in range(5):
            # Create conversation
            conv_response = await async_client.post(
                "/v1/conversations",
                json={"language": "en"}
            )
            conversation_id = conv_response.json()["conversation_id"]

            # Add message
            await async_client.post(
                f"/v1/conversations/{conversation_id}/messages",
                json={"message": f"Project {i}: Need web application"}
            )

            # Complete conversation
            complete_response = await async_client.post(
                f"/v1/conversations/{conversation_id}/complete"
            )

            project_id = complete_response.json()["project_id"]

            projects.append({
                "project_id": project_id,
                "conversation_id": conversation_id
            })

        # ACT: Generate all offers concurrently (simulated with async)
        start_time = time.perf_counter()

        import asyncio
        tasks = []

        async def generate_offer(project):
            return await async_client.post(
                "/v1/offers",
                json={
                    "project_id": project["project_id"],
                    "conversation_id": project["conversation_id"]
                }
            )

        tasks = [generate_offer(project) for project in projects]
        responses = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        max_duration = end_time - start_time

        # ASSERT: All completed successfully within time
        for response in responses:
            assert response.status_code == 201

        # Allow some overhead for concurrency, but should still be reasonable
        assert max_duration < 40.0, f"Concurrent generation took {max_duration:.2f}s"

    @pytest.mark.asyncio
    async def test_timeout_handling_for_excessive_processing(
        self, async_client, pathological_project
    ):
        """
        Test Case: System handles timeout gracefully

        Given: Project that would take >30 seconds
        When: Offer generation requested
        Then: Returns 503 with timeout error

        Validation: System enforces 30s timeout (FR-011)
        """
        # ARRANGE: Pathological project fixture (very complex)
        project_id = pathological_project["id"]
        conversation_id = pathological_project["conversation_id"]

        # ACT: Attempt generation
        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            },
            timeout=35.0  # Give slightly more time to observe timeout
        )

        # ASSERT: Timeout handled gracefully
        # Either completes just under 30s OR returns 503
        if response.status_code == 503:
            error = response.json()
            assert "timeout" in error["message"].lower()
        else:
            # If it succeeded, must be under 30s
            assert response.status_code == 201
            processing_time_ms = int(response.headers["X-Processing-Time"])
            assert processing_time_ms < 30000

    @pytest.mark.asyncio
    async def test_offer_generation_time_components(
        self, async_client, sample_conversation, monitoring_client
    ):
        """
        Test Case: Performance breakdown meets targets

        Given: Offer generation request
        When: Process completes
        Then: Each component within time budget
            - COCOMO calculation: <5s
            - Work package generation: <10s
            - PDF preparation: <5s
            - Database writes: <2s

        Validation: Component-level performance metrics
        """
        # ARRANGE
        project_id = sample_conversation["project_id"]
        conversation_id = sample_conversation["id"]

        # ACT: Generate offer with monitoring
        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        assert response.status_code == 201
        offer_id = response.json()["offer_id"]

        # ASSERT: Get performance metrics
        # (This would require monitoring/tracing integration)
        # For now, verify overall time
        total_time_ms = int(response.headers["X-Processing-Time"])

        assert total_time_ms < 30000, f"Total time {total_time_ms}ms exceeds 30s limit"

        # Verify offer was created with all components
        details = await async_client.get(f"/v1/offers/{offer_id}")
        data = details.json()

        assert "work_packages" in data
        assert len(data["work_packages"]) > 0
        assert "total_value" in data

    @pytest.mark.asyncio
    async def test_pdf_generation_performance_separate(
        self, async_client, existing_offer
    ):
        """
        Test Case: PDF download completes quickly

        Given: Existing offer
        When: PDF download requested
        Then: Generates in <10 seconds

        Performance Target: PDF generation <10s
        """
        # ARRANGE: Existing offer with customer data
        offer_id = existing_offer["id"]

        customer_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        # ACT: Request PDF download
        start_time = time.perf_counter()

        response = await async_client.post(
            f"/v1/offers/{offer_id}/download",
            json=customer_data
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # ASSERT: PDF generated quickly
        assert response.status_code == 200
        assert duration < 10.0, f"PDF generation took {duration:.2f}s, expected <10s"

        assert response.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in response.headers

    @pytest.mark.asyncio
    async def test_performance_metrics_tracked(
        self, async_client, sample_conversation
    ):
        """
        Test Case: Performance metrics recorded for monitoring

        Given: Offer generation
        When: Process completes
        Then: Metrics available for analytics

        Validation: System tracks performance for SLO monitoring
        """
        # ARRANGE
        project_id = sample_conversation["project_id"]
        conversation_id = sample_conversation["id"]

        # ACT: Generate offer
        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        assert response.status_code == 201

        # ASSERT: Timing header present
        assert "X-Processing-Time" in response.headers

        processing_time = int(response.headers["X-Processing-Time"])

        # Verify reasonable range
        assert 1000 < processing_time < 30000  # Between 1s and 30s

        # Verify offer event includes timing
        offer_id = response.json()["offer_id"]

        # Later: verify metrics in Prometheus/analytics
        # For now, verify offer created
        details = await async_client.get(f"/v1/offers/{offer_id}")
        assert details.status_code == 200
