# dsh-trimmed

A trimmed build of the DeepSeek Harness (`dsh`): **headless CLI + desktop-host
only**. The web/desktop frontend, the client web UI, and two self-declared
temporary/deprecated packages were removed under a conservative retention
policy (keep anything useful or possibly useful later). The desktop frontend
will be rebuilt separately; this repository contains **no built copy** and **no
`node_modules`** — CI regenerates the trimmed tree from the pinned upstream
source on every run, so what you see here is the recipe plus its evidence.

Upstream source: https://github.com/deepseek-ai/deepseek-harness,
pinned commit `22ddee3792402c3e70ec5f86a63c3e3e895a2f60`
(the commit the trim was developed and verified against).
Upstream code keeps its original license; the trim/repair scripts in
`tools/trim-dsh/` belong to the AEH project
(https://github.com/weimanmk/AEH).

## What is in this repo

| Path | What it is |
|---|---|
| `tools/trim-dsh/trim.py` | Reproduces the trim: copies the upstream source, deletes the manifest's deletion groups, prunes dangling workspace edges. Refuses to write into a running harness, the AEH repo, or the source clone. |
| `tools/trim-dsh/trim-manifest.json` | Deletion/retention manifest (88 deleted paths; 368 → 280 workspace entries). |
| `tools/trim-dsh/trim-report.json` | Report from the original trim run. |
| `tools/trim-dsh/repair-build.py` | Post-trim build repairs (pnpm patches, dangling tsconfig refs, file-upload seam restore, client-bundle stub, `hostPhase` opt-ins). Idempotent. Takes `--copy` (trimmed tree) and `--source` (upstream clone). |
| `tools/trim-dsh/verify_step18.py` | Isolated Step 18-style session runner (separate `DSH_HOME`/profile, synthetic task). |
| `tools/trim-dsh/loader-evidence-exec.mjs`, `run_loader_trim_build.py` | Loader-evidence scripts proving the 6 AEH plugin tools mount against the trimmed copy's own `node_modules`. |
| `tools/trim-dsh/evidence/` | Loader evidence, Step 18-style session evidence (including real-model 6/6 runs), boot-warning investigation, client-stub verification, and full test logs. All synthetic data; no secrets. |
| `docs/trimmed-runtime.md` | Full write-up: what was deleted and why, the repair steps, verification evidence, and the honest gaps. Read this first. |
| `docs/dsh-function-inventory.md` | Function inventory of the original dsh (368 entries) with the conservative retention classification. |
| `.github/workflows/package-windows.yml` | Windows packaging workflow (created via the GitHub web UI — the GitHub App cannot write workflow files via API). Regenerates, repairs, installs, builds `build:lib:host`, smoke-tests `--help`, and uploads the build outputs. See `PACKAGING-NOTES.md`. |

Not in this repo (by design): the 129 MB trimmed copy itself, `node_modules`,
built `lib/` outputs, the native addon, and the 82 MB before/after JSON
snapshots (regenerable with `tools/trim-dsh/snapshot.py`; kept local only).

## Build it yourself (Linux/macOS/Windows)

```sh
git clone https://github.com/deepseek-ai/deepseek-harness dsh-source
git -C dsh-source checkout 22ddee3792402c3e70ec5f86a63c3e3e895a2f60
python tools/trim-dsh/trim.py --source dsh-source --dest trimmed
python tools/trim-dsh/repair-build.py --copy trimmed --source dsh-source
cd trimmed
pnpm install        # pnpm 11; do NOT use --frozen-lockfile (the lockfile predates the trim)
pnpm run build:lib:host
node apps/cli/lib/bin.js --help
```

`trim.py` requires the source checkout to be clean and at the pinned commit
(pass `--allow-dirty-source` only if you know what you are doing). The native
addon (`build:native-system`) is only needed to start real sessions (file-lock
support); `--help` does not need it.

## Verified states (honest record)

- Loader evidence against the trimmed copy's own `node_modules`: 6/6 AEH
  tools mounted; execution variant exit 0 (see `evidence/loader-trim-build-*`).
- Synthetic and real-model (Sidrune `deepseek-v4-1-flash`) Step 18-style
  sessions against the built trimmed CLI: exit 0, all 6 `aeh_*` tools called
  exactly once in order, 0 errors.
- The 3 boot warnings (`typert`/`typert-loader`/`typert-gateway` did not
  activate) were eliminated in the local build via the `hostPhase` fix
  (`repair-build.py` step 7); CI re-verifies this on every run.
- AEH Python 641 tests / TypeScript 463 tests / `tsc --noEmit` green at the
  time of the trim (see `evidence/step19-verify-*` and `round3-verify-*`).

## Known gaps (not hidden)

- `apps/desktop-host` is retained but **cannot start via the original Desktop
  chain**: the Electron shell, the `web` profile template, and the web app it
  served were deleted. Restoring a desktop version means rebuilding the
  desktop frontend or re-pointing desktop-host at a headless/custom profile.
  See `docs/trimmed-runtime.md` §6.
- The client bundle preset in the trimmed tree is a verbatim-value stub:
  real client-asset bundling fails loud (verified). Do not expect a working
  web UI from this tree.
- The single-file Windows exe (Node SEA) is **unproven**: the CLI resolves
  workspace packages from `node_modules` and the native addon cannot load
  from inside a SEA blob. The workflow carries a best-effort SEA probe that
  does not fail the job; see `PACKAGING-NOTES.md`.
