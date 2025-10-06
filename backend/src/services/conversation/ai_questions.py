"""
AI Question Generator

Generates contextual questions for requirement gathering using GPT-4.
Maximum 5 questions per round following progressive disclosure principles.
"""

from typing import Any, Dict, List, Optional
import os
from openai import AsyncOpenAI
import json


class AIQuestionGenerator:
    """Generates AI-powered questions for requirement gathering."""

    MAX_QUESTIONS_PER_ROUND = 5

    # Question templates by category
    QUESTION_TEMPLATES = {
        "project_type": [
            "What type of application are you looking to build?",
            "Is this a web application, mobile app, or something else?",
            "What is the primary platform for this project?",
        ],
        "tech_stack": [
            "Do you have any specific technology preferences?",
            "Are there existing systems this needs to integrate with?",
            "What technologies are you already using in your organization?",
        ],
        "team_size": [
            "How large is your development team?",
            "Will this be built by an internal team or external consultants?",
            "Do you have dedicated technical resources available?",
        ],
        "timeline": [
            "What is your target deadline for this project?",
            "How urgent is this requirement?",
            "When would you ideally like to launch?",
        ],
        "budget": [
            "Do you have a budget range in mind for this project?",
            "What is your investment capacity for this initiative?",
            "Are there any budget constraints we should be aware of?",
        ],
        "complexity": [
            "How many users do you expect to support?",
            "What are the most critical features for launch?",
            "Are there any complex integrations required?",
        ],
    }

    # Multi-language question templates
    INITIAL_QUESTIONS = {
        "en": [
            "Could you briefly describe the project you have in mind?",
            "What problem are you trying to solve with this project?",
            "Who are the primary users of this application?",
        ],
        "de": [
            "Könnten Sie das Projekt kurz beschreiben, das Sie planen?",
            "Welches Problem möchten Sie mit diesem Projekt lösen?",
            "Wer sind die Hauptnutzer dieser Anwendung?",
        ],
    }

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

    async def generate_initial_questions(
        self,
        language: str = "en"
    ) -> List[str]:
        """
        Generate initial questions to start conversation.

        Args:
            language: Language code (en, de, etc.)

        Returns:
            List of initial questions (max 3)
        """
        questions = self.INITIAL_QUESTIONS.get(language, self.INITIAL_QUESTIONS["en"])
        return questions[:3]  # Return first 3 questions

    async def generate_questions(
        self,
        context: Dict[str, Any],
        gathered_requirements: List[str],
        max_questions: int = MAX_QUESTIONS_PER_ROUND
    ) -> List[str]:
        """
        Generate contextual questions based on conversation progress.

        Args:
            context: Current conversation context
            gathered_requirements: Requirements gathered so far
            max_questions: Maximum questions to generate (default 5)

        Returns:
            List of questions (max 5)
        """
        # Get missing information categories
        missing_categories = self._identify_gaps(context, gathered_requirements)

        if not missing_categories:
            # If no gaps, ask refinement questions
            return await self._generate_refinement_questions(
                context,
                gathered_requirements,
                max_questions
            )

        # Generate questions for missing categories
        questions = await self._generate_category_questions(
            missing_categories,
            context,
            gathered_requirements,
            max_questions
        )

        return questions[:max_questions]

    def _identify_gaps(
        self,
        context: Dict[str, Any],
        gathered_requirements: List[str]
    ) -> List[str]:
        """Identify information gaps in conversation."""
        confidence_scores = context.get("confidence_scores", {})
        MIN_CONFIDENCE = 0.6

        gaps = [
            category
            for category, score in confidence_scores.items()
            if score < MIN_CONFIDENCE
        ]

        return gaps

    async def _generate_category_questions(
        self,
        missing_categories: List[str],
        context: Dict[str, Any],
        gathered_requirements: List[str],
        max_questions: int
    ) -> List[str]:
        """Generate questions for specific missing categories."""
        questions = []

        # Use templates for quick generation
        for category in missing_categories[:max_questions]:
            if category in self.QUESTION_TEMPLATES:
                template_questions = self.QUESTION_TEMPLATES[category]
                questions.append(template_questions[0])  # Use first template

        # If we need more questions, use GPT-4 for dynamic generation
        if len(questions) < max_questions and len(missing_categories) > 0:
            additional_questions = await self._generate_with_gpt4(
                missing_categories,
                context,
                gathered_requirements,
                max_questions - len(questions)
            )
            questions.extend(additional_questions)

        return questions[:max_questions]

    async def _generate_with_gpt4(
        self,
        missing_categories: List[str],
        context: Dict[str, Any],
        gathered_requirements: List[str],
        num_questions: int
    ) -> List[str]:
        """Use GPT-4 to generate contextual questions."""
        language = context.get("language", "en")

        # Build prompt
        prompt = self._build_question_prompt(
            missing_categories,
            gathered_requirements,
            language,
            num_questions
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert IT consultant gathering project requirements. "
                            "Ask clear, specific questions following progressive disclosure principles. "
                            "Never ask more than the requested number of questions. "
                            "Return questions as a JSON array."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            # Parse response
            result = json.loads(response.choices[0].message.content)
            questions = result.get("questions", [])

            return questions[:num_questions]

        except Exception as e:
            # Fallback to template questions
            print(f"GPT-4 question generation failed: {e}")
            return self._fallback_questions(missing_categories, num_questions)

    def _build_question_prompt(
        self,
        missing_categories: List[str],
        gathered_requirements: List[str],
        language: str,
        num_questions: int
    ) -> str:
        """Build prompt for GPT-4 question generation."""
        req_summary = "\n".join(f"- {req}" for req in gathered_requirements[-10:])

        prompt = f"""
Generate exactly {num_questions} questions to gather information about: {', '.join(missing_categories)}.

Context - Requirements gathered so far:
{req_summary if gathered_requirements else "No requirements gathered yet"}

Missing information categories:
{', '.join(missing_categories)}

Language: {language}

Requirements:
1. Generate EXACTLY {num_questions} questions (not more, not less)
2. Questions should be specific and actionable
3. Follow progressive disclosure - start simple, get detailed later
4. Use {language} language
5. Each question should target one missing category
6. Return as JSON: {{"questions": ["question1", "question2", ...]}}
"""
        return prompt

    async def _generate_refinement_questions(
        self,
        context: Dict[str, Any],
        gathered_requirements: List[str],
        max_questions: int
    ) -> List[str]:
        """Generate refinement questions when basic info is gathered."""
        language = context.get("language", "en")

        refinement_prompts = {
            "en": [
                "Are there any specific compliance requirements (GDPR, HIPAA, etc.)?",
                "What are the top 3 must-have features for the first release?",
                "Do you need support for multiple languages or regions?",
                "What level of scalability do you need?",
                "Are there any existing systems this needs to replace?",
            ],
            "de": [
                "Gibt es spezifische Compliance-Anforderungen (GDPR, HIPAA, etc.)?",
                "Was sind die 3 wichtigsten Features für die erste Version?",
                "Benötigen Sie Unterstützung für mehrere Sprachen oder Regionen?",
                "Welches Skalierungsniveau benötigen Sie?",
                "Gibt es bestehende Systeme, die ersetzt werden müssen?",
            ],
        }

        questions = refinement_prompts.get(language, refinement_prompts["en"])
        return questions[:max_questions]

    def _fallback_questions(
        self,
        missing_categories: List[str],
        num_questions: int
    ) -> List[str]:
        """Fallback to template questions if GPT-4 fails."""
        questions = []

        for category in missing_categories[:num_questions]:
            if category in self.QUESTION_TEMPLATES:
                questions.append(self.QUESTION_TEMPLATES[category][0])

        # Fill remaining with generic questions
        generic_questions = [
            "Could you provide more details about your project requirements?",
            "What are your main goals for this project?",
            "Are there any constraints we should be aware of?",
        ]

        while len(questions) < num_questions:
            questions.append(generic_questions[len(questions) % len(generic_questions)])

        return questions[:num_questions]

    async def translate_question(
        self,
        question: str,
        target_language: str
    ) -> str:
        """
        Translate question to target language using GPT-4.

        Args:
            question: Question in source language
            target_language: Target language code

        Returns:
            Translated question
        """
        if target_language == "en":
            return question  # Already in English

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Translate the following question to {target_language}. Keep it professional and formal (use 'Sie' form for German)."
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Translation failed: {e}")
            return question  # Return original if translation fails

    def validate_question_quality(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Validate question quality before presenting to user.

        Args:
            question: Generated question
            context: Current conversation context

        Returns:
            True if question meets quality criteria
        """
        # Check minimum length
        if len(question) < 10:
            return False

        # Check for question mark
        if not question.strip().endswith("?"):
            return False

        # Check not already asked
        answered_questions = context.get("answered_questions", [])
        if question in answered_questions:
            return False

        # Check for specificity (not too generic)
        generic_phrases = ["tell me more", "anything else", "what about"]
        if any(phrase in question.lower() for phrase in generic_phrases):
            return False

        return True
