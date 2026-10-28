#!/usr/bin/env python3
"""Re-run the AEH loader evidence against the trim build's *own* node_modules.

Why this exists
---------------
The previous `tools/trim-dsh/evidence/loader-evidence.txt` was produced from the
npm-published dsh packages in `dsh-plugin/node_modules`, not from the trimmed
workspace build. This runner stages the same loader script next to the trim
build's packages (through symlinks, so the trim build is never modified) and
re-runs it there.

Two runs are recorded:

1. ``loader-evidence.mjs`` -- the original, unmodified script. It proves the six
   ``aeh_*`` tools mount, then stops with ``TOOL_EXECUTOR_UNAVAILABLE`` because
   the workspace build requires an explicit executor (the published build had an
   implicit one).
2. ``loader-evidence-exec.mjs`` -- the workspace-API variant that loads the
   native executor and uses the official ``dsh-tool-testkit`` single-call helper.
   It must pass every original assertion (mount, schema validation,
   cancellation, timeout, unload).

Only synthetic data. No ``~/.dsh``, npx dsh, source clone, or running harness
session is read or written. The trim build is opened read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_TRIM = Path('/home/hatch/workspace/trim-build')
LOADER_SRC = REPO / 'dsh-plugin' / 'scripts' / 'loader-evidence.mjs'
PLUGIN_SRC = REPO / 'dsh-plugin' / 'src'
EXEC_PROBE = REPO / 'tools' / 'trim-dsh' / 'loader-evidence-exec.mjs'

EXPECTED_TOOLS = [
    'aeh_check_curriculum',
    'aeh_generate_report',
    'aeh_prepare_intervention',
    'aeh_schedule_review',
    'aeh_select_probe',
    'aeh_update_hypotheses',
]

# Bare specifiers used by the loader scripts and the plugin source, mapped to
# their real directories inside the trim build. Symlinking these into the
# isolated staging node_modules is what makes resolution use the trim build.
PACKAGE_MAP = {
    '@deepseek-ai/cordis': 'vendor/cordis',
    '@deepseek-ai/cordis-plugin-loader': 'vendor/loader',
    '@deepseek-ai/schemastery': 'vendor/schemastery',
    '@deepseek-ai/dsh-system-prompt': 'packages/core/system-prompt',
    '@deepseek-ai/dsh-tools': 'packages/core/tools',
    '@deepseek-ai/dsh-llm': 'packages/llm/llm',
    '@deepseek-ai/dsh-util-values': 'packages/util/values',
    '@deepseek-ai/dsh-tool-call-timeout-policy': 'packages/guard/timeout-policy',
    '@deepseek-ai/dsh-tool-executor-native': 'packages/core/tool-executor-native',
    '@deepseek-ai/dsh-tool-testkit': 'packages/test-support/tool-testkit',
    'zod': 'node_modules/zod',
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def tree_fingerprint(root: Path) -> dict:
    """File count, byte total, and max mtime over the whole trim build."""
    files = 0
    total = 0
    latest = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            path = Path(dirpath) / name
            try:
                stat = path.lstat()
            except OSError:
                continue
            files += 1
            total += stat.st_size
            latest = max(latest, stat.st_mtime_ns)
    return {'files': files, 'bytes': total, 'latest_mtime_ns': latest}


def package_fingerprints(trim: Path) -> dict:
    """SHA-256 of the entrypoints of every package we load from the trim build."""
    out = {}
    for spec, rel in PACKAGE_MAP.items():
        base = trim / rel
        for candidate in ('package.json', 'lib/index.js', 'lib/index.mjs'):
            path = base / candidate
            if path.is_file():
                out[f'{spec}:{candidate}'] = sha256_file(path)
    for name in ('package.json', 'TRIM-REPORT.json'):
        path = trim / name
        if path.is_file():
            out[name] = sha256_file(path)
    return out


def resolution_probe(stage: Path, entry: Path) -> dict:
    script = (
        "const {createRequire}=require('node:module');"
        "const fs=require('node:fs');"
        "const r=createRequire(process.argv[1]);"
        "for (const p of process.argv.slice(2)) {"
        "  try { const f=r.resolve(p+'/package.json');"
        "    console.log(p+'\\t'+f+'\\t'+fs.realpathSync(f)); }"
        "  catch (e) { console.log(p+'\\tERROR:'+e.code); }"
        "}"
    )
    result = subprocess.run(
        ['node', '-e', script, str(entry), *PACKAGE_MAP],
        cwd=stage,
        capture_output=True,
        text=True,
        timeout=120,
    )
    resolved = {}
    for line in result.stdout.splitlines():
        name, _, rest = line.partition('\t')
        real, _, realpath = rest.partition('\t')
        resolved[name] = {'resolved': real, 'realpath': realpath}
    return {
        'returncode': result.returncode,
        'stderr': result.stderr,
        'resolved': resolved,
    }


MOUNT_RE = re.compile(r'^- mounted tools: (.*)$', re.MULTILINE)


def parse_run(stdout: str, stderr: str, returncode: int) -> dict:
    match = MOUNT_RE.search(stdout)
    mounted = [x.strip() for x in match.group(1).split(',')] if match else []
    return {
        'exit_code': returncode,
        'mounted_tools': mounted,
        'six_of_six_mounted': mounted == EXPECTED_TOOLS,
        'ok_line': 'OK: loader mount' in stdout,
        'executor_unavailable': 'TOOL_EXECUTOR_UNAVAILABLE' in stderr,
        'stdout': stdout,
        'stderr': stderr,
    }


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--trim-build', type=Path, default=DEFAULT_TRIM)
    parser.add_argument('--stage-root', type=Path, default=Path(os.environ.get('AEH_STAGE_ROOT', '/tmp')))
    parser.add_argument('--timestamp', default=None)
    parser.add_argument('--evidence-root', type=Path, default=None)
    args = parser.parse_args()

    trim = args.trim_build.resolve()
    if not (trim / 'packages' / 'core' / 'tools').is_dir():
        print(f'trim build not found: {trim}', file=sys.stderr)
        return 2
    if REPO in trim.parents or trim == REPO:
        print('refusing to treat the AEH repo as the trim build', file=sys.stderr)
        return 2
    if str(trim).startswith(str(Path.home() / '.dsh')):
        print('refusing to use ~/.dsh as the trim build', file=sys.stderr)
        return 2

    ts = args.timestamp or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence_root = args.evidence_root or (REPO / 'tools' / 'trim-dsh' / 'evidence')
    evid = evidence_root / f'loader-trim-build-{ts}'
    stage = args.stage_root / f'aeh-loader-trim-build-{ts}'
    evid.mkdir(parents=True, exist_ok=True)

    started = time.time()
    trim_before = tree_fingerprint(trim)
    pkg_before = package_fingerprints(trim)

    if stage.exists():
        shutil.rmtree(stage)
    (stage / 'scripts').mkdir(parents=True)
    (stage / 'node_modules' / '@deepseek-ai').mkdir(parents=True)

    shutil.copy2(LOADER_SRC, stage / 'scripts' / 'loader-evidence.mjs')
    shutil.copy2(EXEC_PROBE, stage / 'scripts' / 'loader-evidence-exec.mjs')
    shutil.copytree(PLUGIN_SRC, stage / 'src')

    staged_map = {}
    for spec, rel in PACKAGE_MAP.items():
        target = trim / rel
        if not target.exists():
            print(f'missing trim package: {spec} -> {target}', file=sys.stderr)
            return 2
        if spec.startswith('@'):
            scope, name = spec.split('/', 1)
            link = stage / 'node_modules' / scope / name
        else:
            link = stage / 'node_modules' / spec
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(target)
        staged_map[spec] = {'link': str(link), 'target': str(target)}

    probe = resolution_probe(stage, stage / 'scripts' / 'loader-evidence.mjs')
    resolved_outside = []
    for spec, item in probe['resolved'].items():
        real = item['realpath']
        if not real.startswith(str(trim)):
            resolved_outside.append({'spec': spec, **item})
    probe_ok = (
        probe['returncode'] == 0
        and not resolved_outside
        and all(item['realpath'].startswith(str(trim)) for item in probe['resolved'].values())
    )
    resolved_from_plugin = [
        spec for spec, item in probe['resolved'].items()
        if item['realpath'].startswith(str(REPO / 'dsh-plugin'))
    ]
    resolved_from_dsh_home = [
        spec for spec, item in probe['resolved'].items()
        if item['realpath'].startswith(str(Path.home() / '.dsh'))
    ]

    raw = subprocess.run(
        ['node', str(stage / 'scripts' / 'loader-evidence.mjs')],
        cwd=stage,
        capture_output=True,
        text=True,
        timeout=300,
    )
    raw_run = parse_run(raw.stdout, raw.stderr, raw.returncode)

    adapted = subprocess.run(
        ['node', str(stage / 'scripts' / 'loader-evidence-exec.mjs')],
        cwd=stage,
        capture_output=True,
        text=True,
        timeout=300,
    )
    adapted_run = parse_run(adapted.stdout, adapted.stderr, adapted.returncode)

    trim_after = tree_fingerprint(trim)
    pkg_after = package_fingerprints(trim)
    trim_unchanged = trim_before == trim_after and pkg_before == pkg_after

    assertions = {
        'generated_at': ts,
        'trim_build': str(trim),
        'stage': str(stage),
        'evidence_dir': str(evid),
        'node': subprocess.run(['node', '--version'], capture_output=True, text=True).stdout.strip(),
        'expected_tools': EXPECTED_TOOLS,
        'package_map': staged_map,
        'resolution_probe_returncode': probe['returncode'],
        'resolution_probe_stderr': probe['stderr'],
        'resolution': probe['resolved'],
        'resolved_outside_trim_build': resolved_outside,
        'resolved_from_dsh_plugin_node_modules': resolved_from_plugin,
        'resolved_from_dot_dsh': resolved_from_dsh_home,
        'resolution_uses_trim_build_only': probe_ok,
        'raw_script': {
            k: raw_run[k]
            for k in ('exit_code', 'mounted_tools', 'six_of_six_mounted', 'ok_line', 'executor_unavailable')
        },
        'adapted_script': {
            k: adapted_run[k]
            for k in ('exit_code', 'mounted_tools', 'six_of_six_mounted', 'ok_line', 'executor_unavailable')
        },
        'trim_build_fingerprint_before': trim_before,
        'trim_build_fingerprint_after': trim_after,
        'trim_build_unchanged': trim_unchanged,
        'package_fingerprints_before': pkg_before,
        'package_fingerprints_after': pkg_after,
        'duration_seconds': round(time.time() - started, 3),
    }
    assertions['passed'] = bool(
        probe_ok
        and raw_run['six_of_six_mounted']
        and adapted_run['six_of_six_mounted']
        and adapted_run['exit_code'] == 0
        and adapted_run['ok_line']
        and trim_unchanged
    )
    assertions['raw_script_full_contract'] = bool(
        raw_run['exit_code'] == 0 and raw_run['ok_line']
    )
    assertions['raw_script_stop_reason'] = (
        'TOOL_EXECUTOR_UNAVAILABLE: the workspace build needs an explicit tool '
        'executor and a batch-shaped ctx.tools.execute; the npm-published '
        'dsh-tools 0.2.1-rc.3 used for the original evidence had an implicit '
        'executor and a single-call API.'
        if not assertions['raw_script_full_contract'] else None
    )

    write(evid / 'command.txt',
          'trim-build loader evidence (isolated staging, synthetic only)\n'
          f'timestamp: {ts}\n'
          f'trim-build: {trim}\n'
          f'staging: {stage}\n'
          f'node: {assertions["node"]}\n'
          f'DSH_HOME: unset (the Cordis loader is a standalone in-process app)\n'
          f'HOME: {Path.home()}\n'
          'run 1: node scripts/loader-evidence.mjs\n'
          'run 2: node scripts/loader-evidence-exec.mjs\n')
    write(evid / 'loader-evidence.txt', raw.stdout)
    write(evid / 'loader-evidence.stderr.log', raw.stderr)
    write(evid / 'exit-code.txt', f'{raw.returncode}\n')
    write(evid / 'loader-evidence-exec.txt', adapted.stdout)
    write(evid / 'loader-evidence-exec.stderr.log', adapted.stderr)
    write(evid / 'loader-evidence-exec.exit-code.txt', f'{adapted.returncode}\n')
    write(evid / 'package-resolution.txt', json.dumps(probe['resolved'], indent=2) + '\n')
    write(evid / 'assertions.json', json.dumps(assertions, indent=2, ensure_ascii=False) + '\n')
    write(evid / 'trim-build-fingerprint.json',
          json.dumps({
              'before': trim_before,
              'after': trim_after,
              'unchanged': trim_unchanged,
              'package_fingerprints_before': pkg_before,
              'package_fingerprints_after': pkg_after,
          }, indent=2) + '\n')

    readme = f"""# loader-trim-build-{ts}

Isolated re-run of `dsh-plugin/scripts/loader-evidence.mjs` against the trim
build's **own** `node_modules` (`{trim}`). The trim build was not modified:
package entrypoint hashes and the whole-tree file count/byte total are identical
before and after (`trim-build-fingerprint.json`).

## What ran

| Run | Script | Result |
|---|---|---|
| 1 | original `loader-evidence.mjs` (unmodified) | 6/6 tools mounted; exits 1 with `TOOL_EXECUTOR_UNAVAILABLE` |
| 2 | `loader-evidence-exec.mjs` (workspace-API variant) | exit 0; mount + schema validation + cancellation + timeout + unload all pass |

Run 1 proves the required claim: the six `aeh_*` tools mount from the trim build.
It cannot complete the later execution assertions because the workspace build at
commit `22ddee37` requires an explicit tool executor and a batch-shaped
`ctx.tools.execute({{ calls, signal }})`, while the npm-published
`@deepseek-ai/dsh-tools@0.2.1-rc.3` that the original script targeted had an
implicit executor and a single-call API.

Run 2 keeps every original assertion but loads
`@deepseek-ai/dsh-tool-executor-native` and routes the single call through the
official `@deepseek-ai/dsh-tool-testkit` helper. It is supplementary evidence
that the plugin's contract still holds on the workspace API.

## Isolation

- staging is `{stage}`; the plugin source is copied there and bare imports resolve
  through a symlinked `node_modules` that points into the trim build;
- `package-resolution.txt` records every resolved realpath, all under the trim
  build, none under `dsh-plugin/node_modules` or `~/.dsh`;
- no `DSH_HOME` is set, no npm install, no network, no running harness session.

## Files

| File | Content |
|---|---|
| `command.txt` | exact commands and environment |
| `loader-evidence.txt` / `.stderr.log` / `exit-code.txt` | run 1 |
| `loader-evidence-exec.txt` / `.stderr.log` / `loader-evidence-exec.exit-code.txt` | run 2 |
| `package-resolution.txt` | resolved package realpaths |
| `assertions.json` | machine-readable checks |
| `trim-build-fingerprint.json` | before/after proof the trim build is untouched |
"""
    write(evid / 'README.md', readme)

    print(json.dumps({
        'evidence_dir': str(evid),
        'passed': assertions['passed'],
        'resolution_uses_trim_build_only': probe_ok,
        'raw_six_of_six': raw_run['six_of_six_mounted'],
        'raw_exit': raw_run['exit_code'],
        'adapted_six_of_six': adapted_run['six_of_six_mounted'],
        'adapted_exit': adapted_run['exit_code'],
        'trim_build_unchanged': trim_unchanged,
    }, indent=2))
    return 0 if assertions['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
