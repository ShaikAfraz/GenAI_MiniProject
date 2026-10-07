# 🧠 Local GitHub Repository Code Explainer

A full-stack, 100% local GenAI application that takes a public GitHub repository URL, clones it, processes the source code, and uses a locally running open-source LLM (via Ollama) to generate a simple-language architectural explanation.

---

## 🏗️ Architecture Pipeline

The application demonstrates the complete lifecycle of a real-world GenAI application:

```
[ GitHub Repo URL ]
        │
        ▼
[ Repository Processing (GitPython) ]
  • Shallow clone (depth=1)
  • Ignore build artifacts, binaries, and tests
  • Relevance scoring (Manifests -> Entrypoints -> Business Logic)
  • ASCII directory tree construction
        │
        ▼
[ Context Window Budgeting & Prompt Synthesis ]
  • Structured prompt with role instructions and exact output template
        │
        ▼
[ Local LLM Inference (Ollama) ]
  • Running locally (e.g., Llama 3.2 1B, Qwen 2.5, Phi 3)
  • Zero external API costs, private, offline
        │
        ▼
[ FastAPI Backend ]
  • Parses structured sections (Overview, Features, Tech, How it works)
  • REST endpoints for health, model listing, and repo analysis
        │
        ▼
[ Streamlit Frontend UI ]
  • Intuitive input interface, progress indicator, and tabs for:
    - Codebase Explanation
    - File Structure Hierarchy
    - Analyzed Source Files
    - Raw Model Response
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Local GenAI** | [Ollama](https://ollama.ai) (`llama3.2:1b`, `qwen2.5-coder:1.5b`, or `phi3:mini`) |
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com/), [Pydantic v2](https://docs.pydantic.dev/), [Uvicorn](https://www.uvicorn.org/) |
| **Repo Processing**| [GitPython](https://gitpython.readthedocs.io/), Python file handling |
| **Frontend UI** | [Streamlit](https://streamlit.io/) |

---

## 🚀 Quick Start Guide

### 1. Ensure Ollama is running and model is downloaded
Make sure Ollama is installed and running on your machine:
```bash
# Verify Ollama is running
ollama list

# Download the recommended lightweight model
ollama pull llama3.2:1b
```

### 2. Install Dependencies
```bash
cd /Users/shaikmohammedafrazhussain/.gemini/antigravity/scratch/repo-explainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Application
You can run both Backend and Frontend together using the provided script:
```bash
./run.sh
```

Or start them individually in separate terminal tabs:

**Terminal 1 (FastAPI Backend):**
```bash
./venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Streamlit Frontend):**
```bash
./venv/bin/streamlit run frontend/app.py --server.port 8501
```

Access the UI at: **`http://localhost:8501`**  
Access the Interactive API Swagger Docs at: **`http://127.0.0.1:8000/docs`**

---

## 🧪 Verification & Automated Testing

You can verify the end-to-end pipeline (cloning, context extraction, Ollama inference, and section parsing) by running:
```bash
./venv/bin/python test_pipeline.py
```

---

## 📋 API Endpoints

- **`GET /api/health`**: Checks API status and Ollama connectivity.
- **`GET /api/models`**: Lists all local LLM models installed in Ollama.
- **`POST /api/explain`**:
  - Request body:
    ```json
    {
      "repo_url": "https://github.com/pallets/flask",
      "model_name": "llama3.2:1b",
      "max_files": 25
    }
    ```
  - Response:
    ```json
    {
      "status": "success",
      "repo_url": "https://github.com/pallets/flask",
      "repo_name": "pallets/flask",
      "model_used": "llama3.2:1b",
      "overview": "...",
      "features": ["..."],
      "technologies": ["..."],
      "how_it_works": "...",
      "files_analyzed": ["..."],
      "file_tree": "...",
      "stats": { ... }
    }
    ```

---

## 📝 Example Output

**Input:**
```
https://github.com/example/expense-tracker
```

**Output:**
```
Project Overview
This project is an expense tracking application.

The application allows users to:
• Add expenses
• View previous expenses
• Categorize expenses
• Calculate total spending

Main Technologies:
• Python
• Flask
• SQLite

How it works:
The user interacts with the frontend.
The frontend sends requests to the Flask backend.
The backend stores expense information in SQLite.
The backend then sends the result back to the user.
```
