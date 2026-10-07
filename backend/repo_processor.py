"""Repository processor: clones GitHub repos, filters source files, and extracts code context."""

import os
import shutil
import tempfile
import re
from typing import List, Dict, Tuple, Optional
import git

IGNORED_DIRS = {
    ".git",
    ".github",
    ".vscode",
    ".idea",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "vendor",
    "assets",
    "static/images",
    "public/images",
}

IGNORED_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".pyc",
    ".wasm",
    ".mp4",
    ".mp3",
    ".wav",
    ".mov",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".lock",
    ".sum",
    ".min.js",
    ".min.css",
    ".map",
    ".csv",
    ".tsv",
    ".parquet",
    ".db",
    ".sqlite",
    ".sqlite3",
}

MANIFEST_FILES = {
    "readme.md",
    "readme.txt",
    "readme",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "gemfile",
    "composer.json",
    "dockerfile",
    "docker-compose.yml",
}

ENTRY_POINTS = {
    "main.py",
    "app.py",
    "server.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "index.js",
    "index.ts",
    "server.js",
    "app.js",
    "app.ts",
    "main.go",
    "main.rs",
    "application.java",
    "main.js",
}


def sanitize_repo_url(url: str) -> Tuple[str, str]:
    """Clean URL and extract repo name."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        if url.startswith("github.com/"):
            url = f"https://{url}"
        else:
            raise ValueError("Invalid URL format. Please provide a full GitHub URL.")
    
    # Normalize github url
    clean_url = url.rstrip("/")
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]
    
    parts = clean_url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid repository URL structure.")
    repo_name = f"{parts[-2]}/{parts[-1]}"
    return clean_url, repo_name


def clone_repository(repo_url: str, target_dir: str) -> str:
    """Shallow clone repo into target directory using GitPython."""
    clean_url, _ = sanitize_repo_url(repo_url)
    clone_url = f"{clean_url}.git"
    
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(target_dir, exist_ok=True)
    
    # Clone with depth=1 for speed and resource efficiency
    git.Repo.clone_from(clone_url, target_dir, depth=1)
    return target_dir


def generate_ascii_tree(dir_path: str, max_depth: int = 3, max_entries_per_dir: int = 15) -> str:
    """Generate a clean ASCII directory tree representation."""
    lines = []
    
    def walk(current_dir: str, prefix: str = "", depth: int = 0):
        if depth >= max_depth:
            lines.append(f"{prefix}└── ... (deeper levels omitted)")
            return
            
        try:
            entries = sorted(os.listdir(current_dir))
        except OSError:
            return

        # Filter entries
        valid_entries = []
        for e in entries:
            if e in IGNORED_DIRS or e.startswith("."):
                continue
            ext = os.path.splitext(e)[1].lower()
            if ext in IGNORED_EXTS:
                continue
            valid_entries.append(e)

        total = len(valid_entries)
        displayed = valid_entries[:max_entries_per_dir]
        
        for i, entry in enumerate(displayed):
            is_last = (i == len(displayed) - 1) and (len(displayed) == total)
            connector = "└── " if is_last else "├── "
            child_path = os.path.join(current_dir, entry)
            
            if os.path.isdir(child_path):
                lines.append(f"{prefix}{connector}{entry}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                walk(child_path, new_prefix, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry}")
                
        if total > max_entries_per_dir:
            lines.append(f"{prefix}└── ... ({total - max_entries_per_dir} more files)")

    lines.append(os.path.basename(dir_path) + "/")
    walk(dir_path)
    return "\n".join(lines)


def score_file(rel_path: str) -> int:
    """Score file for relevance priority (higher score = more relevant)."""
    basename = os.path.basename(rel_path).lower()
    ext = os.path.splitext(basename)[1].lower()
    
    # Manifest / README top priority
    if basename in MANIFEST_FILES or basename.startswith("readme"):
        return 100
    if basename in ENTRY_POINTS:
        return 80
    if any(k in rel_path.lower() for k in ["routes", "controllers", "api", "models", "services"]):
        return 60
    if ext in [".py", ".ts", ".js", ".go", ".rs", ".java"]:
        return 40
    if ext in [".html", ".css", ".sql", ".sh"]:
        return 20
    return 10


def extract_codebase(
    repo_path: str,
    max_files: int = 25,
    max_chars_total: int = 35000,
    max_chars_per_file: int = 5000
) -> Tuple[List[Dict[str, str]], str, Dict[str, any]]:
    """Scan the repository, filter files, and extract structured source code."""
    file_candidates = []
    
    for root, dirs, files in os.walk(repo_path):
        # Exclude ignored dirs in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        
        for file in files:
            if file.startswith("."):
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext in IGNORED_EXTS:
                continue
                
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_path)
            
            # Skip massive files (> 500KB)
            try:
                size = os.path.getsize(full_path)
                if size > 500_000:
                    continue
            except OSError:
                continue
                
            file_candidates.append((rel_path, full_path, score_file(rel_path)))

    # Sort candidates by relevance score descending, then by shorter path
    file_candidates.sort(key=lambda item: (-item[2], len(item[0]), item[0]))
    
    extracted_files = []
    analyzed_file_names = []
    current_chars = 0
    
    for rel_path, full_path, _ in file_candidates:
        if len(extracted_files) >= max_files or current_chars >= max_chars_total:
            break
            
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
            
        # Truncate file if too large
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n\n... [remaining content truncated for brevity] ...\n"
            
        if current_chars + len(content) > max_chars_total:
            # Take partial slice to fit budget
            remaining_budget = max_chars_total - current_chars
            if remaining_budget > 300:
                content = content[:remaining_budget] + "\n\n... [content truncated to fit model context window] ...\n"
            else:
                break
                
        extracted_files.append({"path": rel_path, "content": content})
        analyzed_file_names.append(rel_path)
        current_chars += len(content)

    file_tree = generate_ascii_tree(repo_path)
    
    stats = {
        "total_files_scanned": len(file_candidates),
        "files_analyzed_count": len(extracted_files),
        "total_characters_extracted": current_chars,
    }
    
    return extracted_files, file_tree, stats
