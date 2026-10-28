#!/usr/bin/env python3
"""Stage a runnable trimmed-dsh tree for the Windows installer.

Pipeline (runs on the CI Windows runner and, with --skip-node, locally):
  1. ``pnpm --filter @deepseek-ai/dsh deploy <stage>/app --prod --legacy``
     from the trimmed tree. The legacy deploy drops peer-only packages
     (e.g. @deepseek-ai/cordis-plugin-group, a peer of dsh-app-boot that
     the CLI does not declare), so step 2 repairs the tree.
  2. Import-driven repair: scan every ``.js`` file under the deployed
     tree for bare ``@deepseek-ai/*`` / ``cordis`` specifiers, and copy
     any missing package from the trimmed tree (workspace/vendor dirs
     first, then the pnpm store) into the top-level ``node_modules`` as
     real files. Iterate to a fixpoint (copies can bring new imports).
  3. Snapshot: write a content store (one copy per unique real file)
     plus app-manifest.json (dirs/files/links). The installer rebuilds
     the tree with setup-tree.cjs (junctions + hardlinks, no elevation).
  4. Unless --skip-node: download the official Node win-x64 zip and place
     ``node.exe`` next to the staged files.
  5. Write the launcher (dsh-trimmed.cmd), install README, STAGE-INFO.txt.

The script never touches the runtime harness (~/.dsh), the source clone,
or the trimmed tree itself (read-only inputs). It writes only under
--stage. Exit non-zero on any failure; the caller runs --help separately.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

CLI_PACKAGE = "@deepseek-ai/dsh"
IMPORT_RE = re.compile(
    r"""(?:from\s+['"]|import\s*\(\s*['"]|require\s*\(\s*['"])"""
    r"""(@deepseek-ai/[A-Za-z0-9._-]+|cordis[A-Za-z0-9._-]*)"""
    r"""(?:/[^'"]*)?['"]"""
)
# Repair copies of single workspace packages exclude their nested
# node_modules (their deps resolve through the deployed tree instead).
IGNORE = shutil.ignore_patterns("node_modules", ".git", "__pycache__", "*.tsbuildinfo")
# Materializing the whole deployed tree must KEEP node_modules: it is the
# runtime. Only build residue is dropped.
MATERIALIZE_IGNORE = shutil.ignore_patterns(".git", "__pycache__", "*.tsbuildinfo")


def pkg_name(spec: str) -> str:
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0]


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    res = subprocess.run(cmd, cwd=cwd)
    if res.returncode != 0:
        raise SystemExit(f"command failed ({res.returncode}): {' '.join(cmd)}")


def build_source_map(trimmed: Path) -> dict[str, Path]:
    """Map package name -> real directory for workspace/vendor packages.

    Walks every package.json in the tree (depth-capped, node_modules
    pruned) instead of assuming a fixed group/pkg layout: the native
    addon entry (@deepseek-ai/node-addon-system) lives at
    native/system/packages/entry, which a packages/apps/vendor-only scan
    misses (run #10: repair could not find its source on Windows).
    """
    mapping: dict[str, Path] = {}
    skip = {"node_modules", ".git", "__pycache__"}
    for dirpath, dirnames, filenames in os.walk(trimmed):
        rel = Path(dirpath).relative_to(trimmed)
        if len(rel.parts) > 5:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        if "package.json" not in filenames:
            continue
        try:
            name = json.loads((Path(dirpath) / "package.json").read_text(encoding="utf-8"))[
                "name"
            ]
        except Exception:
            continue
        mapping.setdefault(name, Path(dirpath))
    return mapping


def store_lookup(trimmed: Path, name: str) -> Path | None:
    """Find a registry package's real dir inside the pnpm store."""
    store = trimmed / "node_modules" / ".pnpm"
    if not store.is_dir():
        return None
    escaped = name.replace("/", "+")
    for entry in store.iterdir():
        if entry.name.startswith(escaped + "@"):
            cand = entry / "node_modules" / name
            if cand.is_dir():
                return cand
    return None


def top_level_present(app: Path, name: str) -> bool:
    return (app / "node_modules" / name).is_dir()


def store_present(app: Path, name: str) -> bool:
    store = app / "node_modules" / ".pnpm"
    if not store.is_dir():
        return False
    escaped = name.replace("/", "+")
    return any(e.name.startswith(escaped + "@") for e in store.iterdir())


def collect_imports(app: Path) -> set[str]:
    """All bare @deepseek-ai/* specifiers imported by .js files in the tree."""
    found: set[str] = set()
    # Scan every .js file, including the pnpm store: transitive imports
    # (e.g. dsh-app-boot -> cordis-plugin-group) live in store packages,
    # and only the full closure makes the deployed tree runnable.
    for js in app.rglob("*.js"):
        try:
            text = js.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in IMPORT_RE.finditer(text):
            found.add(pkg_name(m.group(1)))
    return found


def repair(app: Path, trimmed: Path, source_map: dict[str, Path]) -> list[str]:
    """Copy missing imported packages into top-level node_modules."""
    repaired: list[str] = []
    for _pass in range(4):
        missing = {
            name
            for name in collect_imports(app)
            if not top_level_present(app, name) and not store_present(app, name)
        }
        # The CLI entry itself lives at app/lib; its own package dir is the
        # app root, never a missing import.
        missing.discard(CLI_PACKAGE)
        if not missing:
            return repaired
        progressed = False
        for name in sorted(missing):
            src = source_map.get(name)
            if src is None or not src.is_dir():
                src = store_lookup(trimmed, name)
            if src is None:
                # Last resort: the trimmed tree's top-level node_modules.
                cand = trimmed / "node_modules" / name
                if cand.is_dir():
                    src = cand
            if src is None:
                raise SystemExit(f"cannot find source for missing package {name}")
            src = Path(os.path.realpath(src))
            dst = app / "node_modules" / name
            if os.path.lexists(dst):
                # Broken link or stale entry: replace with a real copy.
                if dst.is_symlink() or dst.is_file():
                    dst.unlink()
                else:
                    shutil.rmtree(dst)
            print(f"repair: {name} <- {src}", flush=True)
            shutil.copytree(src, dst, ignore=IGNORE, symlinks=False)
            repaired.append(name)
            progressed = True
        if not progressed:
            return repaired
    raise SystemExit("import repair did not converge after 4 passes")


def snapshot(src: Path, dst: Path) -> tuple[list[dict], list[str]]:
    """Snapshot the deployed tree into a content store + manifest.

    Why not copy the tree with symlinks resolved (copytree /
    hand-rolled walk)? pnpm's store shares every package across many
    referencing paths, so expanding every link duplicates shared files
    once per referrer (a trial run passed 11 GB and kept growing) and
    deep link chains exceed the kernel's symlink-resolution limit
    (ELOOP). Instead this walk visits each unique real directory once
    and records everything else as a link:

    - unique real dirs/files -> manifest entries + file content in
      ``store/`` (one copy per unique real file, hardlinked from src);
    - a repeated real dir, or any symlink -> a link entry pointing at
      the first occurrence's id; the installer recreates it as an NTFS
      junction (dirs) or hardlink (files), which need no elevation.

    The installer (setup-tree.cjs, run once by Inno Setup) rebuilds
    exactly this structure, so Node resolution behaves as in the
    pnpm tree. Returns (manifest entries, skipped broken links).
    """
    if not src.is_dir():
        raise SystemExit(f"snapshot source missing (deploy failed?): {src}")
    store = dst / "store"
    # NOTE: dst is the stage dir and src (app-raw) lives inside it, so
    # only the store output is cleared here, never dst itself. main()
    # cleans the stage dir before deploying.
    if store.exists():
        shutil.rmtree(store)
    store.mkdir(parents=True)
    entries: list[dict] = []
    skipped_broken: list[str] = []
    # realpath -> id of its first occurrence (dirs and files share the id
    # space; ids are assigned in walk order).
    first_seen: dict[str, str] = {}
    next_id = [0]

    def new_id() -> str:
        next_id[0] += 1
        return f"n{next_id[0]}"

    def store_file(real: Path) -> str:
        key = new_id()
        target = store / key
        try:
            os.link(real, target)
        except OSError:
            shutil.copyfile(real, target, follow_symlinks=True)
        return key

    def walk(s: Path, rel: str, ancestors: frozenset[str]) -> None:
        # s is always a real directory here (callers resolve links), so
        # path strings stay short and never hit the kernel ELOOP limit
        # that deep symlink chains cause.
        for entry in sorted(os.scandir(s), key=lambda e: e.name):
            name = entry.name
            if name in (".git", "__pycache__") or name.endswith(".tsbuildinfo"):
                continue
            child_rel = f"{rel}/{name}" if rel else name
            spath = Path(entry.path)
            real = os.path.realpath(spath)
            if entry.is_symlink() and not Path(real).exists():
                # Platform-specific links (e.g. a macOS-only package)
                # are broken in the source tree too; skipping preserves
                # source semantics. Smoke tests prove the result.
                skipped_broken.append(child_rel)
                print(f"snapshot: skip broken link {child_rel}", flush=True)
                continue
            # First occurrence wins, however it is reached (real dir or
            # symlink): it becomes the canonical real entry, and every
            # later path to the same realpath becomes a link to it.
            # An ancestor's realpath always has a first occurrence (the
            # ancestor itself), so ancestor links need no special case
            # beyond the first_seen lookup.
            if real in first_seen:
                kind = "dirlink" if Path(real).is_dir() else "filelink"
                entries.append({"path": child_rel, "kind": kind, "target": first_seen[real]})
                continue
            ident = new_id()
            first_seen[real] = ident
            if Path(real).is_dir():
                entries.append({"path": child_rel, "kind": "dir", "id": ident})
                walk(Path(real), child_rel, ancestors | {real})
            elif Path(real).is_file():
                key = store_file(Path(real))
                entries.append({"path": child_rel, "kind": "file", "id": ident, "store": key})
            # fifos/sockets/etc: not present in a deployed tree; skip silently

    root_real = os.path.realpath(src)
    root_id = new_id()
    first_seen[root_real] = root_id
    entries.append({"path": "", "kind": "dir", "id": root_id})
    walk(Path(root_real), "", frozenset({root_real}))
    print(
        f"snapshot: {len(entries)} entries, "
        f"{sum(1 for e in entries if e['kind'] == 'file')} unique files, "
        f"{len(skipped_broken)} broken links skipped",
        flush=True,
    )
    return entries, skipped_broken


def download_node(stage: Path, version: str) -> Path:
    url = f"https://nodejs.org/dist/v{version}/node-v{version}-win-x64.zip"
    zpath = stage / f"node-v{version}-win-x64.zip"
    print(f"downloading {url}", flush=True)
    urllib.request.urlretrieve(url, zpath)
    with zipfile.ZipFile(zpath) as zf:
        names = [n for n in zf.namelist() if n.endswith("/node.exe")]
        if len(names) != 1:
            raise SystemExit(f"unexpected node zip layout: {names[:3]}")
        zf.extract(names[0], stage)
        node_exe = stage / names[0]
    target = stage / "node.exe"
    shutil.move(str(node_exe), target)
    shutil.rmtree(stage / names[0].split("/")[0])
    zpath.unlink()
    if target.stat().st_size < 10_000_000:
        raise SystemExit(f"node.exe suspiciously small: {target.stat().st_size}")
    return target


LAUNCHER = (
    "@echo off\r\n"
    "rem DSH Trimmed launcher: bundled Node + trimmed CLI. User data lives\r\n"
    "rem in %USERPROFILE%\\.dsh (DSH_HOME) and is never touched by uninstall.\r\n"
    "\"%~dp0node.exe\" \"%~dp0app\\lib\\bin.js\" %*\r\n"
)

INSTALL_README = """DSH Trimmed (headless CLI) - install notes
=========================================

This installs the trimmed DeepSeek Harness command-line runtime
(headless + desktop-host libraries, no desktop frontend). It is NOT
signed: Windows SmartScreen may warn on first run; choose
"More info" -> "Run anyway" if you trust this build.

Run from a terminal (the install folder is added to your user PATH):

  dsh-trimmed --help
  dsh-trimmed --profile <name> "task"

Your data lives in %USERPROFILE%\\.dsh (override with DSH_HOME).
To run real sessions, configure a profile with a model API key;
no key is shipped in this package. Uninstall from Windows Settings;
your .dsh home is left untouched.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trimmed", required=True, type=Path)
    ap.add_argument("--stage", required=True, type=Path)
    ap.add_argument("--node-version", default="24.22.1")
    ap.add_argument("--skip-node", action="store_true")
    ap.add_argument("--source-ref", default="")
    args = ap.parse_args()

    # Resolve both inputs to absolute paths FIRST: the deploy runs with
    # cwd=<trimmed>, so a relative --stage would make pnpm create the
    # deploy target under trimmed/ while snapshot/repair look for it
    # under the script's cwd (run #9: app-raw "not found").
    trimmed, stage = args.trimmed.resolve(), args.stage.resolve()
    if not (trimmed / "apps" / "cli" / "package.json").is_file():
        raise SystemExit(f"not a trimmed tree: {trimmed}")
    if stage.resolve() == trimmed.resolve() or stage.resolve() == Path.home():
        raise SystemExit(f"refusing to use {stage} as the stage dir")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)
    raw = stage / "app-raw"

    # On Windows, pnpm is a .cmd shim (PNPM_HOME/.bin) and CreateProcess
    # cannot launch it directly (FileNotFoundError, run #8); route through
    # cmd.exe. On POSIX, pnpm resolves normally.
    deploy_cmd = (
        ["cmd", "/c", "pnpm", "--filter", CLI_PACKAGE, "deploy", str(raw), "--prod", "--legacy"]
        if os.name == "nt"
        else ["pnpm", "--filter", CLI_PACKAGE, "deploy", str(raw), "--prod", "--legacy"]
    )
    run(deploy_cmd, cwd=trimmed)
    if not (raw / "lib" / "bin.js").is_file():
        raise SystemExit(f"pnpm deploy did not produce {raw}/lib/bin.js")
    source_map = build_source_map(trimmed)
    repaired = repair(raw, trimmed, source_map)

    entries, skipped_broken = snapshot(raw, stage)
    shutil.rmtree(raw)
    (stage / "app-manifest.json").write_text(
        json.dumps({"version": 1, "entries": entries}, indent=1), encoding="utf-8"
    )
    setup_src = Path(__file__).resolve().parent / "setup-tree.cjs"
    if not setup_src.is_file():
        raise SystemExit(f"setup-tree.cjs missing next to {__file__}")
    shutil.copyfile(setup_src, stage / "setup-tree.cjs")

    if args.skip_node:
        node_note = "skipped (--skip-node)"
    else:
        download_node(stage, args.node_version)
        node_note = f"node.exe {args.node_version} (official win-x64 zip)"
        if os.name == "nt":
            run([str(stage / "node.exe"), "--version"], cwd=stage)

    (stage / "dsh-trimmed.cmd").write_bytes(LAUNCHER.encode("utf-8"))
    (stage / "README-INSTALL.txt").write_text(INSTALL_README, encoding="utf-8")

    store_dir = stage / "store"
    total_bytes = sum(p.stat().st_size for p in store_dir.iterdir() if p.is_file())
    kinds: dict[str, int] = {}
    for e in entries:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    max_rel = max((len(e["path"]) for e in entries), default=0)
    info = (
        f"source-ref={args.source_ref}\n"
        f"node={node_note}\n"
        f"repaired-packages={','.join(repaired) if repaired else '(none)'}\n"
        f"store-bytes={total_bytes}\n"
        f"store-files={sum(1 for p in store_dir.iterdir() if p.is_file())}\n"
        f"manifest-entries={len(entries)} "
        f"({', '.join(f'{k}={v}' for k, v in sorted(kinds.items()))})\n"
        f"max-manifest-path={max_rel}\n"
        f"skipped-broken-links={len(skipped_broken)}:"
        f"{';'.join(skipped_broken[:20])}\n"
    )
    (stage / "STAGE-INFO.txt").write_text(info, encoding="utf-8")
    print(info, flush=True)
    print("stage OK:", stage, flush=True)


if __name__ == "__main__":
    main()
