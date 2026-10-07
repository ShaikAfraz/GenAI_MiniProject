"""Automated end-to-end test for the Local GitHub Repository Code Explainer pipeline."""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.llm_client import OllamaClient
from backend.repo_processor import sanitize_repo_url, clone_repository, extract_codebase
import tempfile
import shutil

def run_tests():
    print("=" * 60)
    print("🔍 Testing Local GitHub Repository Code Explainer Pipeline")
    print("=" * 60)

    # 1. Test Ollama connectivity & model presence
    print("\n[Step 1] Checking Local Ollama & Models...")
    client = OllamaClient()
    connected = client.check_connection()
    assert connected, "❌ Ollama is not running on http://127.0.0.1:11434"
    models = client.list_models()
    print(f"  ✅ Connected to Ollama! Available models: {models}")
    assert any("llama3.2" in m for m in models), f"❌ llama3.2 not found in {models}"

    # 2. Test URL parsing
    print("\n[Step 2] Testing URL Sanitation...")
    url, repo_name = sanitize_repo_url("https://github.com/octocat/Hello-World.git/")
    assert url == "https://github.com/octocat/Hello-World"
    assert repo_name == "octocat/Hello-World"
    print(f"  ✅ URL sanitized: {url} (Repo Name: {repo_name})")

    # 3. Test Git Clone & Code Extraction
    print("\n[Step 3] Testing Git Clone & Code Extraction on 'octocat/Hello-World'...")
    temp_dir = tempfile.mkdtemp(prefix="test_clone_")
    try:
        clone_repository(url, temp_dir)
        print(f"  ✅ Cloned successfully into {temp_dir}")

        extracted_files, file_tree, stats = extract_codebase(temp_dir, max_files=10)
        print(f"  ✅ Extracted {len(extracted_files)} files.")
        print(f"  ✅ File tree:\n{file_tree}")
        print(f"  ✅ Stats: {stats}")
        assert len(extracted_files) > 0, "No files extracted!"

        # 4. Test Local LLM Inference
        print("\n[Step 4] Testing Local LLM Inference with llama3.2:1b...")
        prompt = client.build_prompt(repo_name, file_tree, extracted_files)
        model_name = "llama3.2:1b"
        print(f"  Prompt built ({len(prompt)} chars). Generating with {model_name}...")
        
        raw_response = client.generate(model_name, prompt)
        print("\n--- LLM Response ---")
        print(raw_response)
        print("--------------------")

        overview, features, techs, how_it_works = client.parse_explanation_sections(raw_response)
        print("\n[Step 5] Parsed Output Sections:")
        print(f"  • Overview: {overview[:120]}...")
        print(f"  • Features: {features}")
        print(f"  • Technologies: {techs}")
        print(f"  • How It Works: {how_it_works[:120]}...")

        assert overview, "Overview could not be parsed!"
        print("\n🎉 ALL PIPELINE TESTS PASSED!")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_tests()
