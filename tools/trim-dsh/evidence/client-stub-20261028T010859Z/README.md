# client-stub-<ts> — fail-loud verification of the client bundle stub

Verifies the `repair-build.py` step-6 claim that real client asset bundling
fails loud after the AEH trim. The trimmed build itself was not written: all
builds ran in an isolated full copy (`.scratch/trim-client-test`, `cp -a`) and
a synthetic probe (`.scratch/asset-probe`).

## What the stub is

`trim-build/packages/client/tsdown.client.ts` no longer imports
`./modules/src/assets.ts`, `./modules/src/client/manifest.ts`,
`./web/src/platform.ts` (deleted with the frontend). Their values are inlined
verbatim under a `TRIM-BUILD STUB` comment. The inlined helpers are
byte-identical to the originals in
`deepseek-harness/packages/client/modules/src/assets.ts` and
`deepseek-harness/packages/client/web/src/platform.ts` (checked by diff).

## Results

| Attempt | Command (in copy) | Result |
|---|---|---|
| root client face | `tsdown --config-loader native --env.DSH_BUILD_FACE client` | exit 1, `ERROR UNRESOLVED_ENTRY Cannot resolve entry module lib/types/index.js` |
| `packages/extensions/cordis-client-runner` | same, client face | exit 1, same UNRESOLVED_ENTRY |
| `packages/client/connection` | same | exit 1, `lib/types/client/index.js` |
| `packages/client/file-upload` | same | exit 1, `lib/types/client/index.js` |
| `packages/client/ui-deepseek-model-label-1017` | same | exit 1, `lib/types/index.js` |
| synthetic asset probe | `tsdown --config-loader native --env.DSH_BUILD_FACE client` | exit 1, `[plugin dsh-package-asset] Error: tsdown: @synthetic/asset-probe: .../foo.svg needs package.json exports {"./assets/*":"./lib/assets/*"} and "lib/assets" in files`, top frame `tsdown.client.ts` `reference` |

No `client.browser.js` was produced anywhere in the copy after the root run
(count 0).

## Interpretation (honest)

- "Real client bundling fails loud and produces no client bundle" is **true**.
- The proximate cause is that the host-only trim never compiled the client
  halves (`lib/types/client/*`) and deleted `packages/client/modules`,
  `packages/client/web`, `packages/client/runtime`; it is **not** the inlined
  stub throwing. The earlier wording "fails loud via `packageAssets()`" is
  imprecise and is corrected in `docs/trimmed-runtime.md` §5(f).
- The `packageAssets()` guard the comment names does exist and does throw a
  clear error; it is upstream code, and the synthetic probe exercises it
  directly because no retained package ships `src/client/assets`.

## Files

| File | Content |
|---|---|
| `client-face-summary.txt` | exit codes per attempt |
| `packages_*.client-face.log` | per-package client-face output |
| `root-client-face.log` | workspace client-face output |
| `asset-probe.client-face.log` | `packageAssets()` fail-loud output |
