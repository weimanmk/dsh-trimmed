# Packaging notes (Windows)

The `package-windows.yml` workflow proves the reproducible path on a Windows
runner: regenerate the trimmed copy from the pinned upstream commit, repair,
`pnpm install`, `build:lib:host`, and `--help` smoke test. Its artifact
(`trimmed-dsh-windows-build`) contains the built CLI tree (`apps/`,
`package.json`, `pnpm-lock.yaml`, build report) — **not** a runnable
standalone program: running it still needs Node.js 24 and `node_modules`
(`pnpm install` in the artifact directory).

## What is not yet packaged

1. **Native addon.** Starting a real session needs the `system.node` file-lock
   addon (`build:native-system`, needs CMake + MSVC on Windows). It is
   deliberately not built in the workflow yet; `--help` does not need it, and
   the earlier Linux session failure (missing flock addon) showed exactly
   where a session would stop without it. Add a `build:native-system` step
   before any session-level smoke test.
2. **Single-file exe (Node SEA).** Unproven for this tree. Two concrete
   blockers: the CLI entry resolves workspace packages out of
   `node_modules` (a SEA blob embeds one file, not a package tree), and the
   native addon cannot be loaded from inside the SEA virtual filesystem
   (Node docs: native addons must be extracted to a temp file first). The
   workflow's SEA step is a best-effort probe (`continue-on-error`): it
   embeds the real CLI entry, tries to run the resulting exe with `--help`,
   and records the outcome in `sea-attempt.log`. Until that probe passes
   with a bundled entry point, do not call any produced `.exe` a release.
3. **Desktop.** The Electron shell was deleted from the trimmed tree, so
   there is no desktop installer to package from this repo. The desktop
   frontend must be rebuilt first (separate work, tracked in the AEH repo).

## Next packaging trials (in order)

1. Add `build:native-system` + a synthetic 6-tool session smoke on the
   runner (needs a model API key in Actions secrets; never commit one).
2. Bundle the CLI entry (e.g. tsdown single-file bundle of `apps/cli` +
   workspace deps) and retry the SEA probe against the bundle.
3. Only then consider an installer (e.g. Electron rebuilt frontend) or a
   signed release.
