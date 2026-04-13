"""
Backward-compatible wrapper around the corrected ``db_visualizer.py`` entrypoint.
"""
from __future__ import annotations

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from app.db_visualizer import main


if __name__ == "__main__":
    main()
