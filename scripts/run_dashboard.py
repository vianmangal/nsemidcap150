from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    app_path = root / "dashboard.py"
    if not app_path.exists():
        raise FileNotFoundError(f"Dashboard not found: {app_path}")
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
