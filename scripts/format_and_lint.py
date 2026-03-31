#!/usr/bin/env python3
"""
Format and lint code.
Used in CI/CD pipeline to ensure code quality.
"""

import os
import subprocess
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Move to project root


def run_cmd(cmd, desc):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {desc}")
    print(f"Command: {cmd}")
    print("=" * 60)
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main():
    errors = []

    # 1. Auto-format with isort and black
    if not run_cmd("python3 -m isort --quiet .", "Import sorting"):
        errors.append("isort failed")

    if not run_cmd("python3 -m black --quiet .", "Code formatting"):
        errors.append("black failed")

    # 2. Lint check (fail on issues)
    if not run_cmd("python3 -m ruff check . --exit-non-zero-on-fix", "Lint check"):
        errors.append("Lint check failed")

    if errors:
        print("\n" + "=" * 60)
        print("FORMAT/LINT FAILED:")
        for e in errors:
            print(f"  - {e}")
        print("=" * 60)
        return 1

    print("\n" + "=" * 60)
    print("FORMAT AND LINT PASSED!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
