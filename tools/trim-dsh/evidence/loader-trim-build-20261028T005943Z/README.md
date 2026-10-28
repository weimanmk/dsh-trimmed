# loader-trim-build-20261028T005943Z

Isolated re-run of `dsh-plugin/scripts/loader-evidence.mjs` against the trim
build's **own** `node_modules` (`/home/hatch/workspace/trim-build`). The trim build was not modified:
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
`ctx.tools.execute({ calls, signal })`, while the npm-published
`@deepseek-ai/dsh-tools@0.2.1-rc.3` that the original script targeted had an
implicit executor and a single-call API.

Run 2 keeps every original assertion but loads
`@deepseek-ai/dsh-tool-executor-native` and routes the single call through the
official `@deepseek-ai/dsh-tool-testkit` helper. It is supplementary evidence
that the plugin's contract still holds on the workspace API.

## Isolation

- staging is `/tmp/aeh-loader-trim-build-20261028T005943Z`; the plugin source is copied there and bare imports resolve
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
