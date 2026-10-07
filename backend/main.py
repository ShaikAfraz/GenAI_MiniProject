"""FastAPI Backend for GitHub Repository Code Explainer."""

import os
import shutil
import tempfile
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    ExplainRequest,
    ExplainResponse,
    ModelsListResponse,
    HealthResponse,
)
from .repo_processor import (
    sanitize_repo_url,
    clone_repository,
    extract_codebase,
)
from .llm_client import OllamaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repo_explainer")

app = FastAPI(
    title="Local GitHub Repository Code Explainer API",
    description="Backend API to clone GitHub repositories, extract code context, and generate plain-language explanations using a local LLM.",
    version="1.0.0",
)

# Enable CORS for Streamlit / external frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_client = OllamaClient()


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Local GitHub Repository Code Explainer API is running.",
        "docs_url": "/docs",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["General"])
def health_check():
    connected = llm_client.check_connection()
    models = llm_client.list_models() if connected else []
    return HealthResponse(
        status="healthy" if connected else "degraded",
        ollama_connected=connected,
        available_models=models,
    )


@app.get("/api/models", response_model=ModelsListResponse, tags=["LLM"])
def list_models():
    models = llm_client.list_models()
    default_model = "llama3.2:1b" if "llama3.2:1b" in models or "llama3.2:1b" in [m.split(":")[0] for m in models] else (models[0] if models else "llama3.2:1b")
    return ModelsListResponse(
        models=models,
        default_model=default_model,
    )


@app.post("/api/explain", response_model=ExplainResponse, tags=["Explainer"])
def explain_repository(request: ExplainRequest):
    repo_url = request.repo_url.strip()
    try:
        clean_url, repo_name = sanitize_repo_url(repo_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL: {str(e)}",
        )

    # Verify Ollama connection
    if not llm_client.check_connection():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local Ollama service is not reachable. Please ensure Ollama is running (`ollama serve`).",
        )

    # Check model availability
    available_models = llm_client.list_models()
    if not available_models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No local LLM models found in Ollama. Run `ollama pull llama3.2:1b` (or your preferred model).",
        )

    selected_model = request.model_name or "llama3.2:1b"
    # Fallback to match exact or base name
    matched_model = None
    for m in available_models:
        if m == selected_model or m.startswith(selected_model):
            matched_model = m
            break
    if not matched_model:
        matched_model = available_models[0]
        logger.warning(
            f"Requested model '{selected_model}' not found. Falling back to '{matched_model}'."
        )

    # Step 1: Clone Repository to temporary directory
    temp_dir = tempfile.mkdtemp(prefix="repo_explainer_")
    try:
        logger.info(f"Cloning {clean_url} into {temp_dir}...")
        try:
            clone_repository(clean_url, temp_dir)
        except Exception as e:
            logger.error(f"Git clone error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to clone repository: {str(e)}. Please check if the repository exists and is publicly accessible.",
            )

        # Step 2: Extract relevant code & build file tree
        logger.info("Extracting code and generating tree...")
        max_files = request.max_files or 25
        extracted_files, file_tree, stats = extract_codebase(
            repo_path=temp_dir,
            max_files=max_files,
        )

        if not extracted_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No readable source code or documentation files found in this repository.",
            )

        # Step 3: Build Prompt & Query Local LLM
        logger.info(f"Generating explanation using model '{matched_model}'...")
        prompt = llm_client.build_prompt(repo_name, file_tree, extracted_files)
        
        try:
            raw_explanation = llm_client.generate(matched_model, prompt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Local LLM inference failed: {str(e)}",
            )

        # Step 4: Parse structured output
        overview, features, technologies, how_it_works = llm_client.parse_explanation_sections(raw_explanation)

        files_analyzed = [f["path"] for f in extracted_files]

        return ExplainResponse(
            status="success",
            repo_url=clean_url,
            repo_name=repo_name,
            model_used=matched_model,
            overview=overview,
            features=features,
            technologies=technologies,
            how_it_works=how_it_works,
            raw_explanation=raw_explanation,
            files_analyzed=files_analyzed,
            file_tree=file_tree,
            stats=stats,
        )

    finally:
        # Clean up cloned files to preserve disk space
        shutil.rmtree(temp_dir, ignore_errors=True)
