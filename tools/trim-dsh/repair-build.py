#!/usr/bin/env python3
"""Phase 2 of the AEH dsh trim: make the trimmed copy buildable.

Run AFTER tools/trim-dsh/trim.py, on the build copy only (never on the
source clone, never on ~/.dsh). Usage:

    python3 tools/trim-dsh/repair-build.py --copy /path/to/build-copy

What trim.py alone leaves broken (found by building the copy on
2026-10-27, host-libraries build):

1. Unused pnpm patches: deleting the frontend orphans 6 patchedDependencies
   (electron osx-sign, fortune-sheet, app-builder-lib, exceljs, lexical).
   pnpm aborts the install on ERR_PNPM_UNUSED_PATCH. The entries and patch
   files are removed from the copy.
2. Dangling seam consumer: packages/api/workspace-controller imports the
   deleted @deepseek-ai/dsh-host-directory-picker seam. The whole seam is
   removed from that package (directory-picker.ts, its test, the type
   re-exports and failure vocabulary, the Loader registration, and the
   tsconfig file/reference entries).
3. Dangling tsconfig references: 20 tsconfig files reference deleted
   packages. Reference objects and "files" entries whose target does not
   exist are dropped line-surgically (no reformatting of untouched files).
4. Over-deleted transport seam: packages/client/file-upload is a small
   transport/protocol package (no UI) that kept host code imports. It is
   restored from the source clone, its peer/dev edges in session-controller
   are restored, its tsconfig reference is restored, and its paths mappings
   are restored in tsconfig.base.json.
5. Dev/web-only packages in the host compile set: harness-dev-context
   (Web GUI dev context), webworker-runtime and webworker-packer
   (experimental web-worker tooling) are deleted with their aggregate
   references in tsconfig.host.json.
6. Client bundle preset: packages/client/tsdown.client.ts imports three
   files from deleted client packages. Their values are inlined verbatim
   (asset constants/pure functions, platform module list, manifest helper)
   with a TRIM-BUILD STUB comment; client-asset bundling is out of scope
   for the host-only build and fails loud if attempted.
7. Host-half opt-in for two dual packages loaded by the base/headless
   profile: packages/typert/registry and packages/api/gateway call
   clientBundle() without `hostPhase`, so the preset returns
   SKIP_WORKSPACE_BUILD for the host face and the host-only build never emits
   their lib/index.js. The base Loader then reports "3 entries did not
   activate" (typert @deepseek-ai/dsh-typert-registry failed to import,
   typert-loader pending, typert-gateway @deepseek-ai/dsh-api-gateway failed
   to import). Adding `hostPhase: true` emits only their Node half in the host
   pass; no frontend package is restored. Headless sessions already ran
   despite the warning; this removes the noise and the latent import failure.
8. Dead-surface files excluded from the host typecheck: files under
   scripts/, the web profile CLI tests, a browser benchmark and one
   gateway spec import only deleted modules (apps/web, apps/desktop,
   client/modules, frontend static), and the root tsconfig.host.json
   include globs pull them into `tsc -p`, which then fails with TS2307
   (found by running the full build:lib:host locally; the earlier
   "exit 0" record covered only the host-face tsdown passes, never this
   tsc step). They stay on disk (a future desktop rebuild may need
   them) and are added to the root tsconfig.host.json "exclude" array
   instead of deleted; anything still imported by kept code is pulled
   back into the program by tsc and would fail loudly, so the exclusion
   cannot hide a live dependency.
9. Root scripts: build:lib:host ends with a pnpm --filter bundle step for
   @deepseek-ai/dsh-desktop, which was deleted with the frontend, so the
   filter matches nothing and fails. The tail is dropped when the package
   is absent, and the three script entries that invoke deleted scripts
   (verify-package-dependencies, verify-client-packages, constraints)
   are removed.

All steps are idempotent: re-running on an already-repaired copy changes
nothing. The script refuses to run inside the AEH repository or on the
source clone.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

SOURCE = Path("/home/hatch/workspace/deepseek-harness")


def refuse(path: Path, label: str, source: Path = SOURCE) -> None:
    if path.resolve() == Path("/home/hatch/workspace/AEH").resolve():
        raise SystemExit(f"refusing {label}: destination inside the AEH repository")
    if path.resolve() == source.resolve():
        raise SystemExit(f"refusing {label}: must not modify the source clone")


def drop_lines_with(path: Path, needles: tuple[str, ...]) -> bool:
    lines = path.read_text().splitlines(keepends=True)
    kept = [ln for ln in lines if not any(n in ln for n in needles)]
    if len(kept) != len(lines):
        path.write_text("".join(kept))
        return True
    return False


def ref_ok(base: Path, rp: str) -> bool:
    ap = os.path.normpath(base / rp)
    if os.path.isfile(ap):
        return True
    if os.path.isdir(ap):
        return any(
            os.path.exists(os.path.join(ap, x))
            for x in ("tsconfig.json", "tsconfig.host.json", "tsconfig.client.json")
        )
    return os.path.isfile(ap + ".json")


def prune_tsconfigs(root: Path) -> list[str]:
    """Drop dangling tsconfig reference/file entries, line-surgically."""
    changed: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if "node_modules" in dirpath:
            continue
        dirnames[:] = [d for d in dirnames if d != "node_modules"]
        for name in filenames:
            if not (name == "tsconfig.json" or (name.startswith("tsconfig.") and name.endswith(".json"))):
                continue
            path = Path(dirpath) / name
            lines = path.read_text().splitlines(keepends=True)
            out: list[str] = []
            i = 0
            dropped = 0
            in_refs = in_files = False
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                if stripped.startswith('"references"'):
                    in_refs, in_files = True, False
                    out.append(line)
                    i += 1
                    continue
                if stripped.startswith('"files"'):
                    in_files, in_refs = True, False
                    out.append(line)
                    i += 1
                    continue
                if in_refs and stripped == "]":
                    in_refs = False
                    out.append(line)
                    i += 1
                    continue
                if in_files and stripped == "]":
                    in_files = False
                    out.append(line)
                    i += 1
                    continue
                if in_refs and stripped.startswith("{"):
                    j = i
                    buf = []
                    while j < len(lines):
                        buf.append(lines[j])
                        if "}" in lines[j]:
                            break
                        j += 1
                    m = re.search(r'"path"\s*:\s*"([^"]+)"', "".join(buf))
                    if m and not ref_ok(Path(dirpath), m.group(1)):
                        dropped += 1
                        i = j + 1
                        continue
                    out.extend(buf)
                    i = j + 1
                    continue
                if in_files:
                    m = re.match(r'\s*"([^"]+)"\s*,?\s*$', line)
                    if m and not os.path.exists(os.path.normpath(Path(dirpath) / m.group(1))):
                        dropped += 1
                        i += 1
                        continue
                    out.append(line)
                    i += 1
                    continue
                out.append(line)
                i += 1
            if dropped:
                path.write_text("".join(out))
                changed.append(str(path.relative_to(root)))
    return changed


def insert_ts_reference(path: Path, anchor: str, ref: str) -> bool:
    """Insert a {"path": ref} entry after the anchor's reference object.

    Returns True if the reference is present afterwards. The anchor's
    object may be single-line or multi-line; the scan stops at the first
    line at or after the anchor that contains the closing brace, so both
    formats work. (The previous implementation required the anchor's path
    line itself to end with "},", which the multi-line format never does,
    so the session-controller host reference was silently never restored
    and the Windows CI build failed with TS6059/TS6307 in run #1.)"""
    lines = path.read_text().splitlines(keepends=True)
    if any(ref in ln for ln in lines):
        return True
    insert_at = None
    for i, ln in enumerate(lines):
        if anchor in ln:
            j = i
            while j < len(lines) and "}" not in lines[j]:
                j += 1
            if j >= len(lines):
                return False
            if lines[j].strip() == "}":
                lines[j] = lines[j].replace("}", "},", 1)
            insert_at = j + 1
            break
    if insert_at is None:
        return False
    indent = lines[insert_at - 1][: len(lines[insert_at - 1]) - len(lines[insert_at - 1].lstrip())]
    entry = indent + "{\n" + indent + f'  "path": "{ref}"\n' + indent + "},\n"
    lines.insert(insert_at, entry)
    path.write_text("".join(lines))
    return any(ref in ln for ln in path.read_text().splitlines())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy", required=True, help="trimmed build copy directory")
    ap.add_argument(
        "--source",
        type=Path,
        default=SOURCE,
        help="upstream dsh source clone (file-upload seam is restored from it)",
    )
    args = ap.parse_args()
    root = Path(args.copy)
    source = args.source
    refuse(root, "--copy", source)
    if not (root / "pnpm-workspace.yaml").exists():
        raise SystemExit(f"not a dsh build copy: {root}")

    report: dict = {}

    # 1. Unused pnpm patches.
    ws = root / "pnpm-workspace.yaml"
    drop_patches = (
        "@electron/osx-sign",
        "@fortune-sheet/core",
        "@fortune-sheet/react",
        "app-builder-lib",
        "exceljs",
        "lexical",
    )
    lines = ws.read_text().splitlines(keepends=True)
    kept = [
        ln
        for ln in lines
        if not any(
            ln.strip().startswith(f"'{d}@") or ln.strip().startswith(f"{d}@")
            for d in drop_patches
        )
    ]
    if len(kept) != len(lines):
        ws.write_text("".join(kept))
    removed_patches = []
    for patch_file in (
        "patches/@electron__osx-sign@1.3.3.patch",
        "patches/@fortune-sheet__core@1.0.4.patch",
        "patches/@fortune-sheet__react@1.0.4.patch",
        "patches/app-builder-lib@26.17.0.patch",
        "patches/exceljs@4.4.0.patch",
        "patches/lexical@0.49.0.patch",
    ):
        target = root / patch_file
        if target.exists():
            target.unlink()
            removed_patches.append(patch_file)
    report["unused_patches_removed"] = removed_patches

    # 2. Directory-picker seam removal from workspace-controller.
    wc = root / "packages/api/workspace-controller"
    for victim in (wc / "src/directory-picker.ts", wc / "tests/directory-picker.host.spec.ts"):
        if victim.exists():
            victim.unlink()
    types_path = wc / "src/types.ts"
    s = types_path.read_text()
    s = s.replace(
        """ * Browser-safe request, result, and state-stream vocabulary for the Workspace
 * and directory-picking Remote namespaces this package owns. The picking seam
 * declares its own listing types, so they are re-exported here rather than
 * restated: a browser consumer reads the very declaration the backend answers.
""",
        """ * Browser-safe request, result, and state-stream vocabulary for the Workspace
 * Remote namespace this package owns. The directory-picking seam was removed
 * with the frontend trim, so its listing types and failure vocabulary are gone.
""",
    )
    s = s.replace(
        "export type { DirectoryEntry, DirectoryListing } from '@deepseek-ai/dsh-host-directory-picker/types'\n",
        "",
    )
    for entry in (
        "    /** The verb needs an interaction the composed backend does not serve. */\n    'directory-picker/unavailable': { readonly capability: string }\n",
        "    /** The target is not fully qualified, or the backend cannot list it. */\n    'directory-picker/unreadable': { readonly path: string }\n",
        "    /** A child of that name is already there. */\n    'directory-picker/exists': { readonly path: string }\n",
        "    /** The parent is not fully qualified, the name is not one segment, or creation failed. */\n    'directory-picker/create-failed': { readonly path: string }\n",
    ):
        s = s.replace(entry, "")
    types_path.write_text(s)
    index_path = wc / "src/index.ts"
    s = index_path.read_text()
    s = s.replace("import { DirectoryPickerController } from './directory-picker.ts'\n", "")
    s = s.replace("export { DirectoryPickerController } from './directory-picker.ts'\n", "")
    s = s.replace(
        """    // This package is the Loader entry for both Remote owners it hosts: the
    // directory-picking seam is abstract and never an entry itself. The child
    // stays pending until a picking backend is composed, so a host without one
    // registers no picking namespace instead of answering an unservable verb.
    ctx.plugin(DirectoryPickerController)
""",
        "",
    )
    index_path.write_text(s)
    report["directory_picker_seam_removed"] = True

    # 3. Dangling tsconfig references (also covers the workspace-controller
    # tsconfig file/reference entries from step 2).
    report["tsconfigs_pruned"] = prune_tsconfigs(root)

    # 4. Restore the file-upload transport seam.
    fu_src = source / "packages/client/file-upload"
    fu_dst = root / "packages/client/file-upload"
    if not fu_dst.exists():
        shutil.copytree(fu_src, fu_dst)
    sc_pkg = root / "packages/api/session-controller/package.json"
    d = json.loads(sc_pkg.read_text())
    for section in ("devDependencies", "peerDependencies"):
        d.setdefault(section, {})["@deepseek-ai/dsh-client-file-upload"] = "workspace:*"
    sc_pkg.write_text(json.dumps(d, indent=2) + "\n")
    sc_ts = root / "packages/api/session-controller/tsconfig.host.json"
    host_ok = insert_ts_reference(
        sc_ts, '"path": "../../core/session"', "../../client/file-upload/tsconfig.host.json"
    )
    sc_client_ts = root / "packages/api/session-controller/tsconfig.client.json"
    client_ok = True
    if sc_client_ts.exists():
        client_ok = insert_ts_reference(
            sc_client_ts, '"path": "../../core/session"', "../../client/file-upload/tsconfig.client.json"
        )
    base_ts = root / "tsconfig.base.json"
    lines = base_ts.read_text().splitlines(keepends=True)
    if not any("dsh-client-file-upload" in ln for ln in lines):
        out = []
        for ln in lines:
            out.append(ln)
            if '"@deepseek-ai/dsh-client-connection":' in ln:
                indent = ln[: len(ln) - len(ln.lstrip())]
                out.append(indent + '"@deepseek-ai/dsh-client-file-upload": ["./packages/client/file-upload/src"],\n')
                out.append(indent + '"@deepseek-ai/dsh-client-file-upload/types": ["./packages/client/file-upload/src/types.ts"],\n')
        base_ts.write_text("".join(out))
    base_ok = "dsh-client-file-upload" in base_ts.read_text()
    report["file_upload_seam_restored"] = bool(host_ok and client_ok and base_ok)
    if not report["file_upload_seam_restored"]:
        raise SystemExit(
            "repair-build: file-upload seam restore failed "
            f"(host={host_ok} client={client_ok} base={base_ok}); refusing to report success"
        )

    # 5. Delete dev/web-only packages from the host compile set.
    deleted = []
    for rel in (
        "packages/context/harness-dev-context",
        "packages/experimental/webworker-runtime",
        "packages/experimental/webworker-packer",
    ):
        target = root / rel
        if target.exists():
            shutil.rmtree(target)
            deleted.append(rel)
    host_ts = root / "tsconfig.host.json"
    drop_lines_with(host_ts, ("harness-dev-context", "webworker-runtime", "webworker-packer"))
    report["dev_web_packages_deleted"] = deleted

    # 6. Client bundle preset stub (values inlined verbatim from the deleted
    # sources; see the TRIM-BUILD STUB comment written into the file).
    preset = root / "packages/client/tsdown.client.ts"
    s = preset.read_text()
    if "./modules/src/assets.ts" in s:
        old = """import {
  PACKAGE_ASSET_EXPORT,
  PACKAGE_ASSET_EXPORT_TARGET,
  PACKAGE_ASSET_FILES_ENTRY,
  PACKAGE_ASSET_MEDIA_TYPES,
  packageAssetMediaType,
  packageAssetReference,
  packageAssetRevision,
  packageAssetRevisionedPath,
} from './modules/src/assets.ts'
import { optionalStringArray } from './modules/src/client/manifest.ts'
import { PLATFORM_MODULES, PRELOADED_CLIENT_EXTERNALS } from './web/src/platform.ts'
"""
        new = """// TRIM-BUILD STUB (AEH approved trim: frontend deleted, host + desktop-host only).
// The client asset/module sources this preset imported (packages/client/modules,
// packages/client/web) were deleted with the frontend. Their values are inlined
// verbatim below so host-face config loading and host bundling keep working.
// Any actual client-asset bundling fails loud via packageAssets() below, which
// is unreachable in host builds. Restore the deleted packages to rebuild the
// desktop frontend.
import { createHash } from 'node:crypto'
const PACKAGE_ASSET_SEGMENT = 'assets'
const PACKAGE_ASSET_MEDIA_TYPES: ReadonlyMap<string, string> = new Map([
  ['.svg', 'image/svg+xml'],
  ['.png', 'image/png'],
  ['.webp', 'image/webp'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
])
const PACKAGE_ASSET_EXPORT = './assets/*'
const PACKAGE_ASSET_EXPORT_TARGET = './lib/assets/*'
const PACKAGE_ASSET_FILES_ENTRY = 'lib/assets'
const PACKAGE_ASSET_REVISION_LENGTH = 12
function packageAssetMediaType(assetPath: string): string | undefined {
  const name = assetPath.slice(Math.max(assetPath.lastIndexOf('/'), assetPath.lastIndexOf('\\\\')) + 1)
  const dot = name.lastIndexOf('.')
  return dot <= 0 ? undefined : PACKAGE_ASSET_MEDIA_TYPES.get(name.slice(dot).toLowerCase())
}
function packageAssetRevision(bytes: Uint8Array): string {
  return createHash('sha1').update(bytes).digest('hex').slice(0, PACKAGE_ASSET_REVISION_LENGTH)
}
function packageAssetRevisionedPath(assetPath: string, rev: string): string {
  const dot = assetPath.lastIndexOf('.')
  return dot > assetPath.lastIndexOf('/') + 1
    ? `${assetPath.slice(0, dot)}-${rev}${assetPath.slice(dot)}`
    : `${assetPath}-${rev}`
}
function packageAssetReference(packageName: string, emittedPath: string): string {
  const path = emittedPath.split('/')
    .map(segment => encodeURIComponent(segment).replace(/[!'()*]/gu, char => `%${char.charCodeAt(0).toString(16).toUpperCase()}`))
    .join('/')
  return `plugins/${packageName}/${PACKAGE_ASSET_SEGMENT}/${path}`
}
function optionalStringArray(subject: string, field: string, value: unknown): string[] | undefined {
  if (value === undefined) return undefined
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string')) {
    throw new Error(`client-modules: ${subject} ${field} must be a string array`)
  }
  return value as string[]
}
const PLATFORM_MODULES = [
  'react', 'react/jsx-runtime', 'react-dom', 'react-dom/client', '@deepseek-ai/cordis',
  'zod', '@tanstack/react-virtual', '@deepseek-ai/dsh-client-store',
  '@deepseek-ai/dsh-client-ui-slots',
  '@deepseek-ai/dsh-client-ui-primitives',
  '@deepseek-ai/dsh-client-ui-dockkit',
] as const
const PRELOADED_CLIENT_EXTERNALS = [] as const
"""
        assert old in s, "preset import block not found; already stubbed or upstream changed"
        preset.write_text(s.replace(old, new))
        report["preset_stub_applied"] = True
    else:
        report["preset_stub_applied"] = False

    # 7. Host-half opt-in for the two dual packages the base profile loads. A
    # package-local tsdown.config.ts replaces the root workspace layout; with
    # clientBundle() and no hostPhase the host face returns SKIP_WORKSPACE_BUILD
    # and lib/index.js is never built, so the Loader warns that the typert and
    # typert-gateway entries failed to import. hostPhase is the preset's
    # documented host-reflection opt-in and touches no frontend package.
    host_half_opt_ins = []
    for rel in (
        "packages/typert/registry/tsdown.config.ts",
        "packages/api/gateway/tsdown.config.ts",
    ):
        path = root / rel
        if not path.exists():
            continue
        s = path.read_text()
        if "hostPhase" in s:
            continue
        assert "{ dualClient: true }" in s, f"unexpected tsdown config: {rel}"
        path.write_text(s.replace("{ dualClient: true }", "{ dualClient: true, hostPhase: true }"))
        host_half_opt_ins.append(rel)
    report["host_half_opt_ins"] = host_half_opt_ins

    # 8. Exclude dead-surface files from the host typecheck program
    # (root tsconfig.host.json is JSONC: comments allowed, so edit lines,
    # never json round-trip). Explicit file entries only: broad globs
    # like scripts/verify-*.ts would swallow live verifiers.
    dead_surface_files = [
        # Whole web-profile e2e subtree: every file in it scaffolds the
        # deleted web profile (importers pull excluded files back in with
        # TS6307, so single-file excludes cascade; the subtree is 100%
        # web-only, verified by listing it).
        "apps/cli/tests/profiles/web/tests/**/*.ts",
        "apps/cli/tests/web-agent-presets.e2e.ts",
        "benchmarks/long-session-browser/long-session.bench.ts",
        "packages/api/gateway/tests/operator-connect.host.spec.ts",
        "scripts/browser-bundled-externals.ts",
        "scripts/browser-bundled-externals.spec.ts",
        "scripts/check-workspace-constraints.ts",
        "scripts/check-workspace-constraints.spec.ts",
        "scripts/client-asset-types.spec.ts",
        "scripts/optional-bundles.spec.ts",
        "scripts/shipped-locales.spec.ts",
        "scripts/verify-client-packages.ts",
        "scripts/verify-client-packages.spec.ts",
        "scripts/verify-package-dependencies.ts",
        "scripts/verify-package-dependencies.spec.ts",
        "scripts/web-product-bundle-isolation.spec.ts",
        "scripts/windows-build-workspace.spec.ts",
        "scripts/benchmark-next-package-dependency.ts",
        "scripts/benchmark-next-package-dependency.spec.ts",
        "scripts/verify-product-use.ts",
        "scripts/verify-product-use.spec.ts",
        "scripts/verify-default-product-isolation.ts",
        "scripts/verify-default-product-isolation.spec.ts",
        "scripts/gen-third-party-notices.ts",
        "scripts/gen-third-party-notices.spec.ts",
    ]
    host_ts = root / "tsconfig.host.json"
    lines = host_ts.read_text().splitlines(keepends=True)
    marker = "TRIM: host build excludes files that only exercise deleted surfaces"
    excl_start = next(
        i for i, ln in enumerate(lines) if ln.strip().startswith('"exclude"')
    )
    excl_end = next(
        i for i in range(excl_start, len(lines)) if lines[i].strip() in ("]", "],")
    )
    block_text = "".join(lines[excl_start:excl_end])
    missing = [rel for rel in dead_surface_files if f'"{rel}"' not in block_text]
    if missing:
        if lines[excl_end - 1].strip() and not lines[excl_end - 1].rstrip().endswith(","):
            lines[excl_end - 1] = lines[excl_end - 1].rstrip("\n") + ",\n"
        block = []
        if not any(marker in ln for ln in lines):
            block.append(f"    // {marker}; kept on disk for a future desktop rebuild.\n")
        block += [f'    "{rel}",\n' for rel in missing]
        lines[excl_end:excl_end] = block
        host_ts.write_text("".join(lines))
    after = host_ts.read_text()
    missing = [rel for rel in dead_surface_files if f'"{rel}"' not in after]
    if missing:
        raise SystemExit(f"repair-build: host excludes missing: {missing}")
    report["host_excludes_added"] = dead_surface_files

    # 9. Root package.json scripts: drop the deleted desktop bundle tail
    # from build:lib:host and the entries invoking deleted scripts.
    root_pkg = root / "package.json"
    d = json.loads(root_pkg.read_text())
    desktop_present = False
    for pattern in ("apps/*/package.json", "apps/*/*/package.json",
                    "packages/*/package.json", "packages/*/*/package.json"):
        for pkg_path in root.glob(pattern):
            if json.loads(pkg_path.read_text()).get("name") == "@deepseek-ai/dsh-desktop":
                desktop_present = True
                break
        if desktop_present:
            break
    scripts = d.get("scripts", {})
    if not desktop_present and "build:lib:host" in scripts:
        scripts["build:lib:host"] = scripts["build:lib:host"].replace(
            " && pnpm --filter @deepseek-ai/dsh-desktop run bundle", ""
        )
    for dead_script in (
        "verify-package-dependencies",
        "verify-client-packages",
        "verify-product-use",
        "constraints",
    ):
        scripts.pop(dead_script, None)
    d["scripts"] = scripts
    root_pkg.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    d2 = json.loads(root_pkg.read_text())
    assert "dsh-desktop" not in d2["scripts"].get("build:lib:host", "")
    assert not any(
        s in d2["scripts"]
        for s in (
            "verify-package-dependencies",
            "verify-client-packages",
            "verify-product-use",
            "constraints",
        )
    )
    report["root_scripts_pruned"] = True

    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
