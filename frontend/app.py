"""Streamlit Frontend for Local GitHub Repository Code Explainer."""

import streamlit as st
import requests
import json
import time

# Configure page
st.set_page_config(
    page_title="GitHub Repo Code Explainer | Local GenAI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .pipeline-badge {
        display: inline-block;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        color: white;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
    .card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .metric-box {
        background-color: #EFF6FF;
        border-radius: 8px;
        padding: 0.75rem;
        text-align: center;
        border: 1px solid #BFDBFE;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Backend configuration
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"

# Sidebar: Controls & System Health
with st.sidebar:
    st.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=64)
    st.title("Settings & Status")
    
    backend_url = st.text_input(
        "Backend API URL",
        value=DEFAULT_BACKEND_URL,
        help="Endpoint where FastAPI server is running",
    )

    # Check Backend & Ollama Health
    health_status = "Disconnected"
    available_models = ["llama3.2:1b"]
    ollama_ok = False
    
    try:
        res = requests.get(f"{backend_url}/api/health", timeout=2.0)
        if res.status_code == 200:
            data = res.json()
            ollama_ok = data.get("ollama_connected", False)
            available_models = data.get("available_models", ["llama3.2:1b"])
            health_status = "Connected"
    except Exception:
        health_status = "Offline (Start FastAPI)"

    if health_status == "Connected":
        st.success(f"Backend: **{health_status}**")
        if ollama_ok:
            st.success(f"Local LLM: **Ollama Active**")
        else:
            st.warning("Ollama not responding on port 11434")
    else:
        st.error(f"Backend: **{health_status}**")

    st.markdown("---")
    st.subheader("🤖 Local Model Selection")
    
    selected_model = st.selectbox(
        "Choose Local LLM",
        options=available_models if available_models else ["llama3.2:1b"],
        index=0,
        help="Open-source LLM running completely on your device",
    )

    max_files = st.slider(
        "Max Files to Analyze",
        min_value=5,
        max_value=50,
        value=25,
        step=5,
        help="Limits the number of relevant source code files passed to LLM context",
    )

    st.markdown("---")
    st.markdown("### 💡 Quick Test Repos")
    sample_repos = {
        "Pallets / Click (CLI)": "https://github.com/pallets/click",
        "FastAPI Examples": "https://github.com/tiangolo/fastapi",
        "Flask (Web Framework)": "https://github.com/pallets/flask",
        "psf / Requests": "https://github.com/psf/requests",
    }
    for label, url in sample_repos.items():
        if st.button(f"Use {label}", use_container_width=True):
            st.session_state["repo_url_input"] = url

# Main Area
st.markdown('<div class="pipeline-badge">LOCAL GENAI APPLICATION</div>', unsafe_allow_html=True)
st.markdown('<div class="main-header">GitHub Repository Code Explainer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Clones a GitHub repository, parses its structure & source code, and uses a 100% local LLM to generate plain-language explanations.</div>',
    unsafe_allow_html=True,
)

# Pipeline Architecture Diagram
with st.expander("ℹ️ How This GenAI App Works (Architecture Pipeline)", expanded=False):
    st.markdown(
        """
        ```
        ┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
        │  GitHub Repo URL │ ──> │ Git Clone & Extract │ ──> │ Prompt Synthesis │
        └──────────────────┘     │ (GitPython + AST)   │     │ (Budgeted Context)│
                                 └─────────────────────┘     └─────────┬────────┘
                                                                       │
        ┌──────────────────┐     ┌─────────────────────┐               │
        │ Streamlit Web UI │ <── │  FastAPI Backend    │ <─────────────┘
        │ (Explanation)    │     │ (Parse & Structure) │     ┌──────────────────┐
        └──────────────────┘     └─────────────────────┘ <── │ Local Ollama LLM │
                                                             │ (Llama 3.2 1B)   │
                                                             └──────────────────┘
        ```
        1. **Repository Processing:** Clones shallow copy using `GitPython`, filters noise (tests, locks, images), scores relevance.
        2. **Code Extraction:** Extracts README, manifests, and core business files into a structured code context.
        3. **Local LLM:** Sends prompt to local Ollama running on device (`Llama 3.2 1B`).
        4. **Backend:** FastAPI coordinates workflow, error handling, and parses explanation sections.
        5. **Frontend:** Streamlit renders the structured results, file tree, and code preview.
        """
    )

# Input Section
default_url = st.session_state.get("repo_url_input", "https://github.com/pallets/click")

col_input, col_btn = st.columns([4, 1])
with col_input:
    repo_url = st.text_input(
        "Enter GitHub Repository URL:",
        value=default_url,
        placeholder="https://github.com/username/repository",
        help="Public repository URL from GitHub",
    )

with col_btn:
    st.write("")  # Vertical spacing
    st.write("")
    explain_clicked = st.button("🚀 Explain Repository", type="primary", use_container_width=True)

# Process & Display
if explain_clicked:
    if not repo_url or not repo_url.strip():
        st.error("Please enter a valid GitHub repository URL.")
    else:
        status_container = st.empty()
        progress_bar = st.progress(0)
        
        try:
            status_container.info("🔄 Step 1/3: Contacting backend and cloning repository...")
            progress_bar.progress(25)
            time.sleep(0.3)
            
            payload = {
                "repo_url": repo_url.strip(),
                "model_name": selected_model,
                "max_files": max_files,
            }
            
            status_container.info("🔍 Step 2/3: Filtering source files and constructing code context...")
            progress_bar.progress(50)
            
            # Send request to FastAPI backend
            start_time = time.time()
            response = requests.post(
                f"{backend_url}/api/explain",
                json=payload,
                timeout=240.0,
            )
            elapsed = time.time() - start_time
            
            progress_bar.progress(90)
            status_container.info("🧠 Step 3/3: Running local LLM inference...")
            
            if response.status_code != 200:
                err_msg = "Unknown error occurred"
                try:
                    err_data = response.json()
                    err_msg = err_data.get("detail", str(err_data))
                except Exception:
                    err_msg = response.text
                status_container.empty()
                progress_bar.empty()
                st.error(f"❌ Error: {err_msg}")
            else:
                progress_bar.progress(100)
                time.sleep(0.2)
                status_container.empty()
                progress_bar.empty()
                
                result = response.json()
                st.session_state["last_result"] = result
                st.session_state["last_elapsed"] = elapsed
                st.success(f"✅ Explanation generated successfully in {elapsed:.1f}s using local model **{result.get('model_used')}**!")
                
        except requests.exceptions.ConnectionError:
            status_container.empty()
            progress_bar.empty()
            st.error(f"Could not connect to FastAPI backend at `{backend_url}`. Please make sure the backend is running.")
        except Exception as e:
            status_container.empty()
            progress_bar.empty()
            st.error(f"An unexpected error occurred: {str(e)}")

# Render Results
if "last_result" in st.session_state:
    data = st.session_state["last_result"]
    elapsed = st.session_state.get("last_elapsed", 0.0)
    
    st.markdown("---")
    
    # Top Metrics
    stats = data.get("stats", {})
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Repository", data.get("repo_name", "Unknown"))
    with m2:
        st.metric("Model", data.get("model_used", "Local LLM"))
    with m3:
        st.metric("Files Analyzed", f"{stats.get('files_analyzed_count', len(data.get('files_analyzed', [])))}")
    with m4:
        st.metric("Inference Time", f"{elapsed:.1f}s")
        
    tab_explanation, tab_tree, tab_files, tab_raw = st.tabs([
        "📖 Codebase Explanation",
        "🌲 Repository Structure",
        "📂 Analyzed Files",
        "🔬 Raw LLM Response",
    ])
    
    with tab_explanation:
        # 1. Project Overview
        st.markdown("### 📌 Project Overview")
        overview = data.get("overview", "")
        if overview:
            st.info(overview)
        else:
            st.write("No overview section parsed.")

        col_left, col_right = st.columns([1, 1])
        
        # 2. Key Features
        with col_left:
            st.markdown("### 🎯 The application allows users to:")
            features = data.get("features", [])
            if features:
                for f in features:
                    st.markdown(f"• **{f}**")
            else:
                st.write("No specific features listed.")

        # 3. Technologies
        with col_right:
            st.markdown("### 🛠️ Main Technologies:")
            technologies = data.get("technologies", [])
            if technologies:
                for t in technologies:
                    st.markdown(f"• `{t}`")
            else:
                st.write("No technologies detected.")

        # 4. How It Works
        st.markdown("### ⚙️ How it works:")
        how_it_works = data.get("how_it_works", "")
        if how_it_works:
            st.markdown(how_it_works)
        else:
            st.write("No workflow details parsed.")
            
        # Download Markdown Report
        report_content = f"""# Codebase Explanation: {data.get('repo_name')}
Generated by Local GenAI Explainer ({data.get('model_used')})

## Project Overview
{overview}

## Features
{chr(10).join([f'- {item}' for item in features])}

## Main Technologies
{chr(10).join([f'- {tech}' for tech in technologies])}

## How it works
{how_it_works}

---
Repository: {data.get('repo_url')}
Files Analyzed: {len(data.get('files_analyzed', []))}
"""
        st.download_button(
            label="📥 Download Explanation Report (.md)",
            data=report_content,
            file_name=f"{data.get('repo_name', 'repo').replace('/', '_')}_explanation.md",
            mime="text/markdown",
        )

    with tab_tree:
        st.markdown("### 🌲 Project File Hierarchy")
        st.caption("Auto-generated directory tree filtering out build artifacts and external libraries:")
        file_tree = data.get("file_tree", "")
        st.code(file_tree, language="text")

    with tab_files:
        st.markdown("### 📂 Source Files Selected for Analysis")
        files_list = data.get("files_analyzed", [])
        st.caption(f"The smart code extractor selected {len(files_list)} priority files based on relevance scoring:")
        for idx, f in enumerate(files_list, 1):
            st.markdown(f"**{idx}.** `{f}`")

    with tab_raw:
        st.markdown("### 🔬 Exact LLM Output")
        st.caption("Direct response from local Ollama model without post-processing:")
        st.text_area(
            "Raw Text",
            value=data.get("raw_explanation", ""),
            height=300,
            disabled=True,
        )
