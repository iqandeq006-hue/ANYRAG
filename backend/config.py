import os
from pathlib import Path
from typing import List, Set

BASE_DIR = Path(__file__).resolve().parent.parent

# Resolve local embedding model path (checking assets/ first, then models/)
if (BASE_DIR / "assets" / "embeddings" / "all-MiniLM-L6-v2").exists():
    DEFAULT_MODEL_DIR = BASE_DIR / "assets" / "embeddings" / "all-MiniLM-L6-v2"
else:
    DEFAULT_MODEL_DIR = BASE_DIR / "models" / "embeddings" / "all-MiniLM-L6-v2"

DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_CHROMA_DIR = DEFAULT_DATA_DIR / "chromadb"
DEFAULT_DB_PATH = DEFAULT_CHROMA_DIR

# PDF Parser configuration (Docling auto-switch vs forced)
# Options: "auto" (default smart heuristic), "true" (always Docling), "false" (always PyMuPDF)
DOCLING_MODE = os.environ.get("ANYRAG_USE_DOCLING", "auto").lower()
USE_DOCLING_FOR_PDF = None if DOCLING_MODE == "auto" else DOCLING_MODE in ("true", "1", "yes")

# OpenRouter Cloud Configuration (Primary: Kimi / DeepSeek)
DEFAULT_OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_OPENROUTER_MODEL = os.environ.get("ANYRAG_OPENROUTER_MODEL", os.environ.get("ANYRAG_CLOUD_MODEL", "moonshotai/kimi-k2"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

OPENROUTER_MODEL_ALIASES = {
    "kimi": "moonshotai/kimi-k2",
    "kimi-k2": "moonshotai/kimi-k2",
    "kimi-k2.5": "moonshotai/kimi-k2.5",
    "moonshot": "moonshotai/kimi-k2",
    "deepseek": "deepseek/deepseek-chat",
    "deepseek-chat": "deepseek/deepseek-chat",
    "deepseek-r1": "deepseek/deepseek-r1",
    "r1": "deepseek/deepseek-r1",
}

# Ollama Cloud / Remote configuration
DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", os.environ.get("ANYRAG_OLLAMA_HOST", "http://localhost:11434"))
DEFAULT_OLLAMA_MODEL = os.environ.get("ANYRAG_OLLAMA_MODEL", os.environ.get("OLLAMA_MODEL", "kimi"))

# Standalone llama.cpp runtime & offline GGUF model paths (local fallback)
DEFAULT_LLAMA_CLI_PATH = BASE_DIR / "assets" / "runtime" / "llama-cli.exe"
DEFAULT_LLAMA_SERVER_PATH = BASE_DIR / "assets" / "runtime" / "llama-server.exe"
DEFAULT_LLAMA_SERVER_DLL = BASE_DIR / "assets" / "runtime" / "llama-server-impl.dll"
_local_model_env = os.environ.get("ANYRAG_LOCAL_MODEL_PATH")
DEFAULT_GGUF_MODEL_PATH = Path(_local_model_env) if _local_model_env else (BASE_DIR / "assets" / "models" / "phi-4-mini-[3.8b-q4_k_m]-abliterated.gguf")
DEFAULT_LLAMA_SERVER_PORT: int = int(os.environ.get("ANYRAG_LLAMA_SERVER_PORT", "8080"))
DEFAULT_LLAMA_SERVER_URL: str = os.environ.get("ANYRAG_LLAMA_SERVER_URL", f"http://127.0.0.1:{DEFAULT_LLAMA_SERVER_PORT}")
DEFAULT_LLAMA_SERVER_CTX: int = int(os.environ.get("ANYRAG_LLAMA_SERVER_CTX", "4096"))

# Ensure data directory exists
DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Allowed extensions
ALLOWED_EXTENSIONS: Set[str] = {
    ".pdf", ".docx", ".pptx", ".md", ".txt", ".csv", ".json", ".py", ".html", ".htm"
}

# Chunking configurations
DEFAULT_CHUNK_SIZE: int = 600
DEFAULT_CHUNK_OVERLAP: int = 100

# Strict folder allowlist: only permitted user directories and subfolders
ALLOWED_USER_FOLDERS: List[str] = [
    "Documents",
    "Downloads",
    "Pictures",
    "Videos",
]

def get_allowed_root_directories() -> List[Path]:
    """
    Returns list of permitted root directory Paths:
    Documents, Downloads, Pictures, Videos (including OneDrive-mirrored paths if present).
    Supports custom additions via ANYRAG_ALLOWED_DIRS environment variable.
    """
    home = Path.home().resolve()
    allowed_roots: List[Path] = []

    for folder_name in ALLOWED_USER_FOLDERS:
        allowed_roots.append(home / folder_name)
        # Check OneDrive mirrored locations
        onedrive_folder = home / "OneDrive" / folder_name
        if onedrive_folder.exists():
            allowed_roots.append(onedrive_folder)

    # Optional custom allowlist directories from environment
    custom_env = os.environ.get("ANYRAG_ALLOWED_DIRS", "")
    if custom_env:
        for p in custom_env.split(os.pathsep):
            p = p.strip()
            if p:
                allowed_roots.append(Path(p).resolve())

    return [r.resolve() for r in allowed_roots]

def is_path_allowed(file_or_dir_path: str | Path) -> bool:
    """
    Validates if a path is permitted for ingestion.
    Strict allowlist: only permits files from Documents, Downloads, Pictures, Videos
    (and their subfolders). Rejects everything else by default.
    """
    try:
        resolved = Path(file_or_dir_path).resolve()
    except Exception:
        return False

    allowed_roots = get_allowed_root_directories()
    for allowed_root in allowed_roots:
        try:
            if resolved == allowed_root or resolved.is_relative_to(allowed_root):
                return True
        except (ValueError, AttributeError):
            try:
                resolved.relative_to(allowed_root)
                return True
            except ValueError:
                continue

    return False
