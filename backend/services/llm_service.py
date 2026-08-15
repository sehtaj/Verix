"""Gemini-powered test generation for Verix."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from services.github_service import RepositoryGenerationContext
from services.repository_prompt import build_repository_test_prompt


MODEL_NAME = "gemini-3.5-flash"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class GeminiLLMService:
    """Generate Python unit tests with the Gemini API."""

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

    def _generate_from_prompt(self, prompt: str) -> str:
        """Send one prepared prompt to Gemini and require a non-empty response."""
        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        if not isinstance(response.text, str) or not response.text.strip():
            raise RuntimeError("Gemini returned an empty response.")

        return response.text
