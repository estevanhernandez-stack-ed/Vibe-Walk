"""
Pytest configuration for Vibe-Walk tests.
Adds the scripts root to sys.path so tests can import discovery modules directly.
"""
import sys
from pathlib import Path

# Make scripts importable without installation
SCRIPTS_ROOT = Path(__file__).parent.parent / "plugins" / "vibe-walk" / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

FIXTURES_DIR = Path(__file__).parent / "fixtures"
