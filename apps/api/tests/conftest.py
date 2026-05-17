import os
import sys
from pathlib import Path

# Make `app` importable when pytest is run from apps/api.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OLLAMA_URL", "http://test-ollama:11434")
os.environ.setdefault("OLLAMA_MODEL", "test-model")
