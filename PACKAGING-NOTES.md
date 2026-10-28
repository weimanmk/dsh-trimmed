# Packaging notes (Windows)

The `package-windows.yml` workflow proves the reproducible path on a Windows
runner: regenerate the trimmed copy from the pinned upstream commit, repair,
`pnpm install`, `build:lib:host`, and `--help` smoke test. Its artifact
(`trimmed-dsh-windows-build`) contains the built CLI tree (`apps/`,
`package.json`, `pnpm-lock.yaml`, build report) — **not** a runnable
standalone program: running it still needs Node.js 24 and `node_modules`
(`pnpm install` in the artifact directory).

The workflow also builds a Windows installer (`dsh-trimmed-setup.exe`,
uploaded as the `dsh-trimmed-setup` artifact). See "Installer" below.

## Installer (`dsh-trimmed-setup.exe`)

Per-user Inno Setup 6 installer, **unsigned** (SmartScreen will warn;
"More info" -> "Run anyway"). It installs the headless CLI only — no
desktop frontend exists in this tree — with a bundled Node 24.22.1,
adds the install folder to the user's PATH (`dsh-trimmed` command),
creates a Start Menu entry, and ships an uninstaller. User data
(`%USERPROFILE%\.dsh`) is never touched by install or uninstall.

How the runtime tree is packaged: `pnpm deploy --prod --legacy` produces
the runnable closure, then `tools/packaging/stage-installer.py` repairs
19 peer-only packages the deploy drops (e.g. `@deepseek-ai/cordis-plugin-group`,
a peer of `dsh-app-boot` the CLI never declares) and snapshots the tree
into a content store (one copy per unique real file) plus
`app-manifest.json`. The installer recreates the tree once via
`setup-tree.cjs`: files as hardlinks from the store, directory links as
NTFS junctions (no elevation needed), which preserves Node's
`node_modules` resolution exactly as pnpm laid it out. Shipping symlinks
directly was rejected: recreating them needs elevation/Developer Mode,
and expanding every link duplicates shared files once per referrer
(a trial run passed 11 GB and kept growing; the snapshot store is
864 MB / 59,340 files). One platform-only link is skipped at snapshot
time (a macOS-only package, broken in the source tree too).

Smoke coverage: the workflow silently installs into a temp dir, runs the
installed `dsh-trimmed.cmd --help` with a fresh `DSH_HOME`, then silently
uninstalls and verifies the dir is gone. No real session is smoke-tested:
that needs a model API key in Actions secrets (never commit one). The
installer is not signed and no release is published from it yet.

## What is not yet packaged

1. **Native addon (Windows: not needed).** On Windows, sessions use the
   Harness's existing semaphore-based flock implementation — no Windows
   platform package exists for the native addon and none is needed
   (`native/system/AGENTS.md`). The earlier session failure from a
   missing flock addon was on Linux, where `build:native-system` (CMake)
   is required before any session-level smoke test.
2. **Single-file exe (Node SEA).** Unproven for this tree. Three concrete
   blockers: the CLI entry resolves workspace packages out of
   `node_modules` (a SEA blob embeds one file, not a package tree); the
   native addon cannot be loaded from inside the SEA virtual filesystem
   (Node docs: native addons must be extracted to a temp file first); and
   blob injection is not a Node flag at all. Run #5 evidence
   (2026-10-28): the probe's `node --build-sea` failed with `bad option`
   on Node 24.22.1 — injection needs `postject` (or an equivalent tool),
   which the probe did not use, so its exe was a plain node copy printing
   node help. Next trial: inject the blob with postject, then re-probe;
   the node_modules/native-addon blockers remain. The workflow's SEA step
   stays a best-effort probe (`continue-on-error`): it embeds the real CLI
   entry, tries to run the resulting exe with `--help`, and records the
   outcome in `sea-attempt.log`. Until that probe passes with a bundled
   entry point, do not call any produced `.exe` a release.
3. **Desktop.** The Electron shell was deleted from the trimmed tree, so
   there is no desktop installer to package from this repo. The desktop
   frontend must be rebuilt first (separate work, tracked in the AEH repo).

## Next packaging trials (in order)

1. A synthetic 6-tool session smoke on the runner, through the
   *installed* CLI (needs a model API key in Actions secrets; never
   commit one). This is the first proof the installer runs real sessions.
2. Bundle the CLI entry (e.g. tsdown single-file bundle of `apps/cli` +
   workspace deps) and retry the SEA probe against the bundle.
3. Only then consider a signed release (code-signing certificate) or a
   desktop installer (needs the desktop frontend rebuilt first).
