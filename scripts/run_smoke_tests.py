#!/usr/bin/env python3
"""Standalone Smoke Test Runner for foveated-lidar-sih repository."""

import sys
from pathlib import Path


def main() -> int:
    # Ensure workspace root is on sys.path
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    print("=" * 70)
    print("Foveated Semantic 2.5D LiDAR Mapping — Smoke Test Suite")
    print(f"Repository Root: {repo_root}")
    print(f"Python Version : {sys.version.split()[0]}")
    print("=" * 70)

    try:
        import pytest
    except ImportError:
        print("[ERROR] pytest is not installed in the current environment.")
        print("Install foundational dependencies using: pip install -r requirements.txt")
        return 1

    test_dir = str(repo_root / "tests")
    exit_code = pytest.main(["-v", test_dir])
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
