# Step 18 isolated end-to-end evidence — trim-verify-20261027T132324Z

Synthetic session only. No real student data and no secret is present.

## Isolation

- isolated `DSH_HOME`: `/home/hatch/workspace/AEH/.trim-verify/home`
- isolated profile: `aeh-e2e`
- isolated runtime: `/home/hatch/workspace/AEH/.trim-verify/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js`
- synthetic entry: `/home/hatch/workspace/AEH/dsh-plugin/e2e/aeh-e2e-entry.ts`
- entry sha256: `e4709fda940e30c376d37ce0701cd60c937066b4a67440a9677883ce2fc00534`
- running harness `~/.dsh`, its npx install, and the harness clone: **untouched**

## Toolchain

| package | version |
|---|---|
| dsh | 0.2.1-rc.3 |
| dsh-base | 0.2.1-rc.3 |
| dsh-headless | 0.2.1-rc.3 |
| dsh-llm-pi-ai | 0.2.1-rc.3 |
| dsh-tools | 0.2.1-rc.3 |
| cordis | 4.0.5 |

- provider/model: `sidrune` / `deepseek-v4-1-flash`
- Node: `v24.22.1`

## Result

- exit code: `0`
- JSON events: 32
- tool calls / results: 6 / 6
- error events: 0

## Tool calls

| # | tool | input (truncated) | status | highlight |
|---|---|---|---|---|
| 1 | `aeh_check_curriculum` | `{"mode": "learn", "itemId": "item.fraction.add.001", "studentRef": "synthetic.student.s...` | completed | `{"allowed": true, "reasons": []}` |
| 2 | `aeh_check_curriculum` | `{"mode": "learn", "itemId": "item.fraction.multiply.001", "studentRef": "synthetic.stud...` | completed | `{"allowed": false, "reasons": ["kcs_not_allowed:kc.fraction.multiply"]}` |
| 3 | `aeh_update_hypotheses` | `{"operation": "spawn", "state": {"hypotheses": [], "unknownWeight": 0.5}, "hypothesis":...` | completed | `{"hypotheses": 1, "snapshotRef": "hyp_1"}` |
| 4 | `aeh_select_probe` | `{"mode": "learn", "studentRef": "synthetic.student.step18", "weights": {"hyp.adds_ok": ...` | completed | `{"itemId": "item.fraction.equiv.001", "score": -0.2953027976057393, "skipped": false}` |
| 5 | `aeh_schedule_review` | `{"state": {"learnerRef": "synthetic.student.step18", "memoryUnitId": "kc.fraction.add",...` | completed | `{"nextIntervalDays": 3.2, "stabilityDays": 3.2, "difficultyState": 4.8}` |
| 6 | `aeh_generate_report` | `{"audience": "teacher", "studentRef": "synthetic.student.step18", "windowStart": "2026-...` | completed | `{"attempts": 4, "independentCorrect": 3, "excluded": 0}` |

## Final answer

```text
Session complete — all four stages executed in order; no further tool calls.

**Final summary**

| Stage | Result |
|---|---|
| A1 gate `item.fraction.add.001` | **allowed = true** (no reasons; mode learn) |
| A2 gate `item.fraction.multiply.001` | **allowed = false** — fail-closed refusal `kcs_not_allowed:kc.fraction.multiply` |
| B1 hypotheses | `hyp.adds_ok` spawned, normalised to weight 1.0, unknown 0.0; dominant hypothesis `hyp.adds_ok`; snapshot `hyp_1` |
| B2 probe | **item.fraction.equiv.001** selected (score −0.2953; info gain 0.0731; gateAllowed true; required KC `kc.fraction.equiv`) |
| C1 review | **nextIntervalDays = 3.2**, target retention 0.9, stability 3.2 d, difficulty 4.8, retrievability at next review 0.9 |
| D1 report | **attempts = 4**, independent correct = 3, hints = 1, minutes = 10; independent accuracy 0.75; 1 authorised aggregate event used, 0 excluded; topic `kc.fraction.add` |

**Summary answers:** Gate decisions — add allowed, multiply refused. Selected probe — `item.fraction.equiv.001`. Review interval — 3.2 days. Report attempt total — 4 attempts (3 independent correct, 1 hint, 10 minutes).
```

## Evidence files

- `command.txt` — exact command, cwd, environment (credential redacted)
- `task.md` — the synthetic task text
- `profile.package.json` / `profile.cordis.patch.yml` — composed isolated profile
- `dump-config.txt` — `--dump-config` output proving the AEH row is composed
- `stdout.jsonl` — newline-delimited run events, including full tool inputs/results
- `stderr.log` — diagnostics (empty on success)
- `summary.json` — machine-readable summary of the same events
- `session-log/` — decompressed isolated session JSONL
- `metadata.json` — versions and hashes
