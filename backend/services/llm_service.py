"""Gemini-powered test generation for Verix."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


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

Python code:
{code}
"""
        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        return response.text
