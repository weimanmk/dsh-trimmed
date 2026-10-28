# dsh 精简运行时（AEH 已批准 P1 + 前端删除）

状态：**已执行并完成隔离验证**。源克隆保持只读；所有删除只发生在构建副本。
本次实际构建副本最初在 **`/tmp/dsh-trimmed`**（173 MB，含 `.git`）；Muse 随后用
rsync（排除 `.git`）把它复制到了 durable 的 **`~/workspace/dsh-trimmed`**（129 MB），
并核实了 desktop-host 在、前端与 P1 包已删。`tools/trim-dsh/trim.py --dest ...`
可从源克隆重新复现。

## 1. 基线与范围

| 项 | 值 |
|---|---|
| 上游 | `deepseek-ai/deepseek-harness` |
| 版本 | `0.2.1-rc.3` |
| commit | `22ddee3792402c3e70ec5f86a63c3e3e895a2f60` |
| 源克隆 | `/home/hatch/workspace/deepseek-harness`（只读，工作树干净） |
| 构建副本 | `/tmp/dsh-trimmed`（从源 `cp -a`，217 MB → 173 MB） |
| workspace manifest | 368 → 280（删除 88 个包/应用路径，其中 3 个是前端 app） |

批准边界逐条落实：

1. **只删 1 个 P1 包**：`@deepseek-ai/dsh-agent-tool-presentation`（自声明 Deprecated）。
   `@deepseek-ai/dsh-client-ui-deepseek-model-label-1017` 徽章包保留，未删。
2. **20 个待确认项保留、保持禁用、不删**：shell / fs / jobs / skill / todo / goal /
   web / workflow / subagent / working-directory / user-questions / hmr /
   plugin-manager / agent-instructions / authorization / credentials-local /
   deepseek-account-platform。清单见 `trim-manifest.json` 的
   `keep.pending_disabled_20`。
3. **前端删除**：`apps/web`、`apps/desktop`、`apps/plugin-market-generator`、
   `packages/bundle/web-app`，以及 `packages/client/*`（保留 `connection` 和 1017
   徽章两个例外）、`packages/extensions/ui-cordis`、7 个
   `packages/experimental/client-ui-*`、6 个 Web 宿主配套包、3 个纯前端 bundle。
   按清单 §7 的依赖顺序确定删除集；删除后统一清理 app/bundle/CLI 等 surviving
   `package.json` 中指向已删包的依赖边。
4. **其余保留/传递依赖不删**：后端、API、host、session、tool、bundle/headless、
   CLI、desktop-host 及其直接依赖全部保留；没有删除 20 个待确认包或任何非前端包。

## 2. 删除清单（88 个路径）

| 组 | 数量 | 内容 |
|---|---:|---|
| `p1-deprecated` | 1 | `packages/core/agent-tool-presentation` |
| `frontend-apps` | 3 | `apps/web`、`apps/desktop`、`apps/plugin-market-generator` |
| `web-bundle` | 1 | `packages/bundle/web-app` |
| `client-web-ui` | 74 | 66 个 `packages/client/*`（除 connection/1017）+ `extensions/ui-cordis` + 7 个 experimental client UI |
| `web-host-support` | 6 | `host/frontend-static`、4 个 directory-picker、`host/open-in-app` |
| `frontend-feature-bundles` | 3 | cot-translation / plugin-market / voice-input 三个纯前端 bundle |

机器可读清单：`tools/trim-dsh/trim-manifest.json`。逐路径删除记录、清理的依赖边和
根脚本/tsconfig 行见 `tools/trim-dsh/trim-report.json`。

## 3. 第二阶段：让精简副本能构建（repair-build.py）

只删包不够：被删包的消费者（源码 import、tsconfig 引用、pnpm patch、bundle
preset）会让构建失败。`tools/trim-dsh/repair-build.py --copy <构建副本>` 在
构建副本上做第二阶段修复（幂等，重跑不改东西），全部是 2026-10-27 实际构建
时逐项发现并验证过的修复：

1. 删 6 个被删前端包留下的无用 pnpm patch（electron osx-sign、fortune-sheet、
   app-builder-lib、exceljs、lexical），否则 pnpm 报 `ERR_PNPM_UNUSED_PATCH`。
2. 删 `workspace-controller` 里 dangling 的 directory-picker 缝（文件、测试、
   类型重导出、失败词汇、Loader 注册、tsconfig 条目），缝的定义包已删，消费
   侧必须一起走（缝必须完整，不能只剩一半）。
3. 20 个 tsconfig 文件里 dangling 的引用/文件条目按行剔除，不动其他内容。
4. 恢复 `client/file-upload`（无 UI 的传输/协议缝，489 行，被保留的 host 代码
   依赖它）+ session-controller 的 peer/dev 边 + tsconfig 引用 +
   `tsconfig.base.json` 的 paths 映射。
5. 删仅供 Web/开发用的 `harness-dev-context`、`webworker-runtime`、
   `webworker-packer` 及其 aggregate 引用。
6. `packages/client/tsdown.client.ts` 里被删的三个模块用 verbatim 内联值代替
   （asset 常量/纯函数、platform 列表、manifest helper），并标注 TRIM-BUILD
   STUB；内联值与 `packages/client/modules/src/assets.ts`、
   `packages/client/web/src/platform.ts` 逐字一致（已 diff 核对），所以 host face
   的配置加载与打包不受影响。真要做 client bundle 会 **loud 失败**（2026-10-28
   在隔离副本实测，见 §5(f) 与 `tools/trim-dsh/evidence/client-stub-<时间戳>/`），
   不会静默产出一份缺组件的客户端包。等桌面前端重做时恢复被删包。
7. `typert/registry` 与 `api/gateway` 的 tsdown 配置加 `hostPhase: true`
  （见 §5(e)）。
8. 根 `tsconfig.host.json` 的 `exclude` 里加死面文件（只测已删 web/
   desktop/client 面的脚本、web profile e2e、浏览器 benchmark、一个
   gateway spec 及其互相 import 的 spec）：文件留磁盘（以后桌面重做可能
   要用），只排除出 host typecheck；仍被 kept 代码 import 的文件会被
   tsc 拉回并 loud 报错，所以排除藏不住活依赖。排除用显式文件条目
   （`scripts/verify-*.ts` 这类宽 glob 会误伤活着的 verifier）加一个
   web tests 子树 glob。
9. 根 `package.json`：`build:lib:host` 末尾 drop 已删 `dsh-desktop` 的
   bundle 步骤（pnpm filter 找不到项目会失败），并删 4 个调已删脚本的
   script 条目（verify-package-dependencies、verify-client-packages、
   verify-product-use、constraints）。
10. 编码：脚本内所有文件读写一律显式 `encoding="utf-8"`。Windows 上
    `Path.read_text()` 默认走 cp1252，上游多个 `package.json` 含
    UTF-8 非 ASCII 字节，CI run #2 在 Repair 步骤 0 秒崩溃
    （`UnicodeDecodeError`，新加的 package 名扫描循环处）；Linux 默认
    UTF-8 所以本地一直没暴露。

> 2026-10-28 步骤 4 补 fix：步骤 4 恢复 tsconfig.host.json 引用的锚点只匹配
> 单行格式（path 行本身以 `},` 结尾），而源文件里该引用是多行格式，锚点
> 永远匹配不上，引用静默丢失（报告还无条件写 `restored: True`），本地
> trim-build 能构建是因为它的该文件在分阶段手工构建时已带上引用。Windows
> CI 首次运行（run #1，`build:lib:host`，TS6059/TS6307）抓住了这个问题。
> 已改为：按引用对象块扫描插入（单行/多行格式都处理）+ host 与 client 两个
> face 都恢复 + 写后校验、三项缺一就 loud 失败。修复后在全新 re-trim 副本
> 上重跑 repair 验证通过（引用落位、JSON 合法、幂等），再跑本地
> `build:lib:host` 复现 CI 构建。

构建命令（沙箱里 pnpm 写 lockfile 会报 EPERM chown，但包已链接完成，不影响
构建；用 `tsx` 直接跑构建脚本可绕过 pnpm 的 pre-run 安装检查）：

```
pnpm install --ignore-scripts   # EPERM 写 lockfile 可忽略，链接已完成
./node_modules/.bin/tsx scripts/compile-referenced-projects.ts host-libraries
```

2026-10-27 在 `~/workspace/trim-build/` 实测：`build:lib:host` exit 0，
`apps/cli/lib/bin.js` 在隔离 `DSH_HOME` 下 `--help` 正常。

**缺口补全（2026-10-28）**：此前 `tools/trim-dsh/evidence/` 里那份
`loader-evidence.txt` 和 Step 18 式会话用的是 npm 发布的完整版 dsh，不是精简
副本自身 `node_modules`，不能作为精简副本的证据。现已补做：

- loader 挂载：`tools/trim-dsh/run_loader_trim_build.py` 把未改动的
  `dsh-plugin/scripts/loader-evidence.mjs` 复制到隔离 staging，通过符号链接把
  bare import 解析到 `/home/hatch/workspace/trim-build/` 自身的包，重跑证明
  **6/6 `aeh_*` 工具挂载**；证据见
  `tools/trim-dsh/evidence/loader-trim-build-<时间戳>/`（`package-resolution.txt`
  证明所有解析 realpath 都在 trim-build 内，未落到 `dsh-plugin/node_modules`
  或 `~/.dsh`）。
- 同一份未改动脚本在精简构建上挂载后停在 `TOOL_EXECUTOR_UNAVAILABLE`：workspace
  版 `dsh-tools`（commit `22ddee37`）要求显式注册 tool executor 且
  `ctx.tools.execute` 是 batch 形态，而 npm 发布的 `0.2.1-rc.3` 有隐式
  executor、单调用 API。该差异已如实记录，详见 §5(a)。
- Step 18 会话：`tools/trim-dsh/evidence/step18-trim-verify-<时间戳>/`（实测的是
  从 `~/workspace/dsh-trimmed` 构建产物做的独立 npm 安装，见
  `step18-trim-verify-20261027T152858Z/summary.json` 的 `dsh_entry`）。

## 3. 保留的关键包

| 类别 | 保留 |
|---|---|
| 入口 | `apps/cli`（`@deepseek-ai/dsh`）、`apps/desktop-host` |
| 运行时 | `packages/bundle/headless`、`packages/bundle/base`、`sdk`、`acp`、`sdk-minimal` |
| 传输 | `packages/client/connection`（desktop-host 与 API 需要，例外保留） |
| 徽章 | `packages/client/ui-deepseek-model-label-1017`（按要求保留；见 §7 限制） |
| 待确认 | 20 个包全部保留，未启用 |
| 其他 | 全部后端/API/host/session/tool/bundle 包与传递依赖 |

## 4. 复现

```bash
cd /home/hatch/workspace/AEH

# 请求路径（在有写权限的会话中）
python3 tools/trim-dsh/trim.py \
  --source /home/hatch/workspace/deepseek-harness \
  --dest /home/hatch/workspace/dsh-trimmed \
  --json-report tools/trim-dsh/trim-report.json

# 本会话实际可写路径
python3 tools/trim-dsh/trim.py --dest /tmp/dsh-trimmed \
  --json-report tools/trim-dsh/trim-report.json
```

脚本行为：校验源 HEAD/干净度 → 检查目标不存在与空间 → `cp -a` → 按 manifest 删除 →
清理所有 surviving `package.json` 中指向已删包的 workspace 边 → 清理
`official-bundles`、CLI help、根 `package.json` 脚本、`tsconfig.base.json` /
`tsconfig.host.json` / `tsconfig.json` 中失效的路径与项目引用 → 验证 0 悬空依赖、
徽章/20 个待确认包/CLI/desktop-host/headless 均存在 → 写 `TRIM-REPORT.json`。

## 5. 验证结果

### a) 独立 Cordis loader 实例

所有 loader 证据都在独立进程、独立临时目录里运行，没有使用正在运行的 dsh 会话，
也没有设置 `DSH_HOME`。分两组：

**(i) npm 发布版 dsh（历史证据，只能代表发布包，不代表精简构建）**

- 用 `dsh-plugin/node_modules` 运行 `dsh-plugin/scripts/loader-evidence.mjs`：
  6 个工具挂载、授权门禁 allow/deny、报告数据最小化、非法参数 `INVALID_ARGS`、
  注入 `AEH_INJECTION_REJECTED`、取消 `ABORTED_BEFORE_DISPATCH`、超时
  `TOOL_TIMEOUT`、卸载后工具数 0，全部通过。
- 证据：`tools/trim-dsh/evidence/loader-evidence.txt`（*不是* 精简副本证据）。

**(ii) 精简构建 `~/workspace/trim-build/` 自身的 `node_modules`（2026-10-28 补做）**

运行器：`tools/trim-dsh/run_loader_trim_build.py`；证据目录：
`tools/trim-dsh/evidence/loader-trim-build-<时间戳>/`。

- 未改动的 `loader-evidence.mjs`：**6/6 工具挂载**（`mounted tools` 与
  `assert.deepEqual` 期望完全一致），随后在首次工具执行处退出 1：
  `TOOL_EXECUTOR_UNAVAILABLE`。
- workspace-API 变体 `tools/trim-dsh/loader-evidence-exec.mjs`：保留原脚本全部
  断言，额外加载 workspace 的 `@deepseek-ai/dsh-tool-executor-native`，并用官方
  `@deepseek-ai/dsh-tool-testkit` 的单调用 helper 走 batch API；exit 0，挂载、
  schema 校验、取消、超时、卸载全部通过。
- 隔离证明：`package-resolution.txt` 列出每个 bare import 的 realpath，全部落在
  `/home/hatch/workspace/trim-build/` 内，未落到 `dsh-plugin/node_modules` 或
  `~/.dsh`；`trim-build-fingerprint.json` 显示运行前后文件数/字节数/包入口
  SHA-256 完全一致，trim-build 未被写入。
- 已知差异（如实记录，不假装修复）：workspace commit `22ddee37` 的
  `dsh-tools` 要求显式注册 tool executor，`ctx.tools.execute` 输入是
  `{ calls, signal }` 的 batch；npm 发布的 `0.2.1-rc.3` 有隐式 executor、单调用
  API。因此原脚本能证明挂载，但不能在精简构建上跑完后半段契约断言；要让它
  直接跑通，需要把 `dsh-plugin/scripts/loader-evidence.mjs` 升级到 workspace
  API（或固定发布版 dsh）。当前插件源码与测试仍按发布版 API 编写，属于
  **未在本轮改动**的项。

### b) TypeScript / Node / Python

| 检查 | 结果 | 证据 |
|---|---|---|
| `npm run typecheck` | exit 0 | `evidence/typecheck.log` |
| `node --test tests/*.test.ts` | 463 pass / 0 fail | `evidence/node-tests.log` |
| `python3 -m unittest discover -s tests` | 641 tests OK | `evidence/python-tests.log` |

Step 19（2026-10-28）在 AEH 仓库内原样复核：Python `641 tests OK`、
`tsc --noEmit` exit 0、`node --test` 463 pass / 0 fail、前端
`npm run build` exit 0（产物 `frontend/dist/index.html` 等）；证据见
`tools/trim-dsh/evidence/step19-verify-<时间戳>/`。

### c) Step 18 合成会话（隔离 runner）

复用 `step18/run-e2e.py`，只把 `DSH_HOME` / profile / work / evidence / runtime
重绑到 `.trim-verify/`（见 `tools/trim-dsh/verify_step18.py`），运行
`deepseek-v4-1-flash` + Sidrune 的合成会话。未使用 `~/.dsh`，未使用运行中的 dsh，
未使用真实学生数据。

- exit code **0**；32 个 JSON events；6 次工具调用 / 6 个结果；0 error。
- 门禁：`item.fraction.add.001` allowed=true；
  `item.fraction.multiply.001` allowed=false（`kcs_not_allowed`）。
- 诊断：`hyp.adds_ok` spawn，snapshot `hyp_1`；probe 选中
  `item.fraction.equiv.001`。
- 复习：`nextIntervalDays=3.2`、stability `3.2`、difficulty `4.8`。
- 报告：attempts `4`、independent correct `3`、hints `1`、minutes `10`、
  independent accuracy `0.75`；1 个授权聚合事件，0 排除。
- 证据：`evidence/step18-trim-verify-20261027T132324Z/summary.md`、
  `dump-config.txt`、`metadata.json`、`stdout.jsonl`、`stderr.log`（空）。

说明：本次 32 events 比基线 39 少，原因是模型生成的文本事件更少；6 个工具调用、
门禁/诊断/复习/报告的关键字段和最终回答均完整，0 error。

### d) 受保护路径前后快照

`tools/trim-dsh/snapshot.py` 对每个文件记录 path/size/mtime/SHA-256，并计算根摘要。
快照：`snapshots/before.json`、`snapshots/after.json`；逐根差异：
`evidence/snapshot-compare.json`。

| 根 | before | after | 结论 |
|---|---|---|---|
| 源克隆 | `24dd0f3a…` | `24dd0f3a…` | **完全一致**（19203 files / 13 symlinks） |
| npx dsh | `119f92e0…` | `119f92e0…` | **完全一致**（63053 files / 12 symlinks） |
| step18/runtime | `d7407a1d…` | `d7407a1d…` | **完全一致**（63072 files / 12 symlinks） |
| `~/.dsh` | `0aa89cd3…`（92 files） | `b9e55eb5…`（95 files） | 见下 |

`~/.dsh` 的差异只有：

- 新增 3 个文件：当前工作区会话
  `sessions/--home-hatch-workspace-AEH--/e7e76526-.../session.lock`、
  `session.v4.jsonl.zstd`，以及对应的 `storages/session_projcache` 条目；
- 修改 2 个文件：同一 `--home-hatch-workspace-AEH--` 下的当前会话
  `session-5015bbac-...` 的 session 日志与 projcache 条目。

这些是**正在运行的 harness 为本次对话自身写入的会话状态**，不是精简脚本写的；
`~/.dsh` 的配置、凭据、非当前会话存储没有变化。本任务对 `~/.dsh` 只有只读快照，
所有 dsh 验证命令都显式使用 `.trim-verify/home` 作为 `DSH_HOME`。

`step18/runtime` 的只读验证：为节省空间，用 `cp -al` 在 `.trim-verify/runtime`
建硬链接副本，只删除副本内的前端包并运行；原 runtime 的内容、大小、mtime
不变（根摘要完全一致）。硬链接复制会改变 inode ctime，但 ctime 不在内容摘要中，
也不改变任何文件内容。

### e) 启动警告：3 个 profile 条目未激活（2026-10-28 调查）

精简副本启动时报 `dsh: warning: 3 entries did not activate`：

| 条目 | 包 | 现象 |
|---|---|---|
| `typert` | `@deepseek-ai/dsh-typert-registry` | `lib/index.js` 缺失（`ERR_MODULE_NOT_FOUND`） |
| `typert-loader` | `@deepseek-ai/dsh-typert-loader` | pending，等待 `typert` 服务 |
| `typert-gateway` | `@deepseek-ai/dsh-api-gateway` | `lib/index.js` 缺失（`ERR_MODULE_NOT_FOUND`） |

**原因（已核实）**：这两个包用 `packages/client/tsdown.client.ts` 的
`clientBundle(...)` 且没有 `hostPhase: true`。该 preset 对 host face 返回
`SKIP_WORKSPACE_BUILD`（`tsdown.config.ts` 注释也写明“package-level config
replaces the root workspace layout”），所以 host-only 构建只由 `tsc` 产出
`lib/types/*.js`，不会产出 `lib/index.js`。完整构建（`build:lib:all`）靠 client
pass 顺带构建它们的 node half，host-only 构建不跑 client pass，因此缺失。
`lib/types/index.js` 是存在的（`packages/typert/registry/lib/types/index.js`、
`packages/api/gateway/lib/types/index.js`），只是没被 bundle 成 `lib/index.js`。

**尝试的修复（已实现到 `repair-build.py` 步骤 7）**：给这两个
`tsdown.config.ts` 的 `clientBundle(...)` 加 `hostPhase: true`，让 host pass
也产出它们的 node half；不恢复任何前端包。

**验证方法与结果（在隔离副本上，未改 trim-build）**：用 `cp -al` 把
`~/workspace/trim-build` 硬链接复制到 `.scratch/trim-fix-copy`，只对副本里两个
配置文件做“先删后写”（断开硬链接），然后：

- 不加 `hostPhase`、`--env.DSH_BUILD_FACE host` 跑
  `node_modules/.bin/tsdown`：两个包都**不产出** `lib/index.js`（复现缺口）；
- 加 `hostPhase: true`、同样 host face 重跑：`api/gateway` 产出 75065 B、
  `typert/registry` 产出 24449 B 的 `lib/index.js`，且不产出 client 资产；
- 直接从两棵树 import 该文件：
  `trim-build/.../lib/index.js` → `ERR_MODULE_NOT_FOUND`，
  副本（已修复）→ `OK`，导出 `TypertRegistry/TypertGatewayService` 等。

**影响与边界（如实记录）**：

- 该警告对 headless 会话**无功能影响**：Step 18 合成会话在带警告的情况下
  exit 0、6 次工具调用全部完成；警告只是 typert/api-gateway 这两个未用到的
  服务条目未激活。

**消除（2026-10-28，第 3 轮，已在 `~/workspace/trim-build/` 上完成）**：
同一 `hostPhase` 补丁已直接打到 trim-build 的两个 `tsdown.config.ts`，并用
`node_modules/.bin/tsdown --env.DSH_BUILD_FACE host` 在两个包内重跑 host face
（`gateway_rc=0`、`registry_rc=0`），产出的 `lib/index.js` 与隔离副本验证的
字节数/sha256 完全一致（75065 B `c4a5664d…`、24449 B `03371d23…`）。
`--help` 冒烟 exit 0 且 `did not activate`/WARN 计数为 0；随后用真实 Sidrune
模型（`deepseek-v4-1-flash`）重跑 Step 18 式 6 工具会话，exit 0、6 次调用各一
次按序完成、0 错误、stderr 中 `did not activate` 为 0。证据：
`tools/trim-dsh/evidence/warnings-fix-verify-20261028T015500Z/` 与
`tools/trim-dsh/evidence/real-model-trim-verify-20261028T015022Z/`。
此后 trim-build 的文件指纹与第 1 轮记录的指纹不再相同（仅上述两个配置文件
与两个新产出的 `lib/index.js` 有变化）；`~/workspace/dsh-trimmed/` 原始副本
未动，`repair-build.py` 步骤 7 已包含同一修复，CI 复现路径不受影响。

### f) client bundle stub 的 fail-loud 验证（2026-10-28）

`repair-build.py` 步骤 6 注释声称“真做 client 资产打包会 loud 失败”。本轮在
隔离副本（`.scratch/trim-client-test`，`cp -a` 全量复制，未写 trim-build）和
合成探针上验证，证据目录
`tools/trim-dsh/evidence/client-stub-<时间戳>/`。

核实到的三点：

1. **内联 stub 本身是逐字忠实的**。`packageAssetMediaType` /
   `packageAssetRevision` / `packageAssetRevisionedPath` /
   `packageAssetReference`、`PACKAGE_ASSET_*` 常量、`PLATFORM_MODULES`、
   `PRELOADED_CLIENT_EXTERNALS` 与源克隆的
   `packages/client/modules/src/assets.ts`、`packages/client/web/src/platform.ts`
   一致。所以“loud 失败”不是 stub 抛的，而是被删包/缺失编译产物造成的——原注释
   把失败归因给 `packageAssets()` 并不准确，已在本节更正。
2. **真实 client face 构建确实 loud 失败，且不产出客户端包**。在副本里跑
   root `tsdown --config-loader native --env.DSH_BUILD_FACE client`：exit 1，
   `ERROR ... UNRESOLVED_ENTRY Cannot resolve entry module lib/types/index.js`
   （host-only 精简构建没有编译 client face 的 `lib/types/client/*`；且
   `packages/client/modules`、`packages/client/web`、`packages/client/runtime`
   这三个前端包已被删除）。事后搜索副本，`client.browser.js` 数量为 0。
   逐包跑 `cordis-client-runner` / `client/connection` / `client/file-upload` /
   `client/ui-deepseek-model-label-1017` 也都是 exit 1。
3. **`packageAssets()` 的 fail-loud 通路确实存在**。用合成包
   `.scratch/asset-probe`（`package.json` 未声明 asset export，client entry 引入
   `src/client/assets/foo.svg`）加载 trim-build 的 `tsdown.client.ts` preset，
   client face exit 1，报
   `[plugin dsh-package-asset] Error: tsdown: @synthetic/asset-probe: .../foo.svg
   needs package.json exports {"./assets/*":"./lib/assets/*"} and "lib/assets" in
   files`，栈顶为 `tsdown.client.ts` 的 `reference`。这印证了注释所说的失败通路，
   但它是上游 guard，不是 stub 新增的。

结论：**“尝试真实 client 打包会 loud 失败、不会静默成功”成立**；但触发失败的
直接原因是缺 client 编译产物与已删前端包，而不是 stub 自身报错。桌面前端重做前
host-only 构建不受影响。

## 6. desktop-host：保留但当前无法工作（如实报告）

`apps/desktop-host` 目录和它的直接依赖（`dsh`、`dsh-app-boot`、
`dsh-client-connection`、`dsh-host-webserver`、`dsh-home-paths`、`dsh-workspace`、
`dsh-skill-office`、`koffi` 等）都保留，包图没有悬空；本次没有单独构建它。
删掉前端后它**不能按原 Desktop 链路启动**，缺口是确定的：

```
apps/desktop（Electron shell，已删）
  → apps/desktop-host（保留）
  → desktop profile（由 Electron 用 PROFILE_TEMPLATES.web 初始化）
  → @deepseek-ai/dsh-web-app（已删）
  → @deepseek-ai/dsh-client-connection + @deepseek-ai/dsh-host-webserver（保留传输）
  → 已删的 packages/client/ui-* / client modules / host-frontend-static
```

具体断点：

1. `apps/desktop` 删除后，没有 Electron 进程创建/管理 `desktop` profile，也没有
   代码再调用 `DesktopProjectManager`。
2. `apps/desktop/src/project-manager.ts` 原本以 `PROFILE_TEMPLATES.web` 初始化
   profile；精简后 `PROFILE_TEMPLATES` 只剩 `acp/headless/sdk/sdk-minimal`，
   `web` 为 `undefined`（`evidence/bundle-check.txt`）。
3. `dsh-web-app` 已删并加入 `RETIRED_BUNDLES`；desktop-host 传给 profile 的
   `--no-open --host 127.0.0.1 --port 0` 正是 web-app 的启动参数，headless 不接受。
4. web-app 依赖的 client UI/modules、`host-frontend-static` 全部删除；即使强行保留
   传输层，也没有可服务的浏览器入口、UI 资源和 `ctx.webServer`/`ctx.connection`
   的完整组合。

因此本次**没有**绕过这个缺口，也没有把 desktop-host 说成可运行。要恢复桌面版，
需要按“以后重做桌面前端”的方向重新实现 web-app/web 前端，或把 desktop-host 改成
headless/自定义 profile 的启动器；这不是本次删除能自动修复的。

## 7. 参考清理与已知限制

- 25 个 surviving `package.json` 的悬空 workspace 边已删除；脚本验证
  `dangling_workspace_dependencies=0`。
- 根 `package.json` 删除 33 个 web/desktop 脚本；`tsconfig.base.json` /
  `tsconfig.host.json` 删除 373 行失效路径/项目引用，`tsconfig.client.json`
  聚合文件删除，`tsconfig.json` 只保留 host 聚合。`build:lib` 只构建 host。
- **保留的 1017 徽章包**目录和源码仍在，但它的 `dsh.client.inject` 与
  `src/client/*` 仍引用已删的 `dsh-client-locale`、`dsh-client-ui-model-selection`、
  `dsh-client-ui-renderer` 等前端包；5 条 devDependencies 已清理，但源码/inject
  仍不可解析，因此它作为独立包不再可构建。这是“按指示保留徽章、同时删除前端”的
  直接结果，已在 `TRIM-REPORT.json` 记录。若以后重做前端，需要恢复这些依赖与 inject。
- 保留的 host/session/API 包中仍有指向已删 client 子路径的源码/测试（例如
  `api/remotes`、`session-log-export`、`message-quotes`、`test-support/client-runtime`）。
  它们的 package.json 边已清理，headless 路径不加载这些 client 子路径；本次没有
  删除这些非前端包，以遵守“其余保留/传递依赖不删”。因此精简树是
  **headless/desktop-host 运行时包集**，不是完整的前端 monorepo 构建。
- `pnpm-lock.yaml` 未重写：当前环境没有 pnpm，且没有做联网安装。用 pnpm 安装时
  需要重新生成 lockfile；`--frozen-lockfile` 不适用于删除包后的树。Step 18 验证
  使用的是已存在的隔离 npm runtime 的裁剪副本，不是新做的 npm install。

## 8. AEH 内集成文件

| 文件 | 作用 |
|---|---|
| `tools/trim-dsh/trim.py` | 可复现精简脚本 |
| `tools/trim-dsh/trim-manifest.json` | 删除/保留/例外清单 |
| `tools/trim-dsh/README.md` | 使用说明与沙箱路径说明 |
| `tools/trim-dsh/trim-report.json` | 本次运行报告（删除路径、清理边、验证） |
| `tools/trim-dsh/snapshot.py` | 受保护路径快照工具 |
| `tools/trim-dsh/snapshots/` | before/after 快照 |
| `tools/trim-dsh/verify_step18.py` | 裁剪 runtime 的 Step 18 隔离 runner 入口 |
| `tools/trim-dsh/evidence/` | loader、Step 18、测试、快照对比证据 |
| `docs/trimmed-runtime.md` | 本文 |

## 9. 未做与边界

- 没有修改 `~/.dsh` 配置/凭据/非当前会话存储；没有加载 AEH 插件到正在运行的
  harness 会话；没有使用正在运行的 dsh 执行任何验证。
- 没有修改 `~/workspace/deepseek-harness`、npx dsh、`step18/runtime`、
  `references/`、`spec/`。
- 没有 push 到 GitHub，没有发送邮件，没有使用真实学生数据或密钥。
- `/home/hatch/workspace/dsh-trimmed` 因沙箱权限未能创建；实际副本是
  `/tmp/dsh-trimmed`。`trim.py` 已支持请求路径，换有写权限的会话即可复现。

## 10. 单独仓库上传方案（待 Daniel 醒后确认，不直接推 129 MB 副本）

- **不推副本的原因**：`~/workspace/dsh-trimmed/` 共 14,429 个文件、129 MB，
  含 14 个符号链接，超出 GitHub snapshot push 单次 2,000 文件 / 16 MiB 的
  上限，且构建产物（`node_modules`、`lib/`、native addon）不应进仓库。
- **仓库内容**：只放 `tools/trim-dsh/`（`trim.py`、`trim-manifest.json`、
  `repair-build.py`、`verify_step18.py`、快照与证据）、`docs/trimmed-runtime.md`
  与 `docs/dsh-function-inventory.md`、以及一个 Windows 打包 workflow。
  仓库名待定（创建曾返回 403，可能需走 GitHub web 流程）。
- **CI 复现流程**：Windows runner 上 clone 公共源仓库
  `https://github.com/deepseek-ai/deepseek-harness` 并固定到本次验证的提交
  `22ddee3792402c3e70ec5f86a63c3e3e895a2f60`，运行 `trim.py` 生成精简副本，
  再运行 `repair-build.py`、pnpm install 与 `build:lib:host`，`--help` 冒烟通过
  后再打包。源仓库 clone 与本次本地 `git status` 干净的源 clone 一致，未改动。
- **待定项**：仓库名；exe 打包方式（单文件 Node  bundle 还是安装包，写 workflow
  前由 Daniel 定）；workflow 文件本身因 API 403 需走 GitHub web 创建。
