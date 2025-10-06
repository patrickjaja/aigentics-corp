"""Load testing scenarios for AI Offer Agent.

This module defines Locust load tests for the main user flows:
- Conversation creation and messaging
- Offer generation and retrieval
- PDF download
- Admin approval workflow

Performance Targets (from plan.md):
- <30s offer generation
- <3s API response time
- 100 req/min API rate limit
- 1000 concurrent users

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    locust -f locustfile.py --host=http://localhost:8000 --users 1000 --spawn-rate 10
"""

import json
import logging
import random
import time
from typing import Dict, Any, Optional

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask

logger = logging.getLogger(__name__)


# Test data pools
COMPANY_NAMES = [
    "TechStart GmbH",
    "Digital Solutions AG",
    "Innovation Labs",
    "Future Systems",
    "CloudWorks"
]

PROJECT_TYPES = [
    "Web Application",
    "Mobile App",
    "API Integration",
    "Data Analytics Platform",
    "E-commerce System"
]

TECHNOLOGIES = [
    ["Python", "FastAPI", "PostgreSQL"],
    ["Node.js", "React", "MongoDB"],
    ["Java", "Spring Boot", "MySQL"],
    ["TypeScript", "Next.js", "Redis"],
    ["Go", "gRPC", "Kafka"]
]


class OfferAgentUser(HttpUser):
    """Simulates a user interacting with the AI Offer Agent system.

    This user follows a realistic workflow:
    1. Create a conversation
    2. Exchange messages with the AI
    3. Generate an offer
    4. Download the PDF
    5. (Optional) Trigger approval workflow for high-value offers
    """

    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks

    def on_start(self):
        """Initialize user session with authentication."""
        self.conversation_id: Optional[str] = None
        self.offer_id: Optional[str] = None
        self.customer_id: Optional[str] = None
        self.api_key: Optional[str] = None
        self.headers: Dict[str, str] = {}

        # Generate API key for this user
        self._create_api_key()

    def _create_api_key(self):
        """Create API key for load testing."""
        # In a real scenario, you'd authenticate properly
        # For load testing, we simulate with a test API key
        self.api_key = f"test_key_{self.environment.runner.user_count}_{random.randint(1000, 9999)}"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    @task(10)
    def create_and_run_conversation(self):
        """Complete conversation flow (highest weight - main user journey)."""
        # Step 1: Create conversation
        conversation_data = {
            "customer": {
                "company_name": random.choice(COMPANY_NAMES),
                "contact_email": f"test.user{random.randint(1, 10000)}@example.com",
                "contact_name": "Test User",
                "language": random.choice(["de", "en"])
            },
            "initial_message": "I need a custom software solution for my business."
        }

        with self.client.post(
            "/v1/conversations",
            json=conversation_data,
            headers=self.headers,
            catch_response=True,
            name="/v1/conversations [CREATE]"
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.conversation_id = data.get("conversation_id")
                self.customer_id = data.get("customer_id")
                response.success()
            else:
                response.failure(f"Failed to create conversation: {response.status_code}")
                raise RescheduleTask()

        # Step 2: Answer AI questions (simulate 3-5 rounds)
        rounds = random.randint(3, 5)
        for round_num in range(rounds):
            time.sleep(random.uniform(1, 3))  # Simulate user thinking

            message_data = {
                "message": self._generate_answer(round_num),
                "metadata": {
                    "round": round_num + 1
                }
            }

            with self.client.post(
                f"/v1/conversations/{self.conversation_id}/messages",
                json=message_data,
                headers=self.headers,
                catch_response=True,
                name="/v1/conversations/:id/messages [ANSWER]"
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "completed":
                        response.success()
                        break
                    response.success()
                else:
                    response.failure(f"Failed to send message: {response.status_code}")

    @task(8)
    def generate_and_retrieve_offer(self):
        """Generate offer and retrieve it (second most common flow)."""
        if not self.conversation_id:
            # Need conversation first
            self.create_and_run_conversation()

        # Generate offer
        offer_data = {
            "conversation_id": self.conversation_id,
            "project_type": random.choice(PROJECT_TYPES),
            "requirements": {
                "technologies": random.choice(TECHNOLOGIES),
                "timeline_weeks": random.randint(8, 24),
                "team_size": random.randint(2, 8)
            }
        }

        start_time = time.time()

        with self.client.post(
            "/v1/offers",
            json=offer_data,
            headers=self.headers,
            catch_response=True,
            name="/v1/offers [GENERATE]"
        ) as response:
            generation_time = time.time() - start_time

            if response.status_code == 201:
                data = response.json()
                self.offer_id = data.get("offer_id")

                # Check performance target: <30s
                if generation_time > 30:
                    response.failure(f"Offer generation too slow: {generation_time:.2f}s > 30s target")
                else:
                    response.success()

                # Log metrics
                events.request.fire(
                    request_type="METRIC",
                    name="offer_generation_time",
                    response_time=generation_time * 1000,
                    response_length=0,
                    exception=None,
                    context={}
                )
            else:
                response.failure(f"Failed to generate offer: {response.status_code}")
                raise RescheduleTask()

        # Retrieve the generated offer
        time.sleep(0.5)  # Small delay

        with self.client.get(
            f"/v1/offers/{self.offer_id}",
            headers=self.headers,
            catch_response=True,
            name="/v1/offers/:id [GET]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to retrieve offer: {response.status_code}")

    @task(5)
    def download_offer_pdf(self):
        """Download offer as PDF."""
        if not self.offer_id:
            # Need offer first
            self.generate_and_retrieve_offer()

        # GDPR consent required before download
        consent_data = {
            "customer_id": self.customer_id,
            "gdpr_consent": True,
            "consent_timestamp": time.time()
        }

        with self.client.post(
            f"/v1/offers/{self.offer_id}/download",
            json=consent_data,
            headers=self.headers,
            catch_response=True,
            name="/v1/offers/:id/download [PDF]"
        ) as response:
            if response.status_code == 200:
                # Verify PDF content
                if response.headers.get("Content-Type") == "application/pdf":
                    response.success()
                else:
                    response.failure("Expected PDF content type")
            else:
                response.failure(f"Failed to download PDF: {response.status_code}")

    @task(2)
    def admin_approval_workflow(self):
        """Simulate high-value offer approval workflow."""
        if not self.offer_id:
            self.generate_and_retrieve_offer()

        # Get pending approvals
        with self.client.get(
            "/v1/approvals/pending",
            headers=self.headers,
            catch_response=True,
            name="/v1/approvals/pending [LIST]"
        ) as response:
            if response.status_code == 200:
                response.success()
                approvals = response.json().get("approvals", [])

                if approvals:
                    # Review a random approval
                    approval_id = random.choice(approvals).get("approval_id")

                    review_data = {
                        "status": random.choice(["approved", "rejected"]),
                        "comments": "Load test approval",
                        "reviewer_id": f"manager_{random.randint(1, 5)}"
                    }

                    with self.client.post(
                        f"/v1/approvals/{approval_id}/review",
                        json=review_data,
                        headers=self.headers,
                        catch_response=True,
                        name="/v1/approvals/:id/review [SUBMIT]"
                    ) as review_response:
                        if review_response.status_code == 200:
                            review_response.success()
                        else:
                            review_response.failure(f"Failed to submit review: {review_response.status_code}")
            else:
                response.failure(f"Failed to get pending approvals: {response.status_code}")

    @task(1)
    def check_health(self):
        """Health check endpoint (low weight)."""
        with self.client.get(
            "/health",
            headers=self.headers,
            catch_response=True,
            name="/health [CHECK]"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("System not healthy")
            else:
                response.failure(f"Health check failed: {response.status_code}")

    def _generate_answer(self, round_num: int) -> str:
        """Generate realistic answer based on conversation round."""
        answers = {
            0: f"We need a {random.choice(PROJECT_TYPES)} for our business.",
            1: f"We want to use {', '.join(random.choice(TECHNOLOGIES))} technologies.",
            2: f"Our budget is around EUR {random.randint(50, 300)}k.",
            3: f"We need this completed in {random.randint(2, 6)} months.",
            4: "Yes, that sounds good. Let's proceed with the offer."
        }
        return answers.get(round_num, "Additional information as requested.")


class StressTestUser(HttpUser):
    """High-intensity stress test user for extreme load scenarios.

    This user hammers the API with rapid-fire requests to test:
    - Rate limiting (100 req/min)
    - Circuit breaker behavior
    - System degradation under stress
    """

    wait_time = between(0.1, 0.5)  # Very short wait times

    def on_start(self):
        """Initialize stress test user."""
        self.api_key = f"stress_test_{random.randint(10000, 99999)}"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    @task
    def rapid_fire_health_checks(self):
        """Rapid health checks to test rate limiting."""
        with self.client.get(
            "/health",
            headers=self.headers,
            catch_response=True,
            name="/health [STRESS]"
        ) as response:
            # We expect some 429 Too Many Requests responses
            if response.status_code in [200, 429]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    logger.info("="*60)
    logger.info("Starting load test for AI Offer Agent")
    logger.info(f"Target host: {environment.host}")
    logger.info("Performance Targets:")
    logger.info("  - Offer generation: <30s")
    logger.info("  - API response: <3s")
    logger.info("  - Rate limit: 100 req/min")
    logger.info("  - Concurrent users: 1000")
    logger.info("="*60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and summary."""
    logger.info("="*60)
    logger.info("Load test completed")
    logger.info("="*60)


# Performance monitoring custom metrics
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics tracking."""

    @events.request.add_listener
    def on_request(request_type, name, response_time, response_length, exception, **kwargs):
        """Track custom metrics for specific requests."""
        # Log slow requests (>3s target)
        if response_time > 3000 and request_type != "METRIC":
            logger.warning(
                f"Slow request detected: {name} took {response_time}ms (>3s target)"
            )

        # Track offer generation specifically
        if "offer_generation_time" in name:
            if response_time > 30000:
                logger.error(
                    f"Offer generation SLA violation: {response_time/1000:.2f}s (>30s)"
                )
