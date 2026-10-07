"""Local LLM Client for Ollama inference and structured prompt generation."""

import re
import httpx
from typing import List, Dict, Any, Optional, Tuple

OLLAMA_BASE_URL = "http://127.0.0.1:11434"


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, timeout_seconds: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    def check_connection(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List all models currently installed in Ollama."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return models
        except Exception:
            pass
        return []

    def build_prompt(
        self,
        repo_name: str,
        file_tree: str,
        extracted_files: List[Dict[str, str]]
    ) -> str:
        """Build a high-quality prompt for the local LLM to explain the repository."""
        files_section_parts = []
        for file in extracted_files:
            path = file["path"]
            content = file["content"]
            files_section_parts.append(f"--- File: {path} ---\n{content}\n")
        
        files_text = "\n".join(files_section_parts)

        prompt = f"""You are an expert AI software architect and technical explainer.
Analyze the following GitHub repository codebase and generate a simple, clear, and comprehensive explanation of what this repository does.

Repository Name: {repo_name}

Project Directory Structure:
```
{file_tree}
```

Extracted Source Code and Documentation:
{files_text}

IMPORTANT INSTRUCTIONS:
- Explain what the repository does in simple language that any developer or stakeholder can understand.
- Ground your explanation strictly on the provided codebase and architecture.
- You MUST format your response following this EXACT template:

Project Overview
[A concise 2-3 sentence overview explaining what this project is and its purpose.]

The application allows users to:
• [Key capability or feature 1]
• [Key capability or feature 2]
• [Key capability or feature 3]
• [Key capability or feature 4]

Main Technologies:
• [Technology/Framework/Library 1]
• [Technology/Framework/Library 2]
• [Technology/Framework/Library 3]

How it works:
[Explain the architecture and flow step-by-step: how user actions trigger the frontend, how the backend processes requests, how data is stored or retrieved, and how results return to the user.]
"""
        return prompt

    def generate(self, model_name: str, prompt: str) -> str:
        """Call Ollama API to generate completion."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_ctx": 8192,
            }
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Ollama API returned status {resp.status_code}: {resp.text}"
                )
            result = resp.json()
            return result.get("response", "").strip()

    @staticmethod
    def parse_explanation_sections(raw_text: str) -> Tuple[str, List[str], List[str], str]:
        """Parse structured sections from LLM output with robust regex fallbacks."""
        overview = ""
        features: List[str] = []
        technologies: List[str] = []
        how_it_works = ""

        # Normalize line endings
        text = raw_text.replace("\r\n", "\n")

        # Robust regex section markers
        # Project Overview
        m_overview = re.search(
            r"(?:#+\s*|\*{1,2}\s*)?Project Overview(?:\*{1,2})?:?\s*\n+([\s\S]*?)(?=(?:\n\s*(?:#+\s*|\*{1,2}\s*)?(?:The application allows users to|Key Capabilities|Key Features|Main Features|Main Technologies|How it works)|$))",
            text,
            re.IGNORECASE,
        )
        if m_overview:
            overview = m_overview.group(1).strip()

        # Features
        m_features = re.search(
            r"(?:#+\s*|\*{1,2}\s*)?(?:The application allows users to|Key Capabilities and Features|Key Capabilities|Key Features|Main Features)(?:\*{1,2})?:?\s*\n+([\s\S]*?)(?=(?:\n\s*(?:#+\s*|\*{1,2}\s*)?(?:Main Technologies|Technologies|How it works)|$))",
            text,
            re.IGNORECASE,
        )
        if m_features:
            features_block = m_features.group(1).strip()
            for line in features_block.split("\n"):
                line = line.strip()
                # Remove markdown bullets, asterisks, numbers
                if re.match(r"^([•\-\*]|\d+\.)\s+", line):
                    cleaned = re.sub(r"^([•\-\*]|\d+\.)\s+", "", line).strip()
                    cleaned = cleaned.strip("*_` ")
                    if cleaned:
                        features.append(cleaned)
                elif line and not line.startswith(("#", "**")) and not features:
                    features.append(line.strip("*_` "))

        # Technologies
        m_tech = re.search(
            r"(?:#+\s*|\*{1,2}\s*)?(?:Main Technologies|Technologies)(?:\*{1,2})?:?\s*\n+([\s\S]*?)(?=(?:\n\s*(?:#+\s*|\*{1,2}\s*)?(?:How it works|How It Works)|$))",
            text,
            re.IGNORECASE,
        )
        if m_tech:
            tech_block = m_tech.group(1).strip()
            for line in tech_block.split("\n"):
                line = line.strip()
                if re.match(r"^([•\-\*]|\d+\.)\s+", line):
                    cleaned = re.sub(r"^([•\-\*]|\d+\.)\s+", "", line).strip()
                    cleaned = cleaned.strip("*_` ")
                    if cleaned:
                        technologies.append(cleaned)
                elif line and not line.startswith(("#", "**")) and not technologies and "following technologies" not in line.lower():
                    technologies.append(line.strip("*_` "))

        # How it works
        m_how = re.search(
            r"(?:#+\s*|\*{1,2}\s*)?(?:How it works|How It Works)(?:\*{1,2})?:?\s*\n+([\s\S]*)$",
            text,
            re.IGNORECASE,
        )
        if m_how:
            how_it_works = m_how.group(1).strip()

        # Clean any remaining markdown header boundary noise
        overview = re.sub(r"^\*{1,2}\s*", "", overview).strip()
        how_it_works = re.sub(r"^\*{1,2}\s*", "", how_it_works).strip()

        # Fallbacks if regex missed anything
        if not overview and not features and not technologies and not how_it_works:
            overview = text
            how_it_works = "See raw explanation in the Raw Output tab."

        return overview, features, technologies, how_it_works
