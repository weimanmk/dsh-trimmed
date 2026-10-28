#!/usr/bin/env python3
"""Run the Step 18 isolated session against the trimmed runtime.

This is the same runner code as step18/run-e2e.py; only its isolated paths are
rebound to .trim-verify/. The original step18/runtime and step18/home are not
read or written by this wrapper.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRATCH = REPO / ".trim-verify"
RUNNER = REPO / "step18" / "run-e2e.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("step18_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load runner: {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    runner = load_runner()
    runner.STEP18 = SCRATCH
    runner.REPO = REPO
    runner.HOME = SCRATCH / "home"
    runner.PROFILE = runner.HOME / "profiles" / "aeh-e2e"
    runner.WORK = SCRATCH / "work"
    runner.EVIDENCE = SCRATCH / "evidence"
    runner.RUNTIME = SCRATCH / "runtime"
    runner.DSH_ENTRY = (
        runner.RUNTIME
        / "node_modules"
        / "@deepseek-ai"
        / "dsh"
        / "lib"
        / "bin.js"
    )
    runner.AEH_ENTRY = REPO / "dsh-plugin" / "e2e" / "aeh-e2e-entry.ts"
    sys.argv = [str(Path(__file__).resolve()), *sys.argv[1:]]
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
