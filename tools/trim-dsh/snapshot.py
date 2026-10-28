#!/usr/bin/env python3
"""Content snapshot for the protected paths named by the AEH trim task.

This tool only reads. It records path, size, mtime, and sha256 for every
regular file below each root, plus a root-level digest. It never follows
symlinks (their targets are recorded instead), so a symlinked package tree
changes only its link text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


ROOTS = {
    "source_clone": Path("/home/hatch/workspace/deepseek-harness"),
    "dsh_home": Path("/home/hatch/.dsh"),
    "npx_dsh": Path("/home/hatch/.npm/_npx/1e7f6d9597241db0"),
    "step18_runtime": Path("/home/hatch/workspace/AEH/step18/runtime"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path) -> dict:
    entries: list[dict] = []
    root_digest = hashlib.sha256()
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        for name in filenames:
            path = Path(current) / name
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            rel = path.relative_to(root).as_posix()
            mode = info.st_mode
            if stat.S_ISLNK(mode):
                target = os.readlink(path)
                entries.append(
                    {
                        "path": rel,
                        "kind": "symlink",
                        "target": target,
                        "mtime_ns": info.st_mtime_ns,
                    }
                )
                root_digest.update(f"L\\0{rel}\\0{target}\\n".encode())
            elif stat.S_ISREG(mode):
                digest = sha256_file(path)
                entries.append(
                    {
                        "path": rel,
                        "kind": "file",
                        "size": info.st_size,
                        "mtime_ns": info.st_mtime_ns,
                        "sha256": digest,
                    }
                )
                root_digest.update(
                    f"F\\0{rel}\\0{info.st_size}\\0{digest}\\n".encode()
                )
    return {
        "root": str(root),
        "exists": root.exists(),
        "file_count": sum(1 for entry in entries if entry["kind"] == "file"),
        "symlink_count": sum(1 for entry in entries if entry["kind"] == "symlink"),
        "root_sha256": root_digest.hexdigest(),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = {name: snapshot(root) for name, root in ROOTS.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for name, root in data.items():
        print(
            f"{name}: files={root['file_count']} symlinks={root['symlink_count']} "
            f"sha256={root['root_sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
