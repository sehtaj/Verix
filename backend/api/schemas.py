"""Pydantic request schemas for the Verix API."""

from pydantic import BaseModel, Field


class GenerateTestsRequest(BaseModel):
    code: str = Field(min_length=1)


class RepositoryRequest(BaseModel):
    url: str = Field(min_length=1)
