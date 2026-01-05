from __future__ import annotations

import sys
from pathlib import Path

# Ensure `import app...` works when pytest is executed from repo root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
