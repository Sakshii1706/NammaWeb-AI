"""
NammaWeb AI - Full RAG Evaluation Runner

Runs both retrieval and generation evaluations as one regression check.

Run from the project root:
    .\venv\Scripts\python.exe .\scripts\run_rag_evaluation.py

Exit code:
    0 = both evaluations passed
    1 = one or more evaluations failed
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

EVALUATIONS = [
    PROJECT_ROOT / "scripts" / "evaluate_rag.py",
    PROJECT_ROOT / "scripts" / "evaluate_generation.py",
]


def run_evaluation(script: Path) -> int:
    print()
    print("=" * 80)
    print(f"RUNNING: {script.name}")
    print("=" * 80)

    result = subprocess.run(
        [PYTHON, str(script)],
        cwd=PROJECT_ROOT,
    )

    print()
    print(f"{script.name} exit code: {result.returncode}")
    return result.returncode


def main() -> int:
    print()
    print("=" * 80)
    print("NAMMAWEB AI - FULL RAG REGRESSION EVALUATION")
    print("=" * 80)

    missing = [str(path) for path in EVALUATIONS if not path.exists()]
    if missing:
        print("Missing evaluation files:")
        for path in missing:
            print(f"  - {path}")
        return 1

    failures = 0

    for script in EVALUATIONS:
        code = run_evaluation(script)
        if code != 0:
            failures += 1

    print()
    print("=" * 80)
    print("FULL RAG REGRESSION SUMMARY")
    print("=" * 80)

    if failures == 0:
        print("Retrieval evaluation : PASS")
        print("Generation evaluation: PASS")
        print("Overall              : PASS")
        print("=" * 80)
        return 0

    print(f"Failed evaluations   : {failures}/{len(EVALUATIONS)}")
    print("Overall              : FAIL")
    print("=" * 80)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
