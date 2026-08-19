"""Gemini-powered test generation for Verix."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from models.investigation import (
    RepositoryInvestigationEvidence,
    RepositoryOutcomeKind,
)
from models.repository import RepositoryGenerationContext
from services.repository_investigation_prompt import (
    build_repository_investigation_prompt,
)
from services.repository_prompt import build_repository_test_prompt


MODEL_NAME = "gemini-3.5-flash"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
MAX_INVESTIGATION_EXPLANATION_CHARACTERS = 4_000


class GeminiLLMService:
    """Generate tests and evidence-grounded explanations with the Gemini API."""

    def __init__(self) -> None:
        load_dotenv(ENV_FILE)
        api_key = os.getenv("LLM_API_KEY")

        if not api_key:
            raise RuntimeError("LLM_API_KEY is not configured.")

        self.client = genai.Client(api_key=api_key)

    def generate_tests(self, code: str) -> str:
        """Return pytest tests for the supplied Python code."""
        prompt = f"""Generate pytest unit tests for the following Python code.

Return only the test code, without Markdown fences or explanation.
The submitted code is available as main.py. Import the functions or classes being
tested from main; do not leave an import commented out or assume an unspecified module.

Python code:
{code}
"""
        return self._generate_from_prompt(prompt)

    def generate_repository_tests(
        self, context: RepositoryGenerationContext
    ) -> str:
        """Return pytest tests for one selected repository source target."""
        prompt = build_repository_test_prompt(context)
        return self._generate_from_prompt(prompt)

    def generate_repository_investigation(
        self,
        *,
        outcome: RepositoryOutcomeKind,
        evidence: RepositoryInvestigationEvidence,
    ) -> str:
        """Explain one classified repository run without changing its outcome."""
        prompt = build_repository_investigation_prompt(
            outcome=outcome,
            evidence=evidence,
        )
        explanation = self._generate_from_prompt(prompt).strip()

        if len(explanation) <= MAX_INVESTIGATION_EXPLANATION_CHARACTERS:
            return explanation

        return (
            explanation[: MAX_INVESTIGATION_EXPLANATION_CHARACTERS - 3].rstrip()
            + "..."
        )

    def _generate_from_prompt(self, prompt: str) -> str:
        """Send one prepared prompt to Gemini and require a non-empty response."""
        try:
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
        except Exception:
            raise RuntimeError("Gemini could not generate a response.") from None

        if not isinstance(response.text, str) or not response.text.strip():
            raise RuntimeError("Gemini returned an empty response.")

        return response.text
