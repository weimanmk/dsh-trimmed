# tools/trim-dsh

AEH 已批准的精简（P1 + 前端删除）的可复现脚本、清单、快照与证据。

## 文件

| 文件 | 用途 |
|---|---|
| `trim.py` | 从只读源克隆复制到构建副本，删除清单内路径，清理悬空 workspace 依赖、根脚本和 tsconfig，生成 `TRIM-REPORT.json` |
| `trim-manifest.json` | 删除/保留/例外/desktop-host 缺口的机器可读清单 |
| `snapshot.py` | 对四个受保护路径做 SHA-256 只读快照 |
| `snapshots/before.json` / `after.json` | 精简前后的受保护路径快照 |
| `verify_step18.py` | 复用 `step18/run-e2e.py`，只把隔离路径重绑到 `.trim-verify/` |
| `evidence/` | 本次真实运行的 log、Step 18 证据、快照对比 |

## 复现

默认目标就是最初请求的 `/home/hatch/workspace/dsh-trimmed`：

```bash
cd /home/hatch/workspace/AEH
python3 tools/trim-dsh/trim.py \
  --source /home/hatch/workspace/deepseek-harness \
  --dest /home/hatch/workspace/dsh-trimmed \
  --json-report tools/trim-dsh/trim-report.json
```

本会话的沙箱只允许写 `/home/hatch/workspace/AEH`（以及部分 `/tmp`），
`/home/hatch/workspace/dsh-trimmed` 被拒绝；因此本次实际构建副本是
`/tmp/dsh-trimmed`：

```bash
python3 tools/trim-dsh/trim.py --dest /tmp/dsh-trimmed \
  --json-report tools/trim-dsh/trim-report.json
```

脚本本身不依赖目标路径；在有写权限的会话里把 `--dest` 指回请求路径即可。
脚本拒绝写入 `~/.dsh`、源克隆、npx 缓存、`step18/runtime`、`references/`、`spec/`，
也拒绝写入 AEH 仓库内部，避免把 200 MB 级副本塞进项目。

## 约束

- 只删清单内的 88 个路径；不删 20 个待确认包、不删 1017 徽章包、不删其余后端/传递依赖。
- 只读源克隆；所有删除和编辑都在 `--dest` 副本内。
- 复制前检查源 HEAD 与清单 commit 一致、源工作树干净、目标不存在、剩余空间足够。
- 退出前验证：所有 `workspace:` 依赖都有对应包（0 悬空）、徽章和 20 个待确认包存在、
  删除路径不存在、`apps/cli` + `apps/desktop-host` + headless/base bundle 存在。
