#!/usr/bin/env python3
"""Reproduce the approved AEH dsh trim on an isolated build copy.

The source clone is only read. All deletions and reference edits happen in a
new destination copy. The script refuses to write into the running dsh, the
AEH repository, or the Step 18 runtime.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "trim-manifest.json"
DEFAULT_DEST = Path("/home/hatch/workspace/dsh-trimmed")
PROTECTED = [
    Path("/home/hatch/.dsh"),
    Path("/home/hatch/workspace/deepseek-harness"),
    Path("/home/hatch/.npm/_npx/1e7f6d9597241db0"),
    Path("/home/hatch/workspace/AEH/step18/runtime"),
    Path("/home/hatch/workspace/AEH/references"),
    Path("/home/hatch/workspace/AEH/spec"),
]


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=check, text=True, capture_output=True)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_safe_destination(dest: Path) -> None:
    resolved = dest.resolve()
    for protected in PROTECTED:
        if is_relative_to(resolved, protected.resolve()):
            raise SystemExit(f"refusing destination inside protected path: {protected}")
    aeh = Path("/home/hatch/workspace/AEH").resolve()
    if is_relative_to(resolved, aeh):
        raise SystemExit(
            "refusing destination inside the AEH repository; keep the 200 MB build copy outside it"
        )


def workspace_packages(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for group in ("packages", "apps", "vendor"):
        base = root / group
        if not base.exists():
            continue
        for manifest in base.rglob("package.json"):
            if "node_modules" in manifest.parts:
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            name = data.get("name")
            if isinstance(name, str):
                found[name] = manifest.parent
    for extra in ("native/system", "benchmarks", "website", "python/sdk-runtime"):
        manifest = root / extra / "package.json"
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data.get("name"), str):
                found[data["name"]] = manifest.parent
    native_packages = root / "native/system/packages"
    if native_packages.exists():
        for manifest in native_packages.glob("*/package.json"):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data.get("name"), str):
                found[data["name"]] = manifest.parent
    return found


def dep_dicts(package: dict) -> list[str]:
    return [
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ]


def prune_package_json(root: Path, removed: set[str], log: list[dict]) -> None:
    for manifest in root.rglob("package.json"):
        if "node_modules" in manifest.parts:
            continue
        rel = manifest.relative_to(root).as_posix()
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        changed = False
        removed_edges: list[str] = []
        for field in dep_dicts(data):
            block = data.get(field)
            if not isinstance(block, dict):
                continue
            for name in list(block):
                if name in removed:
                    del block[name]
                    removed_edges.append(f"{field}:{name}")
                    changed = True
        if changed:
            manifest.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            log.append({"package_json": rel, "removed_edges": removed_edges})


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"expected text not found in {path}:\n{old[:200]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def remove_quoted_line(path: Path, name: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^[ \t]*'{re.escape(name)}',[ \t]*\n", re.MULTILINE)
    new, count = pattern.subn("", text)
    if count != expected:
        raise SystemExit(
            f"expected {expected} quoted line(s) for {name} in {path}, found {count}"
        )
    path.write_text(new, encoding="utf-8")


def edit_official_bundles(root: Path) -> None:
    bundles = root / "packages/util/official-bundles/src/bundles.ts"
    replace_exact(
        bundles,
        """  web: {
    bundles: ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app'],
  },
""",
        "",
    )
    for name in (
        "@deepseek-ai/dsh-experimental-voice-input-bundle",
        "@deepseek-ai/dsh-experimental-cot-translation-bundle",
        "@deepseek-ai/dsh-experimental-plugin-market-bundle",
    ):
        remove_quoted_line(bundles, name)
    replace_exact(
        bundles,
        """export const RETIRED_BUNDLES: ReadonlySet<string> = new Set([
  // The Web composition mounts Schedule itself
  // ([upgrade guide](../../../../docs/upgrade-guide/v0.2.0-rc.2/schedule-bundle-retired/guide.md)).
  '@deepseek-ai/dsh-experimental-schedule-bundle',
])""",
        """export const RETIRED_BUNDLES: ReadonlySet<string> = new Set([
  // The Web composition mounts Schedule itself
  // ([upgrade guide](../../../../docs/upgrade-guide/v0.2.0-rc.2/schedule-bundle-retired/guide.md)).
  '@deepseek-ai/dsh-experimental-schedule-bundle',
  // AEH trim: the browser surface and its optional bundles are not shipped.
  '@deepseek-ai/dsh-web-app',
  '@deepseek-ai/dsh-experimental-cot-translation-bundle',
  '@deepseek-ai/dsh-experimental-plugin-market-bundle',
  '@deepseek-ai/dsh-experimental-voice-input-bundle',
])""",
    )


def edit_plugin_manager(root: Path) -> None:
    manager = root / "packages/util/official-bundles/src/plugin-manager.ts"
    replace_exact(
        manager,
        """export const PROTECTED_PLUGINS: ReadonlySet<string> = new Set([
  '@deepseek-ai/dsh-plugin-manager', '@deepseek-ai/cordis-plugin-loader',
  '@deepseek-ai/cordis-plugin-include', '@deepseek-ai/dsh-api-gateway',
  '@deepseek-ai/dsh-host-webserver', '@deepseek-ai/dsh-client-modules',
  '@deepseek-ai/dsh-client-ui-settings-plugin-inventory', '@deepseek-ai/dsh-client-ui-plugin-manager',
  '@deepseek-ai/dsh-host-plugin-inventory', '@deepseek-ai/dsh-typert-registry',
  '@deepseek-ai/dsh-api-remotes', '@deepseek-ai/dsh-api-remote-access',
  '@deepseek-ai/cordis-plugin-timer', '@deepseek-ai/dsh-client-connection',
  '@deepseek-ai/dsh-host-frontend-static', '@deepseek-ai/dsh-tools',
  '@deepseek-ai/dsh-hmr',
])""",
        """export const PROTECTED_PLUGINS: ReadonlySet<string> = new Set([
  '@deepseek-ai/dsh-plugin-manager', '@deepseek-ai/cordis-plugin-loader',
  '@deepseek-ai/cordis-plugin-include', '@deepseek-ai/dsh-api-gateway',
  '@deepseek-ai/dsh-host-webserver',
  '@deepseek-ai/dsh-host-plugin-inventory', '@deepseek-ai/dsh-typert-registry',
  '@deepseek-ai/dsh-api-remotes', '@deepseek-ai/dsh-api-remote-access',
  '@deepseek-ai/cordis-plugin-timer', '@deepseek-ai/dsh-client-connection',
  '@deepseek-ai/dsh-tools',
  '@deepseek-ai/dsh-hmr',
])""",
    )
    remove_quoted_line(manager, "@deepseek-ai/dsh-web-app")
    for name, expected in (
        ("@deepseek-ai/dsh-experimental-voice-input-bundle", 2),
        ("@deepseek-ai/dsh-experimental-plugin-market-bundle", 2),
        ("@deepseek-ai/dsh-experimental-cot-translation-bundle", 2),
    ):
        remove_quoted_line(manager, name, expected)


def edit_cli_help(root: Path) -> None:
    args = root / "apps/cli/src/args.ts"
    replace_exact(
        args,
        """ * `dsh --profile tui --resume abc` boots the tui profile with `--resume abc`,
 * and `dsh --profile web -h` prints the web app's help, not this one's.""",
        """ * `dsh --profile tui --resume abc` boots the tui profile with `--resume abc`,
 * and `dsh --profile headless -h` prints the headless app's help, not this one's.""",
    )
    replace_exact(
        args,
        """Examples:
  dsh web                                   boot the web profile (same as: dsh --profile web)
  dsh rescue --from-default-profile web
                                            recreate rescue from the shipped web template, then boot it
  dsh headless "run the tests"              answer one task, print the result, and exit
  dsh tui --patch ./extra.yml               boot a custom profile with one extra overlay
  dsh tui --resume <session>                arguments after the launcher flags reach the app
  dsh web --help                            the web app's own flags and help
  dsh plugin --profile tui add <package>    install a plugin into the tui profile""",
        """Examples:
  dsh headless "run the tests"              answer one task, print the result, and exit
  dsh rescue --from-default-profile headless
                                            recreate rescue from the shipped headless template, then boot it
  dsh tui --patch ./extra.yml               boot a custom profile with one extra overlay
  dsh tui --resume <session>                arguments after the launcher flags reach the app
  dsh headless --help                       the headless app's own flags and help
  dsh plugin --profile tui add <package>    install a plugin into the tui profile""",
    )



def line_targets_missing(line: str, root: Path) -> bool:
    targets = re.findall(
        r'"((?:\./)?(?:apps|packages|scripts|benchmarks|native|python|vendor)/[^"]+)"',
        line,
    )
    for rel in targets:
        if "*" in rel:
            prefix = rel.split("*", 1)[0]
            if not (root / prefix).exists():
                return True
        elif not (root / rel).exists():
            return True
    return False


def prune_missing_tsconfig_lines(path: Path, root: Path) -> list[str]:
    removed: list[str] = []
    kept: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        if line_targets_missing(line, root):
            removed.append(line.strip())
        else:
            kept.append(line)
    path.write_text("".join(kept), encoding="utf-8")
    return removed


def clean_build_surface(root: Path) -> dict:
    removed_lines: list[str] = []
    for name in ("tsconfig.base.json", "tsconfig.host.json"):
        removed_lines.extend(
            f"{name}: {line}" for line in prune_missing_tsconfig_lines(root / name, root)
        )

    solution = root / "tsconfig.json"
    text = solution.read_text(encoding="utf-8")
    old = '    { "path": "./tsconfig.client.json" }\n'
    if old not in text:
        raise SystemExit("tsconfig.json client aggregate reference not found")
    text = text.replace(old, "", 1).replace(
        '    { "path": "./tsconfig.host.json" },\n  ]',
        '    { "path": "./tsconfig.host.json" }\n  ]',
    )
    solution.write_text(text, encoding="utf-8")

    client_aggregate = root / "tsconfig.client.json"
    if client_aggregate.exists():
        client_aggregate.unlink()

    package_json = root / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {})
    removed_scripts: list[str] = []
    for key in list(scripts):
        value = str(scripts[key])
        if (
            key != "build:lib:host"
            and (
                key == "build:lib:client"
                or key.startswith(("build:web", "test:web", "start:web", "dev:web"))
            or key.startswith(
                (
                    "build:desktop",
                    "dev:desktop",
                    "start:desktop",
                    "prepare:desktop",
                    "package:desktop",
                    "upload:",
                )
            )
            or "@deepseek-ai/dsh-desktop" in value
            or "@deepseek-ai/dsh-web-frontend" in value
                or "apps/desktop" in value
            )
        ):
            removed_scripts.append(key)
            del scripts[key]
    scripts["build:lib"] = "pnpm run build:lib:host"
    scripts["build:lib:host"] = scripts["build:lib:host"].replace(
        " && pnpm --filter @deepseek-ai/dsh-desktop run bundle", ""
    )
    package_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "removed_tsconfig_lines": removed_lines,
        "removed_root_scripts": removed_scripts,
        "deleted_client_aggregate": "tsconfig.client.json",
    }

def verify(root: Path, manifest: dict, removed: set[str]) -> dict:
    packages = workspace_packages(root)
    dangling: list[str] = []
    for name, directory in packages.items():
        manifest_path = directory / "package.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in dep_dicts(data):
            block = data.get(field)
            if not isinstance(block, dict):
                continue
            for dep, version in block.items():
                if isinstance(version, str) and version.startswith("workspace:") and dep not in packages:
                    dangling.append(
                        f"{manifest_path.relative_to(root)}: {field}.{dep}={version}"
                    )

    missing_kept = [
        name
        for name in [
            manifest["keep"]["p1_badge"],
            *manifest["keep"]["pending_disabled_20"],
            *manifest["keep"]["client_transport_exception"].split("\n"),
        ]
        if name and name not in packages
    ]
    removed_still_present = [
        rel
        for group in manifest["deletion_groups"]
        for rel in group["paths"]
        if (root / rel).exists()
    ]
    expected_apps = ["apps/cli", "apps/desktop-host"]
    missing_apps = [rel for rel in expected_apps if not (root / rel / "package.json").exists()]
    headless = ["packages/bundle/headless", "packages/bundle/base"]
    missing_headless = [rel for rel in headless if not (root / rel / "package.json").exists()]
    if dangling:
        raise SystemExit("dangling workspace dependencies remain:\n" + "\n".join(dangling))
    if missing_kept:
        raise SystemExit("required kept packages are missing: " + ", ".join(missing_kept))
    if removed_still_present:
        raise SystemExit("deleted paths still exist: " + ", ".join(removed_still_present))
    if missing_apps or missing_headless:
        raise SystemExit(f"missing required apps/bundles: {missing_apps + missing_headless}")
    return {
        "workspace_package_count": len(packages),
        "removed_package_count": len(removed),
        "dangling_workspace_dependencies": 0,
        "kept_badge": manifest["keep"]["p1_badge"],
        "pending_kept": len(manifest["keep"]["pending_disabled_20"]),
        "apps": expected_apps,
        "bundles": headless,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/home/hatch/workspace/deepseek-harness"))
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--in-place", action="store_true", help="trim an existing copy instead of copying")
    parser.add_argument("--allow-dirty-source", action="store_true")
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    source = args.source.resolve()
    dest = args.dest.resolve()
    assert_safe_destination(dest)
    if not source.is_dir():
        raise SystemExit(f"source clone not found: {source}")

    head = run(["git", "-C", str(source), "rev-parse", "HEAD"]).stdout.strip()
    status = run(["git", "-C", str(source), "status", "--porcelain"]).stdout.strip()
    if head != manifest["source"]["commit"]:
        raise SystemExit(
            f"source HEAD {head} does not match manifest {manifest['source']['commit']}"
        )
    if status and not args.allow_dirty_source:
        raise SystemExit("source clone is dirty; refusing to call it a read-only baseline")

    if args.in_place:
        if not dest.is_dir():
            raise SystemExit(f"--in-place destination does not exist: {dest}")
    else:
        if dest.exists():
            raise SystemExit(f"destination already exists: {dest}")
        source_bytes = sum(
            path.stat().st_size for path in source.rglob("*") if path.is_file()
        )
        free = shutil.disk_usage(dest.parent).free
        required = int(source_bytes * 1.2) + 64 * 1024 * 1024
        print(
            f"[trim] source={source_bytes / 1024 / 1024:.1f} MiB "
            f"free={free / 1024 / 1024:.1f} MiB required>={required / 1024 / 1024:.1f} MiB"
        )
        if free < required:
            raise SystemExit("insufficient free space for the build copy")
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"[trim] copying {source} -> {dest}")
        # Pure-Python copy (Windows runners have no `cp -a`); preserves
        # symlinks like `cp -a` does. Verified by re-trim comparison.
        shutil.copytree(source, dest, symlinks=True)

    before = workspace_packages(dest)
    deletion = [
        {"path": path, "group": group["id"]}
        for group in manifest["deletion_groups"]
        for path in group["paths"]
    ]
    removed_names: set[str] = set()
    deleted_packages: list[dict] = []
    for item in deletion:
        path = dest / item["path"]
        if not path.exists():
            raise SystemExit(f"expected deletion target missing: {item['path']}")
        package_json = path / "package.json"
        if not package_json.exists():
            raise SystemExit(f"deletion target has no package.json: {item['path']}")
        name = json.loads(package_json.read_text(encoding="utf-8")).get("name")
        if not name:
            raise SystemExit(f"deletion target has no package name: {item['path']}")
        removed_names.add(name)
        deleted_packages.append(
            {"path": item["path"], "package": name, "group": item["group"]}
        )

    if manifest["keep"]["p1_badge"] in removed_names:
        raise SystemExit("refusing to delete the retained 1017 badge")
    for name in manifest["keep"]["pending_disabled_20"]:
        if name in removed_names:
            raise SystemExit(f"refusing to delete pending package: {name}")

    pruned: list[dict] = []
    for item in deletion:
        target = dest / item["path"]
        shutil.rmtree(target)
        print(f"[trim] removed {item['path']} ({item['group']})")

    prune_package_json(dest, removed_names, pruned)
    edit_official_bundles(dest)
    edit_plugin_manager(dest)
    edit_cli_help(dest)
    build_surface = clean_build_surface(dest)

    verification = verify(dest, manifest, removed_names)
    removed_paths = [item["path"] for item in deletion]
    report = {
        "schema": 1,
        "source": manifest["source"],
        "destination": str(dest),
        "deleted_groups": manifest["deletion_groups"],
        "deleted_package_count": len(removed_paths),
        "deleted_paths": removed_paths,
        "deleted_packages": deleted_packages,
        "p1_deleted": [
            item["package"] for item in deleted_packages if item["group"] == "p1-deprecated"
        ],
        "pruned_dependency_edges": pruned,
        "build_surface": build_surface,
        "verification": verification,
        "notes": [
            "The retained 1017 badge is kept as instructed; client/Web UI workspace dependencies are pruned from its package.json because the frontend stack is gone.",
            "Only frontend/client packages and their Web-only bundles are deleted; backend, pending, and transitive packages stay.",
            "desktop-host remains in the tree but its desktop profile needs the deleted dsh-web-app bundle and browser UI roster; see docs/trimmed-runtime.md.",
        ],
    }
    (dest / "TRIM-REPORT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    after = workspace_packages(dest)
    print(
        f"[trim] packages before={len(before)} after={len(after)} removed={len(before) - len(after)}"
    )
    print(f"[trim] pruned package.json files={len(pruned)}")
    print(f"[trim] verification={json.dumps(verification, ensure_ascii=False)}")
    print(f"[trim] report={dest / 'TRIM-REPORT.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        sys.stderr.write(error.stderr or error.stdout or str(error))
        raise SystemExit(error.returncode or 1)
