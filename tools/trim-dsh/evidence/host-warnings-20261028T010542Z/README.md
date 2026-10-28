# host-warnings-<ts>

Investigation of the trim-build startup warning
`dsh: warning: 3 entries did not activate`.

## Root cause

`packages/typert/registry` and `packages/api/gateway` each ship a
`tsdown.config.ts` that calls `clientBundle(...)` **without** `hostPhase`.
`packages/client/tsdown.client.ts` returns `SKIP_WORKSPACE_BUILD`
(`{ entry: '' }`) for the `host` face in that case, so the host-only bundle
step skips both packages and `lib/index.js` is never emitted. The base Loader
then reports:

- `typert` (`@deepseek-ai/dsh-typert-registry`): failed to import (`lib/index.js` missing)
- `typert-loader` (`@deepseek-ai/dsh-typert-loader`): pending (waits for `typert`)
- `typert-gateway` (`@deepseek-ai/dsh-api-gateway`): failed to import (`lib/index.js` missing)

`lib/types/index.js` exists for both; only the bundling step is missing.
A full build (`build:lib:all`) builds the node half in its client pass; a
host-only build never runs that pass.

## Fix

Add `hostPhase: true` to the `clientBundle(...)` options in both
`tsdown.config.ts` files. This is the preset's documented host-reflection
opt-in; it emits only the Node half and restores no frontend package. The
change is implemented idempotently as step 7 of
`tools/trim-dsh/repair-build.py` (`config-diff.patch` shows the exact edit).

## Verification (isolated hard-link copy; trim-build never written)

Copy: `.scratch/trim-fix-copy` (`cp -al` of `~/workspace/trim-build`). The two
edited files were unlinked before rewriting so the hard link could not write
through to the trim build.

| Run (`--env.DSH_BUILD_FACE host`) | `lib/index.js` |
|---|---|
| before fix, `api/gateway` | absent (`dist/` fallback only) |
| before fix, `typert/registry` | absent (`dist/` fallback only) |
| after fix, `api/gateway` | present, 75065 bytes, sha256 `c4a5664d…` |
| after fix, `typert/registry` | present, 24449 bytes, sha256 `03371d23…` |

Direct import check (`import-check.txt`): the same `lib/index.js` path fails
with `ERR_MODULE_NOT_FOUND` in `~/workspace/trim-build` and loads successfully
in the fixed copy, exporting `TypertRegistry` / `TypertGatewayService`.

## Scope / honest limits

- The existing `~/workspace/trim-build` is **not** modified and still prints the
  warning; removing it requires re-running `trim.py` + `repair-build.py` +
  `pnpm install` + `build:lib:host` (or applying the same two-line patch and
  re-bundling in a writable copy).
- No full rebuilt-CLI startup smoke was run, to avoid rewriting the shared
  trim build; verification stops at "the missing import target is now emitted
  and importable".
- Functional impact on headless sessions: none observed. The Step 18 synthetic
  session completed with exit 0 and all six tool calls while the warning was
  present.

## Files

| File | Content |
|---|---|
| `config-diff.patch` | exact two config edits |
| `*.host-face.before-fix.log` / `.after-fix.log` | tsdown host-face runs |
| `*.lib-index.js.sha256` | produced artifact hashes |
| `import-check.txt` | import before/after across both trees |
