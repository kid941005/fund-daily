#!/usr/bin/env python3
"""
Check all code quality issues - lint, type check, and tests.
Used in CI/CD pipeline.
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
    print('='*60)
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main():
    errors = []

    # 1. Lint check
    if not run_cmd("python3 -m ruff check .", "Lint check"):
        errors.append("Lint check failed")

    # 2. Type check
    if not run_cmd("python3 -m mypy src/ web/ --ignore-missing-imports", "Type check"):
        errors.append("Type check failed")

    # 3. Tests
    if not run_cmd("python3 -m pytest tests/ -x -q", "Unit tests"):
        errors.append("Tests failed")

    if errors:
        print("\n" + "="*60)
        print("CHECK FAILED:")
        for e in errors:
            print(f"  - {e}")
        print("="*60)
        return 1

    print("\n" + "="*60)
    print("ALL CHECKS PASSED!")
    print("="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
