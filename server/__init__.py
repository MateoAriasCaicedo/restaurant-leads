"""Local web app for the lead pipeline: a JSON API over the existing modules plus the built UI (ui/dist).

The pipeline modules use paths relative to the working directory (config.DB_PATH, LEADS_DIR),
so everything here runs with the repository root as cwd.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
