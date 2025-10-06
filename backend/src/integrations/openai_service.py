"""OpenAI GPT-4 integration with streaming support.

This module provides an interface to OpenAI's GPT-4 API with support for:
- Streaming responses for real-time user feedback
- Fallback to GPT-3.5-turbo on failures
- Circuit breaker protection
- Token usage tracking
- Temperature and parameter configuration
"""

import logging
from typing import AsyncIterator, Dict, List, Optional, Any
from dataclasses import dataclass

import openai
from openai import AsyncOpenAI, OpenAIError

from ..infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI service."""

    api_key: str
    model: str = "gpt-4"
    fallback_model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: float = 30.0
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


class OpenAIService:
    """Service for interacting with OpenAI GPT-4 API.

    This service handles all communication with OpenAI's API, including:
    - Chat completions with streaming
    - Automatic fallback to cheaper models
    - Circuit breaker protection
    - Usage tracking and logging
    """

    def __init__(self, config: OpenAIConfig):
        """Initialize OpenAI service.

        Args:
            config: OpenAI configuration
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout,
        )
        self.usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
        """Generate chat completion from OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            AsyncIterator of response chunks if streaming, else full response

        Raises:
            CircuitBreakerError: If circuit breaker is open
            OpenAIError: If API call fails
        """
        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens

        self.usage_stats["total_requests"] += 1

        try:
            # Check circuit breaker
            if not await self.circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open for OpenAI service")

            # Try primary model (GPT-4)
            try:
                if stream:
                    return self._stream_completion(
                        messages=messages,
                        model=self.config.model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                else:
                    return await self._complete(
                        messages=messages,
                        model=self.config.model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

            except OpenAIError as e:
                logger.warning(
                    f"Primary model {self.config.model} failed: {e}, "
                    f"falling back to {self.config.fallback_model}"
                )

                # Fallback to GPT-3.5-turbo
                self.usage_stats["fallback_requests"] += 1

                if stream:
                    return self._stream_completion(
                        messages=messages,
                        model=self.config.fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                else:
                    return await self._complete(
                        messages=messages,
                        model=self.config.fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

        except Exception as e:
            self.usage_stats["failed_requests"] += 1
            await self.circuit_breaker.record_failure()
            logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            raise

    async def _complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """Execute non-streaming completion.

        Args:
            messages: Chat messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Complete response text
        """
        logger.info(f"Calling OpenAI {model} (non-streaming)")

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )

        # Track usage
        if response.usage:
            self.usage_stats["total_tokens"] += response.usage.total_tokens
            cost = self._estimate_cost(model, response.usage.total_tokens)
            self.usage_stats["total_cost"] += cost

            logger.info(
                f"OpenAI completion: {response.usage.total_tokens} tokens, "
                f"~${cost:.4f}"
            )

        self.usage_stats["successful_requests"] += 1
        await self.circuit_breaker.record_success()

        return response.choices[0].message.content

    async def _stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> AsyncIterator[str]:
        """Execute streaming completion.

        Args:
            messages: Chat messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Yields:
            Response chunks as they arrive
        """
        logger.info(f"Calling OpenAI {model} (streaming)")

        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        tokens_generated = 0

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                tokens_generated += len(content.split())  # Rough estimate
                yield content

        # Track usage (estimate since streaming doesn't return usage)
        estimated_tokens = tokens_generated * 1.3  # Account for prompt
        self.usage_stats["total_tokens"] += int(estimated_tokens)
        cost = self._estimate_cost(model, int(estimated_tokens))
        self.usage_stats["total_cost"] += cost

        logger.info(
            f"OpenAI streaming completion: ~{estimated_tokens} tokens, "
            f"~${cost:.4f}"
        )

        self.usage_stats["successful_requests"] += 1
        await self.circuit_breaker.record_success()

    async def generate_questions(
        self,
        context: str,
        max_questions: int = 5,
        language: str = "en",
    ) -> List[str]:
        """Generate clarifying questions based on context.

        Args:
            context: Current conversation context
            max_questions: Maximum number of questions to generate
            language: Target language for questions

        Returns:
            List of generated questions
        """
        system_prompt = f"""You are an AI assistant helping gather requirements for IT consulting offers.
Generate up to {max_questions} clarifying questions based on the context.
Questions should be specific, relevant, and help scope the project.
Respond in {language}."""

        user_prompt = f"""Context: {context}

Generate {max_questions} clarifying questions to better understand the project requirements."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.chat_completion(
            messages=messages,
            temperature=0.8,  # Higher creativity for questions
            stream=False,
        )

        # Parse questions from response (assuming numbered list)
        questions = [
            line.strip().lstrip("0123456789.- ")
            for line in response.split("\n")
            if line.strip() and any(c.isalpha() for c in line)
        ]

        return questions[:max_questions]

    async def extract_requirements(
        self,
        conversation_history: List[Dict[str, str]],
    ) -> List[str]:
        """Extract structured requirements from conversation.

        Args:
            conversation_history: List of conversation messages

        Returns:
            List of extracted requirements
        """
        system_prompt = """You are an AI assistant that extracts structured requirements from conversations.
Analyze the conversation and extract clear, actionable requirements.
Each requirement should be specific and testable."""

        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {"role": "user", "content": "Extract all requirements discussed so far."},
        ]

        response = await self.chat_completion(
            messages=messages,
            temperature=0.3,  # Lower for more precise extraction
            stream=False,
        )

        # Parse requirements from response
        requirements = [
            line.strip().lstrip("0123456789.- ")
            for line in response.split("\n")
            if line.strip() and any(c.isalpha() for c in line)
        ]

        return requirements

    async def summarize_conversation(
        self,
        conversation_history: List[Dict[str, str]],
        max_length: int = 200,
    ) -> str:
        """Generate a summary of the conversation.

        Args:
            conversation_history: List of conversation messages
            max_length: Maximum words in summary

        Returns:
            Conversation summary
        """
        system_prompt = f"""Summarize the following conversation in no more than {max_length} words.
Focus on key requirements, constraints, and decisions."""

        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
        ]

        return await self.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=max_length * 2,  # Rough token estimate
            stream=False,
        )

    def _estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate API call cost based on model and tokens.

        Args:
            model: Model name
            tokens: Total tokens used

        Returns:
            Estimated cost in USD
        """
        # Pricing as of 2024 (approximate)
        pricing = {
            "gpt-4": 0.03 / 1000,  # $0.03 per 1K tokens (blended)
            "gpt-4-turbo": 0.01 / 1000,  # $0.01 per 1K tokens
            "gpt-3.5-turbo": 0.002 / 1000,  # $0.002 per 1K tokens
        }

        # Find matching model price
        for model_prefix, price_per_token in pricing.items():
            if model.startswith(model_prefix):
                return tokens * price_per_token

        # Default to GPT-4 pricing if unknown
        return tokens * pricing["gpt-4"]

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics.

        Returns:
            Dictionary with usage metrics
        """
        return self.usage_stats.copy()

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self.usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Simple completion to test connectivity
            messages = [{"role": "user", "content": "ping"}]

            await self.client.chat.completions.create(
                model=self.config.fallback_model,
                messages=messages,
                max_tokens=5,
            )

            return True

        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
