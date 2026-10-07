"""Pydantic schemas for the GitHub Repository Code Explainer API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class ExplainRequest(BaseModel):
    repo_url: str = Field(
        ...,
        description="Public GitHub repository URL (e.g., https://github.com/username/repository)",
        examples=["https://github.com/pallets/flask"],
    )
    model_name: Optional[str] = Field(
        default="llama3.2:1b",
        description="Name of the local Ollama LLM to use (e.g., llama3.2:1b, qwen2.5:1.5b)",
    )
    max_files: Optional[int] = Field(
        default=25,
        description="Maximum number of source code files to analyze",
    )


class ParsedExplanation(BaseModel):
    project_overview: str
    features: List[str]
    main_technologies: List[str]
    how_it_works: str


class ExplainResponse(BaseModel):
    status: str = "success"
    repo_url: str
    repo_name: str
    model_used: str
    overview: str
    features: List[str]
    technologies: List[str]
    how_it_works: str
    raw_explanation: str
    files_analyzed: List[str]
    file_tree: str
    stats: Dict[str, Any]


class ModelInfo(BaseModel):
    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None


class ModelsListResponse(BaseModel):
    models: List[str]
    default_model: str


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    available_models: List[str]
