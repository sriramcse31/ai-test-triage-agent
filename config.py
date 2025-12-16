"""
Configuration settings for the triage agent
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DEMO_DIR = PROJECT_ROOT / "demo"
LOGS_DIR = DEMO_DIR / "sample_ci_failures"

# RAG settings
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # Fast, local embeddings
VECTOR_DB_PATH = DATA_DIR / "failures_db"
SIMILARITY_TOP_K = 5

# LLM settings (Ollama)
LLM_MODEL = "llama3.2:3b"  # or "mistral", "llama3.1"
LLM_BASE_URL = "http://20.42.209.235:11434"
LLM_TEMPERATURE = 0.1  # Low temperature for consistent analysis
LLM_MAX_TOKENS = 2000

# Flakiness detection thresholds
FLAKY_RETRY_THRESHOLD = 2  # If test passes after N retries, likely flaky
FLAKY_PATTERN_THRESHOLD = 3  # If same test fails N times in history, check flakiness
FLAKY_SCORE_HIGH = 0.75  # Confidence threshold for "high flakiness"

# Classification confidence thresholds
HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.5
LOW_CONFIDENCE = 0.3

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
DEMO_DIR.mkdir(exist_ok=True)