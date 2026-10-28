# dsh 功能清单与 AEH 依赖分类（只读调研）

> 调研对象：`~/workspace/deepseek-harness`（原版 dsh 单体仓库克隆，**只读**）与
> `step18/runtime`（AEH 本地隔离安装的 `@deepseek-ai/dsh@0.2.1-rc.3`）。
> 目的：为“AEH 只保留插件真正需要的 dsh 能力”提供一份可逐项核对的清单。
> **本文不删除、不修改、不集成任何东西；所有删除建议都只是建议。**
> 证据基准：仓库文件（2026-10-27）与 Step 18 证据目录 `step18/evidence/20261027T110556Z/`。

## Daniel 的保留原则（本次修订的总规则）

> 以下由 Daniel 的反馈整理，是本次分类、统计与删除建议的最高准则；与后文任何冲突时以本节为准。

1. **面向未来桌面版**：AEH 计划做桌面版软件。因此 `apps/desktop`、`apps/desktop-host` 以及与桌面端直接相关的 `client`/Web UI 包，从“无用”改为**保留**；`apps/web` 按“桌面版前端可能复用”处理（**保留**）。理由：桌面版会复用 Web/Electron 前端、宿主与 Remote API，现在删掉等于未来重造。
2. **上下文压缩必须保留**：长会话的上下文压缩在桌面版与真实会话里都会用到。`compaction` 组全部 5 个包（`dsh-command-compact`、`dsh-compaction`、`dsh-compaction-basic`、`dsh-compaction-image-offload`、`dsh-compaction-tool-result-pruner`）改为**保留**。
3. **保守删除**：只要觉得有用、或者未来可能有用的，一律**保留**或**待确认**，绝不删干净；只有“完全无用且未来也不可能用上”的极少数包才列为**可删**。
4. **不碰运行用 dsh**：本清单只做静态调研与文字修订；不在运行中的 dsh、`~/.dsh/`、源码克隆、npx 安装或 `step18/runtime` 上做任何删除或修改。

## 0. 结论摘要

先把数字说清楚。所有数字都能在本文标注的文件/命令里对上，没有估算。

| 指标 | 数字 | 口径 / 证据 |
|---|---:|---|
| `packages/` 下的 workspace 包 | **363** | `pnpm-workspace.yaml` 的 `packages/*/*`；递归 `package.json` 共 372 个，其中 9 个是测试夹具/模板（见 §2.2 注） |
| `packages/` 顶层分组 | **52** | `ls packages/` 的目录数；每个分组下是若干独立包 |
| `apps/` 应用 | **5** | cli、desktop、desktop-host、plugin-market-generator、web |
| 仓库内 workspace 包合计 | **368** | 363 + 5 |
| Step 18 运行时安装的 `@deepseek-ai/*` | **306** | `ls step18/runtime/node_modules/@deepseek-ai`；其中 293 个对应 `packages/`，2 个对应 `apps/`，11 个为仓库外依赖 |
| `@deepseek-ai/dsh` 直接依赖 | **86** | 运行时 `dsh/package.json` 的 `dependencies`；83 个 `@deepseek-ai/*` + 3 个非 scoped |
| 插件直接 import 的 `@deepseek-ai/*` | **5** | `src` 的 import 去重；`e2e` 为 0（只 import 本地文件） |
| 插件 `package.json` 声明的 `@deepseek-ai/*` | **17** | 另有 `zod`，依赖总数 18 |
| Step 18 组合条目 | **99** | `dump-config.txt`：98 个 dsh 条目 + 1 个 AEH 入口 |
| 其中 dsh 条目启用 / 显式 disabled | **76 / 22** | 唯一启用包 75 个；唯一 disabled 包 20 个（`dsh-plugin-manager` 同时有启用与 disabled 条目） |
| 分类结果（368 个 workspace 包） | 必需 **15** / 保留 **222** / 传递 **109** / 待确认 **20** / 无用（可删）**2** | 见 §5.2；另有 2 个外部直接依赖（cordis、schemastery），合计“必需”17 |

**一句话结论**：插件运行时真正 import 的只有 5 个包（其中 cordis、dsh-util-values 还是
type-only，真正的运行时值导入只有 dsh-tools、dsh-llm、schemastery 3 个）；Step 18 能跑起来
另需 11 个启动/会话链路包和 1 个 CLI。其余 353 个 workspace 包里，109 个是依赖/peer 闭包
带进来的，20 个是 Step 18 显式关掉、需要 Daniel 拍板的，**222 个按 Daniel 的保守保留原则
保留**（含桌面端全部前端/宿主、上下文压缩 5 件套与全部实验特性），只有 **2** 个自声明
“临时/弃用”的包列为可删。**保守原则下不再建议删“传递依赖”或产品面的包**：dsh-tools/dsh-llm
仍有 peer/库闭包，真要收缩也应先换 bundle、再按闭包评估（见 §7、§8）。

## 1. 调研边界与只读声明

### 1.1 做了什么

- 只读 `~/workspace/deepseek-harness` 的目录、`package.json`、README、`docs/` 与
  `pnpm-workspace.yaml`；
- 只读 AEH 内的 `dsh-plugin/package.json`、`dsh-plugin/src/**`、`dsh-plugin/e2e/**`、
  `dsh-plugin/tests/**`、`dsh-plugin/scripts/**`；
- 只读 `step18/runtime/node_modules/@deepseek-ai/*/package.json` 与
  `step18/runtime/package-lock.json` 的包名/版本；
- 只读 `step18/evidence/20261027T110556Z/` 的 `dump-config.txt`、`summary.json`、
  `command.txt`、`profile.*`；
- 用 `find`/`ls`/`sha256sum` 做计数与前后快照。

### 1.2 明确没做什么（隔离边界）

- **没有**读写 `~/.dsh/` 的任何配置、profile、sessions、storages；
- **没有**运行 npx 安装的 dsh，也没有运行 `step18/runtime` 里的 dsh；
- **没有**修改 `~/workspace/deepseek-harness` 源码克隆；
- **没有**修改 `references/`、`spec/`（只读）；
- **没有**把 AEH 插件加载进正在执行本任务的 harness 会话；
- **没有**执行 `npm install`、`pnpm install`、`node`、`tsc`、`run-e2e.py`；
- **没有**删除/重命名任何文件、包或依赖声明；本次只修订 `docs/dsh-function-inventory.md` 一个文件；
- **没有**改动运行中的 dsh：不碰 `~/.dsh/`、npx 安装的 dsh、`~/workspace/deepseek-harness`、
  `step18/runtime`，也没有把 AEH 插件加载进正在执行本任务的 harness 会话。

> “运行用 dsh”和“被调研的 dsh”是分开的：运行本任务的 harness 用它自己的 dsh；本文调研的是
> 源码克隆与 `step18/runtime` 的独立安装。两者没有共享 `DSH_HOME`，也没有共享进程。

### 1.3 方法

分类只依据四类静态证据：**插件源码 import**、**插件 package.json 声明**、
**包自身 package.json 的 dependencies/peerDependencies**、**Step 18 的 profile 与
dump-config**。没有做“删掉再跑”的实验。本次按 Daniel 的保守原则重判：任何“有用或未来
可能用”的包归入**保留**，Step 18 显式关掉的归入**待确认**，只有自声明临时/弃用、且无未来
使用路径的包才归入**无用（可删）**。因此“保留/待确认”不是“没证据”，而是“有理由不删”。

## 2. 原版 dsh 单体仓库结构

### 2.1 `apps/`（5 个应用）

| app | 包名 | 说明 | 分类 | 理由 |
|---|---|---|---|---|
| `apps/cli` | `@deepseek-ai/dsh` | dsh CLI：profile 启动、插件管理、配置检查；`bin.dsh=lib/bin.js`。 | **必需（Step18）** | Step 18 隔离运行时安装并由 `dsh --profile aeh-e2e` 启动。 |
| `apps/desktop` | `@deepseek-ai/dsh-desktop` | Electron 桌面壳，内嵌 dsh 运行时与外部插件。 | **保留（未来桌面版）** | Daniel：AEH 未来要做桌面版软件；桌面壳是桌面版入口，删了等于未来重造。 |
| `apps/desktop-host` | `@deepseek-ai/dsh-desktop-host` | Electron 的私有 Node 模式宿主进程。 | **保留（未来桌面版）** | Daniel：桌面宿主进程与 `apps/desktop` 配套，未来桌面版需要。 |
| `apps/plugin-market-generator` | `@deepseek-ai/dsh-plugin-market-generator` | 从 npm 包/Git 仓库列表生成插件市场索引的参考工具。 | **保留（产品面）** | 保守原则：桌面版若带插件市场/发布流程会用到；当前不分发不等于未来不用。 |
| `apps/web` | `@deepseek-ai/dsh-web-frontend` | Web 前端入口：vite 构建 `@deepseek-ai/dsh-client-web`，dist 由 `dsh web` 提供。 | **保留（桌面版前端可复用）** | Daniel：Web 前端与桌面端共用 `client`/`host` 栈，按“桌面版可能复用”保留。 |

### 2.2 `packages/`（52 个分组 / 363 个包）

`packages/<组>/<包>` 是 workspace 的实际布局；一个组是同一子系统的多个独立 npm 包。
下表每行是一个组，最后五列是该组内 363 个包的分类分布（必需/传递/待确认/保留/无用）。

| 组 | 包数 | 这一组是干什么的 | 必需 | 传递 | 待确认 | 保留 | 无用 |
|---|---:|---|---:|---:|---:|---:|---:|
| `acp` | 1 | Agent Client Protocol（JSON-RPC/stdio）自动化接入服务。 | 0 | 0 | 0 | 1 | 0 |
| `api` | 10 | 面向 Web/Desktop 客户端的 Typert Remote API 控制器与网关。 | 0 | 2 | 0 | 8 | 0 |
| `attachment` | 2 | 会话附件的不可变存储 seam 与 DSH_HOME 本地实现。 | 0 | 2 | 0 | 0 | 0 |
| `boot` | 6 | CLI/app 启动、profile 组合、插件管理与配置编辑。 | 0 | 3 | 2 | 1 | 0 |
| `browser-use` | 1 | 浏览器自动化 provider（Playwright / chrome-devtools / Stagehand）。 | 0 | 0 | 0 | 1 | 0 |
| `bundle` | 6 | 可组合的 profile bundle：base、headless、web、sdk、sdk-minimal、acp。 | 2 | 0 | 0 | 4 | 0 |
| `client` | 68 | Web/Desktop 前端：RPC 传输、状态/资源、React UI 组件与渲染器。 | 0 | 0 | 0 | 67 | 1 |
| `compaction` | 5 | 上下文压缩 seam、基础压缩策略、图片卸载与工具结果裁剪。 | 0 | 0 | 0 | 5 | 0 |
| `computer-use` | 1 | 桌面自动化（Computer Use）provider。 | 0 | 0 | 0 | 1 | 0 |
| `context` | 7 | 向模型上下文注入文件引用、会话引用、时间与 tmux 信息。 | 0 | 0 | 1 | 6 | 0 |
| `core` | 10 | Agent/agent-loop、工具注册与执行、会话、system prompt、scope 等核心。 | 6 | 1 | 0 | 2 | 1 |
| `credentials` | 5 | 凭据与授权 seam、本地凭据、DeepSeek 账号与授权流程。 | 0 | 2 | 3 | 0 | 0 |
| `deliverables` | 3 | 交付文件声明、文件引用与工作区变更记录。 | 0 | 1 | 0 | 2 | 0 |
| `document` | 1 | Office 文档转 PDF。 | 0 | 0 | 0 | 1 | 0 |
| `experimental` | 58 | 实验特性合集：agent team、语音、浏览器/桌面自动化、插件市场、Ralph、worktree 等。 | 0 | 0 | 0 | 58 | 0 |
| `extensions` | 4 | Cordis 动态插件的宿主/客户端运行器与运行时检查工具。 | 0 | 0 | 0 | 4 | 0 |
| `feedback` | 2 | 会话与消息反馈（评分、备注）。 | 0 | 2 | 0 | 0 | 0 |
| `fs` | 7 | 文件系统 seam、本地实现、沙箱/观察策略与文件工具。 | 0 | 4 | 2 | 1 | 0 |
| `goal` | 4 | 同会话持久目标：状态服务、slash command 与模型工具。 | 0 | 3 | 1 | 0 | 0 |
| `guard` | 2 | 重复工具调用提醒与工具调用超时策略。 | 0 | 2 | 0 | 0 | 0 |
| `host` | 9 | Web/Desktop 宿主：目录选择、静态前端、webserver、插件清单、产品遥测。 | 0 | 2 | 0 | 7 | 0 |
| `identity` | 1 | 遥测/反馈用的匿名用户 ID。 | 0 | 1 | 0 | 0 | 0 |
| `interaction` | 5 | 命令注册、权限预设、用户提问与审批 seam。 | 0 | 3 | 1 | 1 | 0 |
| `jobs` | 3 | 后台任务注册表、本地实现与任务工具。 | 0 | 2 | 1 | 0 | 0 |
| `llm` | 9 | LLM seam、DeepSeek/pi-ai 适配器、API 扩展、重试与 token 计量。 | 2 | 7 | 0 | 0 | 0 |
| `lsp` | 3 | LSP 语言服务 seam、stdio provider 与 lsp 工具。 | 0 | 0 | 0 | 3 | 0 |
| `mcp` | 2 | MCP 客户端桥接与 MCP 资源读取。 | 0 | 1 | 0 | 1 | 0 |
| `plan` | 1 | 计划模式（plan mode）与会话内计划状态。 | 0 | 1 | 0 | 0 | 0 |
| `preset` | 3 | Agent 能力组合预设、预设注册表与部署 persona。 | 0 | 1 | 0 | 2 | 0 |
| `ptc-runtime` | 2 | 程序化工具调用（PTC）运行时 seam 与 Node 实现。 | 0 | 2 | 0 | 0 | 0 |
| `sandbox` | 4 | 进程沙箱 seam、本地后端、策略解析与 Windows ACL 后端。 | 0 | 4 | 0 | 0 | 0 |
| `schedule` | 2 | 宿主级定时提醒与模型侧 schedule 工具。 | 0 | 0 | 0 | 2 | 0 |
| `sdk` | 3 | SDK 接入：JSON-RPC 协议、服务端与 TypeScript 客户端。 | 0 | 0 | 0 | 3 | 0 |
| `session` | 22 | 会话日志、投影、持久化、标题、查询、遥测、格式迁移与消息引用。 | 3 | 15 | 1 | 3 | 0 |
| `session-query` | 3 | 会话查询服务与 Web 会话日志导出。 | 0 | 2 | 0 | 1 | 0 |
| `settings` | 1 | 用户设置 seam。 | 0 | 1 | 0 | 0 | 0 |
| `shell` | 10 | bash/pwsh 执行器 seam、本地/沙箱实现与持久 shell 工具。 | 0 | 6 | 2 | 2 | 0 |
| `skill` | 5 | Agent 技能注册、文件系统/Office 技能与技能工具。 | 0 | 2 | 1 | 2 | 0 |
| `spill` | 3 | 超长工具输出的溢出存储 seam、本地实现与保留策略。 | 0 | 3 | 0 | 0 | 0 |
| `ssh` | 5 | SSH 远程连接：文件系统、沙箱、子进程/终端 provider。 | 0 | 0 | 0 | 5 | 0 |
| `storage` | 4 | KV 存储 hub、domain 数据形态与 JSON/SQLite 后端。 | 0 | 3 | 0 | 1 | 0 |
| `subagent` | 9 | 子代理 seam 与 fork/spawn/ACP/Claude Code/Codex/SDK 后端。 | 0 | 3 | 2 | 4 | 0 |
| `subprocess` | 3 | 子进程 seam、本地实现与 SSH 实现。 | 0 | 3 | 0 | 0 | 0 |
| `telemetry` | 1 | OpenTelemetry 普通事件与会话日志上报。 | 0 | 1 | 0 | 0 | 0 |
| `terminal` | 2 | 持久 PTY 会话 seam 与 bash PTY 后端。 | 0 | 0 | 0 | 2 | 0 |
| `test-support` | 8 | 测试/基准夹具：mock LLM、replay、testkit、snapshot 等。 | 0 | 0 | 0 | 8 | 0 |
| `todo` | 1 | todo_write 模型工具。 | 0 | 0 | 1 | 0 | 0 |
| `typert` | 4 | Typert 反射/协议、运行时注册表、loader 与生成器。 | 0 | 3 | 0 | 1 | 0 |
| `util` | 21 | 通用基础库：brand、values、crypto、time、deque、atomic-write、chunked-list 等。 | 1 | 14 | 0 | 6 | 0 |
| `web` | 7 | Web 访问 seam、搜索/抓取 provider 与 web 工具。 | 0 | 4 | 1 | 2 | 0 |
| `workflow` | 3 | 工作流引擎 seam、PTC 实现与 workflow 工具。 | 0 | 2 | 1 | 0 | 0 |
| `workspace` | 1 | 工作区实体注册表。 | 0 | 1 | 0 | 0 | 0 |
| **合计** | **363** |  | **14** | **109** | **20** | **218** | **2** |

> 注：`find packages -name package.json` 递归得到 372 个 manifest，其中 9 个不是 workspace 包：
> `packages/preset/agent-preset/skills/cordis-plugin-development/templates/{decoration,mcp}/package.json`
> 两个模板，以及 `packages/typert/generator/tests/fixtures/**` 七个测试夹具。按
> `pnpm-workspace.yaml` 的 `packages/*/*` 口径，workspace 包为 **363**。

### 2.3 `benchmarks/`（9 个目录，48 个文件）

dsh 的性能/回归基准，私有包 `@deepseek-ai/dsh-benchmarks`；不是运行时依赖。

| 目录 | 一句话 |
|---|---|
| `active-stream-reconnect/` | 重连时携带 10 万 delta 推理前缀的 client fold 时间与堆占用基准。 |
| `agent-continuation/` | 后端 continuation（续跑）基准。 |
| `conversation-fold/` | 会话折叠（conversation fold）基准。 |
| `long-session-browser/` | Chromium 中打开 240 轮合成会话并翻页/输入的浏览器基准。 |
| `session-corpus/` | 会话语料与投影列表基准。 |
| `session-open/` | 会话打开延迟基准（含 v0 会话合成）。 |
| `support/` | 基准共用的 worker、校准、机器档位与缩放报告工具。 |
| `terminal-io/` | 终端 I/O 吞吐基准（xterm headless）。 |
| `user-text/` | 用户文本渲染/折叠基准。 |

### 2.4 `python/`（2 个包）

| 目录 | 一句话 |
|---|---|
| `python/sdk/` | Python 高层 turns API + 低层 JSON-RPC 客户端（`deepseek-harness-sdk`）。 |
| `python/sdk-runtime/` | 把 bundled `dsh` CLI 可执行文件与原生 sidecar 打成 Python wheel（`deepseek-harness-runtime-bin`）。 |

### 2.5 `native/`（1 个目录）

| 目录 | 一句话 |
|---|---|
| `native/system/` | `@deepseek-ai/node-addon-system`：Linux Landlock 启动器与 POSIX `flock` 写锁的预编译原生包，含平台二进制子包。 |

### 2.6 `docs/`（867 个文件：69 个根级 + 10 个子目录 798 个）

| 目录/范围 | 一句话 |
|---|---|
| `docs/` 根级 | 架构、子系统、配置目录、CLI、生命周期、持久化、术语表等主文档（中英成对）。 |
| `docs/cookbook/` | 任务型食谱（加包、加插件预览、迁移等）。 |
| `docs/cordis-api/` | Cordis API 参考（Context、事件、服务等）。 |
| `docs/cordis-tutorial/` | 从第一个插件到生命周期的 Cordis 教程。 |
| `docs/defensive-patterns/` | 防御式编码模式（client 组件、错误边界等）。 |
| `docs/i18n/` | 双语文档规范、术语与样式样例。 |
| `docs/persistence-changes/` | 每次会话持久化类型变更的记录与 schema 快照。 |
| `docs/postmortem/` | 事故复盘（ACP 导出、JS 表达式禁用文件工具等）。 |
| `docs/subsystems/` | 各子系统设计文档（agent team 等）。 |
| `docs/upgrade-guide/` | 按版本组织的升级指南。 |
| `docs/user/` | 面向用户的指南与开发文档。 |

## 3. AEH 插件实际依赖

### 3.1 插件直接 import 的 `@deepseek-ai/*`（5 个）

对 `dsh-plugin/src/**` 与 `dsh-plugin/e2e/**` 做 import 去重，只有下面 5 个包；
`e2e/aeh-e2e-entry.ts` 只 import 本地 `../src/*`，没有任何 `@deepseek-ai/*`。

| 包 | import 位置 | 类型 | 在插件里起什么作用 |
|---|---|---|---|
| `@deepseek-ai/cordis` | `src/dsh.ts:31` | **type-only** | 只导出 `Context` 类型：`ctx.effect` 的清理语义、`ctx.tools` 的类型来源；运行时不 import 值。 |
| `@deepseek-ai/dsh-tools` | `src/dsh.ts:19-27`、`:33` | **运行时值 + 类型** | `defineTool` 负责 schema 编译、参数/输出校验、工具注册与执行；`ParameterSchemaSpec`、`ValueSchemaSpec`、`ToolDefinition`、`ToolRunContext` 是作者适配层的类型。 |
| `@deepseek-ai/dsh-llm` | `src/dsh.ts:28,32`、`src/security.ts:30` | **类型 + 运行时值** | `ContentBlock` 是工具结果的内容块类型；`HarnessError` 在安全层做错误映射/拒绝。 |
| `@deepseek-ai/dsh-util-values` | `src/dsh.ts:29` | **type-only** | `JsonValue`，工具输入/输出的 JSON 值类型。 |
| `@deepseek-ai/schemastery` | `src/config.ts:22` | **运行时值** | `Schema` 定义 `Config`，loader 在 `apply` 前校验 profile/retention/allowedModes。 |

**运行时值导入只有 3 个**：`dsh-tools`、`dsh-llm`（`HarnessError`）、`schemastery`。
另外两个是纯类型。这决定了“最小运行时”其实很小。

### 3.2 `package.json` 声明的 18 个依赖（17 个 `@deepseek-ai/*` + `zod`）

`dsh-plugin/package.json:20-36` 声明了 17 个 `@deepseek-ai/*` 与 `zod@4.4.3`。
其中 **12 个在 `src`/`e2e` 里没有任何 import**。逐项证据如下：

| 声明但未 import 的包 | 可核对的依赖关系 | 判断 |
|---|---|---|
| `@deepseek-ai/dsh-agent` | `dsh-tools` 的 **peerDependency**；Step 18 `dump-config` 启用 | 宿主服务；声明可解释为固定 peer 版本，源码未用 → 待确认 |
| `@deepseek-ai/dsh-brand` | `dsh-tools` 的 **dependency**（`dsh-tools/package.json`） | 传递依赖；插件无需直接声明 |
| `@deepseek-ai/dsh-sandbox` | `dsh-tools` 的 **peerDependency**；`dsh-sandbox-local` 等实现它 | 传递/peer；插件未直接调用沙箱 |
| `@deepseek-ai/dsh-scope` | `dsh-tools`、`dsh-agent-loop` 的 **peerDependency** | 传递/peer；插件未直接调用 scope |
| `@deepseek-ai/dsh-session` | `dsh-tools` 的 **peerDependency**；Step 18 启用 | 宿主服务；插件只用结构化的 `session/disposed` 事件（`src/index.ts:121-150`） |
| `@deepseek-ai/dsh-system-prompt` | `dsh-tools` 的 **peerDependency**；`tests/contract.test.ts:22`、`tests/step7.test.ts:23`、`tests/security.test.ts:26`、`scripts/loader-evidence.mjs:19` 使用 | 测试/loader 证据需要；插件 `src` 未用 |
| `@deepseek-ai/dsh-timeout` | `dsh-llm` 的 **dependency** | 传递依赖；插件无需直接声明 |
| `@deepseek-ai/dsh-tool-call-timeout-policy` | `dsh-base` 的 **dependency**；`tests/contract.test.ts:29`、`scripts/loader-evidence.mjs:25` 使用 | 测试/loader 证据需要；插件 `src` 未用 |
| `@deepseek-ai/dsh-typert-protocol` | `dsh-llm` 的 **dependency** | 传递依赖；插件无需直接声明 |
| `@deepseek-ai/dsh-user-approval` | `dsh-tools` 的 **peerDependency**；Step 18 启用 | 宿主服务；AEH 工具当前不触发审批 |
| `@deepseek-ai/dsh-util-crypto` | `dsh-llm` 的 **dependency** | 传递依赖；插件无需直接声明 |
| `@deepseek-ai/cordis-plugin-loader` | `tests/contract.test.ts:28`、`tests/step7.test.ts:26`、`scripts/loader-evidence.mjs:24` 使用；dsh 运行时用它加载 profile | loader 证据/运行时加载需要；插件 `src` 未用 |

**结论**：`package.json` 的声明面（17）明显大于源码 import 面（5）。这 12 个大多可以由
`dsh-tools`/`dsh-llm` 的 peer/dependency 解释，属于“为了锁定宿主版本而显式声明”的冗余，
但只凭只读材料无法证明作者意图，所以归类为“待确认/冗余”，不建议直接删声明（删了可能
改变 peer 解析与宿主版本）。

### 3.3 测试与脚本额外用到的包

`tests/**` 与 `scripts/loader-evidence.mjs` 还 import 了 `dsh-system-prompt`、
`cordis-plugin-loader`、`dsh-tool-call-timeout-policy`。这三个都在上面的 17 个声明里，
没有引入新的包。它们是“验证工具链”的依赖，不是插件运行时依赖。

### 3.4 插件运行所需的 dsh 服务面

- `inject = ['tools']`（`src/index.ts:44`）：只强依赖工具注册表；
- `ctx.effect`（`src/index.ts:103`）：注册/卸载的可逆副作用；
- `ctx.tools.register`（`src/index.ts:109`）：把 6 个工具挂到 dsh-tools；
- `session/disposed`（`src/index.ts:121-150`）：结构化监听，找不到就不挂，不硬依赖 session。

因此插件对 dsh 的“契约面”是 `cordis` + `dsh-tools` + `dsh-llm` + `dsh-util-values` +
`schemastery`；`dsh-agent`/`dsh-session`/`dsh-system-prompt`/`dsh-user-approval` 是宿主为了
把工具跑起来提供的运行环境，不是插件代码直接调用的 API。

## 4. Step 18 隔离运行时

### 4.1 安装事实

`step18/runtime/package.json` 只有一个依赖：`@deepseek-ai/dsh@0.2.1-rc.3`。
`step18/runtime/node_modules/@deepseek-ai/` 下实际有 **306** 个条目：

- 293 个与 `packages/` 的 363 个包同名（其余 70 个没有装进这个运行时）；
- 2 个对应 `apps/`：`dsh`（apps/cli）、`dsh-web-frontend`（apps/web）；
- 11 个是仓库外依赖：`cordis`、`cordis-plugin-group`、`cordis-plugin-include`、
  `cordis-plugin-loader`、`cordis-plugin-timer`、`cosmokit`、`libreoffice-kit`、
  `libreoffice-kit-wasm`、`node-addon-system`、`node-addon-system-linux-x64`、`schemastery`。

> 这 306 个是“安装进来”的，不等于“Step 18 组合并加载”的。后者看 `dump-config.txt`：
> 99 条里 76 条 dsh 条目启用（75 个唯一包），22 条显式 disabled（20 个唯一包）。

### 4.2 `@deepseek-ai/dsh` 直接依赖了哪些包

运行时 `dsh/package.json` 的 `dependencies` 共 **86** 个：83 个 `@deepseek-ai/*` + 3 个
非 scoped（`commander`、`js-yaml`、`node-addon-require-builtin`）。其中 78 个能在
`packages/` 找到，5 个是外部 scoped（cordis、cordis-plugin-include、cordis-plugin-loader、
cordis-plugin-timer、schemastery）。

| 分类 | 个数 | 说明 |
|---|---:|---|
| 必需（直接/Step18） | 5 | 含 `dsh-base`、`dsh-headless`、`dsh-session-projection` 等 |
| 传递依赖 | 23 | 由 `dsh-base` 等带入 |
| 待确认 | 15 | Step18 disabled 的工具/服务 |
| 保留（原“无用”） | 37 | Web/SDK/ACP/实验/可选能力；按保守原则保留 |
| 加载器/外部 | 3 | cordis 三件套 |
| 非 scoped | 3 | commander、js-yaml、node-addon-require-builtin |
| **合计** | **86** | 83 个 `@deepseek-ai/*` + 3 个非 scoped |

<details><summary>86 个直接依赖完整清单（name + 版本范围）</summary>

```text
@deepseek-ai/cordis ~4.0.5
@deepseek-ai/cordis-plugin-include ~1.0.10
@deepseek-ai/cordis-plugin-loader ~1.0.6
@deepseek-ai/cordis-plugin-timer ~1.1.7
@deepseek-ai/dsh-acp-app 0.2.1-rc.3
@deepseek-ai/dsh-agent-instructions 0.2.1-rc.3
@deepseek-ai/dsh-agent-preset 0.2.1-rc.3
@deepseek-ai/dsh-agent-tool-presentation 0.2.1-rc.3
@deepseek-ai/dsh-app-boot 0.2.1-rc.3
@deepseek-ai/dsh-atomic-write 0.2.1-rc.3
@deepseek-ai/dsh-base 0.2.1-rc.3
@deepseek-ai/dsh-client-ui-agent-preset 0.2.1-rc.3
@deepseek-ai/dsh-client-ui-cordis 0.2.1-rc.3
@deepseek-ai/dsh-cmdline 0.2.1-rc.3
@deepseek-ai/dsh-command-compact 0.2.1-rc.3
@deepseek-ai/dsh-command-goal 0.2.1-rc.3
@deepseek-ai/dsh-compaction-basic 0.2.1-rc.3
@deepseek-ai/dsh-compaction-tool-result-pruner 0.2.1-rc.3
@deepseek-ai/dsh-cordis-client-runner 0.2.1-rc.3
@deepseek-ai/dsh-experimental-agent-team-profile 0.2.1-rc.3
@deepseek-ai/dsh-experimental-auto-review 0.2.1-rc.3
@deepseek-ai/dsh-experimental-badge-skill-bundle 0.2.1-rc.3
@deepseek-ai/dsh-experimental-cot-translation-bundle 0.2.1-rc.3
@deepseek-ai/dsh-experimental-inspector-profile 0.2.1-rc.3
@deepseek-ai/dsh-experimental-plugin-market-bundle 0.2.1-rc.3
@deepseek-ai/dsh-experimental-ralph-bundle 0.2.1-rc.3
@deepseek-ai/dsh-experimental-session-search 0.2.1-rc.3
@deepseek-ai/dsh-experimental-session-titles-bundle 0.2.1-rc.3
@deepseek-ai/dsh-experimental-terminal-bundle 0.2.1-rc.3
@deepseek-ai/dsh-experimental-tool-worktree 0.2.1-rc.3
@deepseek-ai/dsh-experimental-voice-input-bundle 0.2.1-rc.3
@deepseek-ai/dsh-fs-local 0.2.1-rc.3
@deepseek-ai/dsh-goal 0.2.1-rc.3
@deepseek-ai/dsh-goal-round-driver 0.2.1-rc.3
@deepseek-ai/dsh-headless 0.2.1-rc.3
@deepseek-ai/dsh-hmr 0.2.1-rc.3
@deepseek-ai/dsh-home-paths 0.2.1-rc.3
@deepseek-ai/dsh-http-proxy 0.2.1-rc.3
@deepseek-ai/dsh-jobs-local 0.2.1-rc.3
@deepseek-ai/dsh-launch-environment 0.2.1-rc.3
@deepseek-ai/dsh-mcp-client 0.2.1-rc.3
@deepseek-ai/dsh-mcp-resources 0.2.1-rc.3
@deepseek-ai/dsh-persona 0.2.1-rc.3
@deepseek-ai/dsh-plan-mode 0.2.1-rc.3
@deepseek-ai/dsh-plugin-manager 0.2.1-rc.3
@deepseek-ai/dsh-pwsh-local 0.2.1-rc.3
@deepseek-ai/dsh-pwsh-sandbox 0.2.1-rc.3
@deepseek-ai/dsh-schedule 0.2.1-rc.3
@deepseek-ai/dsh-sdk-app 0.2.1-rc.3
@deepseek-ai/dsh-sdk-minimal 0.2.1-rc.3
@deepseek-ai/dsh-session-projection 0.2.1-rc.3
@deepseek-ai/dsh-session-reference 0.2.1-rc.3
@deepseek-ai/dsh-skill 0.2.1-rc.3
@deepseek-ai/dsh-skill-filesystem 0.2.1-rc.3
@deepseek-ai/dsh-skill-office 0.2.1-rc.3
@deepseek-ai/dsh-terminal 0.2.1-rc.3
@deepseek-ai/dsh-terminal-bash 0.2.1-rc.3
@deepseek-ai/dsh-time-context 0.2.1-rc.3
@deepseek-ai/dsh-tmux-context 0.2.1-rc.3
@deepseek-ai/dsh-token-meter 0.2.1-rc.3
@deepseek-ai/dsh-tool-ask-user 0.2.1-rc.3
@deepseek-ai/dsh-tool-bash 0.2.1-rc.3
@deepseek-ai/dsh-tool-bash-persistent 0.2.1-rc.3
@deepseek-ai/dsh-tool-cordis 0.2.1-rc.3
@deepseek-ai/dsh-tool-fs 0.2.1-rc.3
@deepseek-ai/dsh-tool-fs-search 0.2.1-rc.3
@deepseek-ai/dsh-tool-goal 0.2.1-rc.3
@deepseek-ai/dsh-tool-jobs 0.2.1-rc.3
@deepseek-ai/dsh-tool-present 0.2.1-rc.3
@deepseek-ai/dsh-tool-pwsh 0.2.1-rc.3
@deepseek-ai/dsh-tool-pwsh-persistent 0.2.1-rc.3
@deepseek-ai/dsh-tool-schedule 0.2.1-rc.3
@deepseek-ai/dsh-tool-skill 0.2.1-rc.3
@deepseek-ai/dsh-tool-str-replace-editor 0.2.1-rc.3
@deepseek-ai/dsh-tool-subagent 0.2.1-rc.3
@deepseek-ai/dsh-tool-subagent-control 0.2.1-rc.3
@deepseek-ai/dsh-tool-todo 0.2.1-rc.3
@deepseek-ai/dsh-tool-web 0.2.1-rc.3
@deepseek-ai/dsh-tool-workflow 0.2.1-rc.3
@deepseek-ai/dsh-tool-workspace-dependencies 0.2.1-rc.3
@deepseek-ai/dsh-web-app 0.2.1-rc.3
@deepseek-ai/dsh-workflow-ptc 0.2.1-rc.3
@deepseek-ai/schemastery ~3.18.5
commander ^15.0.0
js-yaml ^4.3.2
node-addon-require-builtin ^0.1.9
```

</details>


> 版本差异：源码 `apps/cli/package.json` 是 89 个依赖，比发布版多
> `dsh-cua-bundle`、`dsh-official-bundles`、`dsh-personalized-recommendations` 三个；
> 本文的“86”以 **Step 18 实际安装的发布版** 为准。

### 4.3 Step 18 profile 实际组合了什么

`step18/home/profiles/aeh-e2e/package.json` 声明两个 bundle：`@deepseek-ai/dsh-base` +
`@deepseek-ai/dsh-headless`；`cordis.patch.yml` 再把模型路由到 `llm-pi-ai` 的 sidrune
provider，并 `insert` AEH 入口。`dump-config.txt` 的 99 条 = 98 个 dsh 条目 + 1 个
`aeh-education-e2e`。

**22 条显式 disabled（20 个唯一包）**：`tool-plugin-manager`、`hmr`、`user-questions`、
`authorization`、`deepseek-account`、`credentials`、`tool-working-directory`、`tool-bash`、
`tool-pwsh`、`tool-jobs`、`tool-fs`、`tool-fs-search`、`agent-instructions`、`tool-skill`、
`tool-subagent-control`、`tool-subagent`、`tool-workflow`、`tool-todo`、`tool-goal`、`tool-web`。

这 20 个是“Step 18 为了最小验收主动关掉”的，不等于 AEH 生产永远不要。它们进入
**待确认**，需要 Daniel 决定 AEH 是否保留通用 dsh 工具面。

### 4.4 306 个安装项清单

<details><summary>306 个 `@deepseek-ai/*` 安装项完整清单（按字母序）</summary>

```text
cordis
cordis-plugin-group
cordis-plugin-include
cordis-plugin-loader
cordis-plugin-timer
cosmokit
dsh
dsh-acp
dsh-acp-app
dsh-agent
dsh-agent-default-model
dsh-agent-instructions
dsh-agent-loop
dsh-agent-preset
dsh-agent-preset-registry
dsh-agent-tool-presentation
dsh-anonymous-user-id
dsh-api-account-controller
dsh-api-gateway
dsh-api-job-controller
dsh-api-remote-access
dsh-api-remotes
dsh-api-session-controller
dsh-api-settings-controller
dsh-api-terminal-controller
dsh-api-workspace-controller
dsh-api-workspace-files
dsh-app-boot
dsh-atomic-write
dsh-attachment
dsh-attachment-local
dsh-authorization
dsh-base
dsh-bash-local
dsh-bash-sandbox
dsh-brand
dsh-chunked-list
dsh-client-connection
dsh-client-file-upload
dsh-client-hmr
dsh-client-locale
dsh-client-modules
dsh-client-product-analytics
dsh-client-resources
dsh-client-shortcuts
dsh-client-ui-agent-preset
dsh-client-ui-approval
dsh-client-ui-attachment
dsh-client-ui-brand-official
dsh-client-ui-chat
dsh-client-ui-commands
dsh-client-ui-conversation
dsh-client-ui-cordis
dsh-client-ui-deepseek-model-label-1017
dsh-client-ui-deliverables
dsh-client-ui-directory-picker-browse
dsh-client-ui-directory-picker-native
dsh-client-ui-entry-customization
dsh-client-ui-goal
dsh-client-ui-input-trigger
dsh-client-ui-jobs
dsh-client-ui-layout
dsh-client-ui-message-feedback
dsh-client-ui-model-selection
dsh-client-ui-open-in-app
dsh-client-ui-permission-presets
dsh-client-ui-plan
dsh-client-ui-plugin-manager
dsh-client-ui-plugin-market
dsh-client-ui-reference
dsh-client-ui-renderer
dsh-client-ui-schedule
dsh-client-ui-secret-mask
dsh-client-ui-session
dsh-client-ui-settings
dsh-client-ui-settings-account
dsh-client-ui-settings-agent-loop
dsh-client-ui-settings-general
dsh-client-ui-settings-models
dsh-client-ui-settings-plugin-inventory
dsh-client-ui-settings-plugins
dsh-client-ui-settings-session-log
dsh-client-ui-settings-shell
dsh-client-ui-settings-subagent
dsh-client-ui-settings-web-search
dsh-client-ui-shortcuts
dsh-client-ui-sidebar
dsh-client-ui-sidebar-browser
dsh-client-ui-sidebar-documentpreview
dsh-client-ui-sidebar-files
dsh-client-ui-sidebar-right
dsh-client-ui-sidebar-terminal
dsh-client-ui-skill
dsh-client-ui-subagent
dsh-client-ui-theme
dsh-client-ui-tool
dsh-client-ui-trajectory
dsh-client-ui-user-questions
dsh-client-ui-workflow-run
dsh-client-ui-workspace
dsh-cmdline
dsh-command-compact
dsh-command-feedback
dsh-command-goal
dsh-commands
dsh-compaction
dsh-compaction-basic
dsh-compaction-image-offload
dsh-compaction-tool-result-pruner
dsh-config-editor
dsh-cordis-client-runner
dsh-cordis-host-runner
dsh-credentials
dsh-credentials-local
dsh-deepseek-account
dsh-deepseek-account-platform
dsh-deepseek-llm-api-extensions
dsh-deque
dsh-experimental-agent-team
dsh-experimental-agent-team-profile
dsh-experimental-api-speech-to-text
dsh-experimental-auto-review
dsh-experimental-badge-skill-bundle
dsh-experimental-client-ui-agent-team
dsh-experimental-client-ui-cot-translation
dsh-experimental-client-ui-voice-input
dsh-experimental-cot-translation-bundle
dsh-experimental-inspector-profile
dsh-experimental-plugin-market-bundle
dsh-experimental-ralph-bundle
dsh-experimental-session-inspector
dsh-experimental-session-search
dsh-experimental-session-titles-bundle
dsh-experimental-speech-to-text
dsh-experimental-speech-to-text-sensevoice
dsh-experimental-terminal-bundle
dsh-experimental-tool-agent-team
dsh-experimental-tool-worktree
dsh-experimental-translator
dsh-experimental-voice-input-bundle
dsh-experimental-worktree
dsh-file-reference
dsh-file-reference-local
dsh-fs
dsh-fs-local
dsh-fs-observation-policy
dsh-fs-sandbox
dsh-goal
dsh-goal-round-driver
dsh-harness-dev-context
dsh-headless
dsh-hmr
dsh-home-paths
dsh-host-directory-picker
dsh-host-directory-picker-auto
dsh-host-directory-picker-browse
dsh-host-directory-picker-native
dsh-host-frontend-static
dsh-host-open-in-app
dsh-host-plugin-inventory
dsh-host-product-telemetry-otel
dsh-host-webserver
dsh-http-proxy
dsh-jobs
dsh-jobs-local
dsh-launch-environment
dsh-lazy-require
dsh-llm
dsh-llm-deepseek
dsh-llm-deepseek-account
dsh-llm-deepseek-api-key
dsh-llm-pi-ai
dsh-llm-retry
dsh-mcp-client
dsh-mcp-resources
dsh-message-feedback
dsh-native-command
dsh-office-to-pdf
dsh-otel
dsh-output-retention
dsh-package-manifest
dsh-permission-presets
dsh-persona
dsh-plan-mode
dsh-plugin-manager
dsh-plugin-market
dsh-plugin-market-index
dsh-plugin-package-inventory-deepseek
dsh-ptc-runtime
dsh-ptc-runtime-node
dsh-pwsh-local
dsh-pwsh-sandbox
dsh-repeat-tool-reminder
dsh-sandbox
dsh-sandbox-local
dsh-sandbox-policy
dsh-sandbox-windows-acl
dsh-schedule
dsh-scope
dsh-sdk-app
dsh-sdk-jsonrpc-server
dsh-sdk-minimal
dsh-sdk-protocol
dsh-session
dsh-session-checkpoint-policy
dsh-session-format
dsh-session-format-catalog
dsh-session-format-v0-to-v1
dsh-session-format-v1-to-v2
dsh-session-format-v2-to-v3
dsh-session-format-v3-to-v4
dsh-session-log-deepseek
dsh-session-log-export
dsh-session-persistence
dsh-session-persistence-jsonl
dsh-session-projection
dsh-session-projection-cache
dsh-session-query
dsh-session-query-sqlite
dsh-session-reference
dsh-session-stats
dsh-session-telemetry
dsh-session-telemetry-otel
dsh-session-title
dsh-session-title-all-prompts-llm
dsh-session-title-first-prompt-llm
dsh-session-title-llm
dsh-session-turn-outline
dsh-settings
dsh-shell
dsh-shell-env
dsh-skill
dsh-skill-badge
dsh-skill-filesystem
dsh-skill-office
dsh-spill
dsh-spill-local
dsh-spill-policy
dsh-storage
dsh-storage-domain
dsh-storage-json
dsh-subagent
dsh-subagent-fork-in-process
dsh-subagent-spawn-in-process
dsh-subprocess
dsh-subprocess-local
dsh-system-prompt
dsh-terminal
dsh-terminal-bash
dsh-time-context
dsh-timeout
dsh-tmux-context
dsh-token-meter
dsh-tool-ask-user
dsh-tool-bash
dsh-tool-bash-persistent
dsh-tool-call-timeout-policy
dsh-tool-cordis
dsh-tool-fs
dsh-tool-fs-search
dsh-tool-goal
dsh-tool-jobs
dsh-tool-present
dsh-tool-pwsh
dsh-tool-pwsh-persistent
dsh-tool-ralph
dsh-tool-schedule
dsh-tool-session-query
dsh-tool-skill
dsh-tool-str-replace-editor
dsh-tool-subagent
dsh-tool-subagent-control
dsh-tool-terminal
dsh-tool-todo
dsh-tool-web
dsh-tool-workflow
dsh-tool-working-directory
dsh-tool-workspace-dependencies
dsh-tools
dsh-typert-loader
dsh-typert-protocol
dsh-typert-registry
dsh-user-approval
dsh-user-questions
dsh-util-code-language
dsh-util-crypto
dsh-util-time
dsh-util-values
dsh-util-workspace-path
dsh-web
dsh-web-app
dsh-web-deepseek-api
dsh-web-fetch-http
dsh-web-frontend
dsh-web-search-deepseek
dsh-win32-process
dsh-workflow
dsh-workflow-ptc
dsh-working-directory
dsh-workspace
dsh-workspace-changes
libreoffice-kit
libreoffice-kit-wasm
node-addon-system
node-addon-system-linux-x64
schemastery
```

</details>


### 4.5 Step 18 证明了什么、没证明什么

**证明**：在这个隔离安装 + 这个 profile 下，AEH 插件能被 loader 挂载，6 个工具能注册并执行，
合成会话能跑完（`summary.json`：`events=39`、6 次工具调用、退出码 0、0 错误；门禁拒绝
`kcs_not_allowed:kc.fraction.multiply`；复习 `nextIntervalDays=3.2`；报告
`independentAccuracy=0.75`）。

**没证明**：没有做“删包后仍能跑”的实验；没有验证多进程/多副本、崩溃恢复、配额计费、
真实身份/LMS；没有证明 306 个安装项里哪些是运行必需——只有 dump-config 的 75 个启用包
和合成会话实际经过的链路有正面证据。

## 5. 分类方法与总表

### 5.1 判定规则

| 代码 | 分类 | 判定 |
|---|---|---|
| D1 | **AEH 必需（直接 import）** | `dsh-plugin/src/**` 或 `e2e/**` 直接 import 该包 |
| S18 | **AEH 必需（Step 18 链路）** | Step 18 profile 声明，或 `dump-config` 启用且合成会话实际经过的启动/agent/session/模型链路 |
| R | **保留** | Daniel 明确点名保留（桌面端、`client`/Web UI、上下文压缩），或按保守原则判定“有用/未来可能用”的产品面、通用能力、实验特性、测试夹具 |
| T | **传递依赖** | 不在 D1/S18/R，但启用，或位于 D1/S18 的 dependencies/peerDependencies 闭包内；插件不直接 import |
| P | **待确认** | Step 18 显式 disabled；保留但需 Daniel 决定是否作为 AEH 产品面启用 |
| U | **无用（可删）** | 自声明“临时/弃用”、已被指定替代，或完全无未来使用路径；**只有这一列进入删除建议** |

优先级：D1 > S18 > R > P > T > U。也就是说：Daniel 点名保留的，即使原本属于传递依赖也归 R；
Step 18 显式 disabled 的归 P；只要启用或属于闭包，就不会被归 U。

层次口径：**必需**是跑起来的最小闭包；**保留**是“有用或未来可能用”的存量；**传递**是闭包
带入但非产品决策项；**待确认**是需要 Daniel 拍板的 20 个 disabled 项；**无用（可删）**只有
自声明临时/弃用的 2 个。

### 5.2 分类总表

| 分类 | 定义 | `packages/` | `apps/` | 合计 | 处理建议 |
|---|---|---:|---:|---:|---|
| AEH 必需（直接 import） | 插件源码直接 import | 3 | 0 | **3** | 永不删；另有 2 个外部包（cordis、schemastery） |
| AEH 必需（Step 18 链路） | profile/启动/agent/session/模型链路 | 11 | 1 | **12** | 永不删 |
| **保留** | Daniel 点名或按保守原则判定“有用/未来可能用” | 218 | 4 | **222** | 保留；不进入删除建议 |
| 传递依赖 | 依赖/peer 闭包带入 | 109 | 0 | **109** | 不逐个删；换 bundle 后再按闭包收缩 |
| 待确认 | Step 18 显式 disabled | 20 | 0 | **20** | 保留待决，不删 |
| 无用（可删） | 自声明临时/弃用、完全无未来用途 | 2 | 0 | **2** | 唯一进入删除建议的极小集合（§6.6、§7） |
| **合计** |  | **363** | **5** | **368** | 另加 2 个外部直接依赖 = 370 个依赖节点 |

> “必需”合计：workspace 15（3 + 11 + 1 个 CLI）+ 外部 2（cordis、schemastery）= **17**。
> 插件直接 import 的 5 个包里，cordis 与 schemastery 不在 368 个 workspace 包内。
> 口径：**保留** = 明确判定要留（含 Daniel 点名的桌面端/压缩与保守保留）；**待确认** = 需
> Daniel 决定是否启用的 20 个 Step 18 disabled 项；**无用（可删）** = 唯一可删集合，仅 2 个。

### 5.3 必需清单（15 个 workspace + 2 个外部）

| # | 包 | 分类 | 依据 |
|---:|---|---|---|
| 1 | `@deepseek-ai/dsh-tools` | D1 | `src/dsh.ts:19-27` 的 `defineTool` 与 schema 类型 |
| 2 | `@deepseek-ai/dsh-llm` | D1 | `src/security.ts:30` 的 `HarnessError`；`src/dsh.ts:28` 的 `ContentBlock` |
| 3 | `@deepseek-ai/dsh-util-values` | D1（type-only） | `src/dsh.ts:29` 的 `JsonValue` |
| 4 | `@deepseek-ai/dsh-base` | S18 | profile 的第一个 bundle |
| 5 | `@deepseek-ai/dsh-headless` | S18 | profile 的第二个 bundle |
| 6 | `@deepseek-ai/dsh-agent` | S18 | `dump-config` 启用；agent 注册 |
| 7 | `@deepseek-ai/dsh-agent-loop` | S18 | `dump-config` 启用；驱动 6 次工具调用 |
| 8 | `@deepseek-ai/dsh-agent-default-model` | S18 | patch 配置 sidrune / deepseek-v4-1-flash |
| 9 | `@deepseek-ai/dsh-session` | S18 | `dump-config` 启用；会话持久化 |
| 10 | `@deepseek-ai/dsh-session-projection` | S18 | `dump-config` 启用；会话投影 |
| 11 | `@deepseek-ai/dsh-session-persistence-jsonl` | S18 | 证据里的 JSONL 会话日志 |
| 12 | `@deepseek-ai/dsh-session-log-deepseek` | S18 | `dump-config` 启用；日志请求扩展 |
| 13 | `@deepseek-ai/dsh-llm-pi-ai` | S18 | patch 的模型 provider 路由 |
| 14 | `@deepseek-ai/dsh-system-prompt` | S18 | `dump-config` 启用；提示词组装 |
| 15 | `@deepseek-ai/dsh`（apps/cli） | S18 | Step 18 的 `dsh` 启动器 |
| 16 | `@deepseek-ai/cordis` | D1（外部，type-only） | `src/dsh.ts:31` 的 `Context` |
| 17 | `@deepseek-ai/schemastery` | D1（外部） | `src/config.ts:22` 的 `Schema` |

### 5.4 待确认清单（20 个）

这 20 个都是 Step 18 patch 显式 `disabled` 的。它们不是“没证据”，而是“证据显示当前
验收关掉了，但生产是否保留要产品决策”。

| 组 | 包 | 决策问题 |
|---|---|---|
| shell | `dsh-tool-bash`、`dsh-tool-pwsh` | AEH 宿主是否允许模型执行 shell？当前 Step 18 = 不允许。 |
| fs | `dsh-tool-fs`、`dsh-tool-fs-search` | 是否允许模型读写工作区？AEH 工具本身是纯计算/内存。 |
| jobs | `dsh-tool-jobs` | 是否需要后台任务工具？ |
| skill | `dsh-tool-skill` | 是否加载 Agent 技能？ |
| todo | `dsh-tool-todo` | 是否需要 todo 工具？ |
| goal | `dsh-tool-goal` | 是否需要持久目标工具？ |
| web | `dsh-tool-web` | 是否允许联网搜索/抓取？ |
| workflow | `dsh-tool-workflow` | 是否需要 workflow 工具？ |
| subagent | `dsh-tool-subagent`、`dsh-tool-subagent-control` | 是否允许子代理？ |
| session | `dsh-tool-working-directory` | 是否需要工作目录工具？ |
| interaction | `dsh-user-questions` | 是否需要向用户提问？ |
| boot | `dsh-hmr`、`dsh-plugin-manager` | 是否需要热更新/运行时插件管理？ |
| context | `dsh-agent-instructions` | 是否加载 AGENTS.md/CLAUDE.md？ |
| credentials | `dsh-authorization`、`dsh-credentials-local`、`dsh-deepseek-account-platform` | 生产凭据/账号走哪条路径？Step 18 用环境变量 + 禁用托管凭据。 |

**建议的决策规则**：如果 AEH 是“嵌入通用 dsh CLI 的教育插件”，保留这些包但默认 disabled；
如果 AEH 是“自带锁定宿主的垂直产品”，可以删，但要在 profile 层同步删掉对应 patch 行，
否则 `--dump-config` 会因为找不到 id 而失败。**按 Daniel 的保守原则，这 20 个一律不进入删除
建议**：代码与运行时保留、默认 disabled，是否启用属于产品决策。

### 5.5 传递依赖（109 个）的结构

109 个里，57 个在 Step 18 `dump-config` 启用，52 个只在依赖/peer 闭包里、没有单独组合。
`compaction` 组 5 个已按 Daniel 要求移入 §5.6 保留，故由 114 降为 109。按组分布如下
（完整逐包见 §6.3）：

| 组 | 包数 | 组内代表（示例） |
|---|---:|---|
| `session` | 15 | `dsh-session-checkpoint-policy`, `dsh-session-format`, `dsh-session-format-catalog` |
| `util` | 14 | `dsh-atomic-write`, `dsh-brand`, `dsh-chunked-list` |
| `llm` | 7 | `dsh-deepseek-llm-api-extensions`, `dsh-llm-deepseek`, `dsh-llm-deepseek-account` |
| `shell` | 6 | `dsh-bash-local`, `dsh-bash-sandbox`, `dsh-pwsh-local` |
| `fs` | 4 | `dsh-fs`, `dsh-fs-local`, `dsh-fs-observation-policy` |
| `sandbox` | 4 | `dsh-sandbox`, `dsh-sandbox-local`, `dsh-sandbox-policy` |
| `web` | 4 | `dsh-web`, `dsh-web-deepseek-api`, `dsh-web-fetch-http` |
| `boot` | 3 | `dsh-app-boot`, `dsh-cmdline`, `dsh-config-editor` |
| `goal` | 3 | `dsh-command-goal`, `dsh-goal`, `dsh-goal-round-driver` |
| `interaction` | 3 | `dsh-commands`, `dsh-permission-presets`, `dsh-user-approval` |
| `spill` | 3 | `dsh-spill`, `dsh-spill-local`, `dsh-spill-policy` |
| `storage` | 3 | `dsh-storage`, `dsh-storage-domain`, `dsh-storage-json` |
| `subagent` | 3 | `dsh-subagent`, `dsh-subagent-fork-in-process`, `dsh-subagent-spawn-in-process` |
| `subprocess` | 3 | `dsh-subprocess`, `dsh-subprocess-local`, `dsh-win32-process` |
| `typert` | 3 | `dsh-typert-loader`, `dsh-typert-protocol`, `dsh-typert-registry` |
| `api` | 2 | `dsh-api-gateway`, `dsh-api-remote-access` |
| `attachment` | 2 | `dsh-attachment`, `dsh-attachment-local` |
| `credentials` | 2 | `dsh-credentials`, `dsh-deepseek-account` |
| `feedback` | 2 | `dsh-command-feedback`, `dsh-message-feedback` |
| `guard` | 2 | `dsh-repeat-tool-reminder`, `dsh-tool-call-timeout-policy` |
| `host` | 2 | `dsh-host-plugin-inventory`, `dsh-host-webserver` |
| `jobs` | 2 | `dsh-jobs`, `dsh-jobs-local` |
| `ptc-runtime` | 2 | `dsh-ptc-runtime`, `dsh-ptc-runtime-node` |
| `session-query` | 2 | `dsh-session-query`, `dsh-session-query-sqlite` |
| `skill` | 2 | `dsh-skill`, `dsh-skill-filesystem` |
| `workflow` | 2 | `dsh-workflow`, `dsh-workflow-ptc` |
| `core` | 1 | `dsh-scope` |
| `deliverables` | 1 | `dsh-tool-present` |
| `identity` | 1 | `dsh-anonymous-user-id` |
| `mcp` | 1 | `dsh-mcp-resources` |
| `plan` | 1 | `dsh-plan-mode` |
| `preset` | 1 | `dsh-agent-preset-registry` |
| `settings` | 1 | `dsh-settings` |
| `telemetry` | 1 | `dsh-otel` |
| `workspace` | 1 | `dsh-workspace` |
| **合计** | **109** |  |

**硬约束环（不要误删）**：下面这些虽然归“传递依赖”，但删了会直接破坏 peer/库解析：

- `dsh-tools` 的 peer：`dsh-agent`（已必需）、`dsh-scope`、`dsh-session`（已必需）、
  `dsh-system-prompt`（已必需）、`dsh-user-approval`、`dsh-sandbox`、`dsh-sandbox-policy`、
  `dsh-working-directory`、`dsh-ptc-runtime`、`dsh-llm`（已必需）、`cordis`（已必需）。
- `dsh-llm` 的 dependency：`dsh-brand`、`dsh-timeout`、`dsh-util-crypto`、
  `dsh-typert-protocol`、`schemastery`（已必需）、`zod`。
- `dsh-agent-loop` 的 dependency：`dsh-brand`、`dsh-util-values`（已必需）、`schemastery`。
- `dsh-session` 的 dependency：`dsh-llm`（已必需）、`dsh-brand`、`dsh-util-values`（已必需）。

这四组大约 20 个包是“删任何一个都可能让 dsh-tools/dsh-llm 直接起不来”的。其余约 90 个
才是 bundle 收缩后可以再评估的；本版按保守原则**不把传递依赖列为删除对象**。

### 5.6 保留（222 个：218 个 `packages/` + 4 个 `apps/`）的结构

Daniel 的保守保留原则下，原先判为“无用”的 215 个包里 213 个改为保留（2 个自声明死包除外），
再加 `compaction` 组 5 个，共 218 个包；`apps/` 侧保留 `desktop`、`desktop-host`、`web`、
`plugin-market-generator` 4 个。合计 **222**。典型构成：

- **桌面端直接相关**：`apps/desktop`、`apps/desktop-host`、`client` 组 67 个（68 个里去掉
  1 个自声明临时徽章）、`host` 组 7 个、`api` 组 8 个、`bundle/web-app` 等；
- **上下文压缩**：`compaction` 组 5 个（Daniel 点名）；
- **实验特性**：`experimental` 组 58 个（未来桌面版/真实会话可能启用）；
- **其他产品面**：`ssh` 5、`lsp` 3、`sdk` 3、`browser-use`/`computer-use`、`document`、
  `deliverables`、`schedule`、`terminal`、`web`、`plugin-market` 等；
- **测试/构建资产**：`test-support` 8、`typert` 的生成器、`util` 的桌面/市场辅助库等。

按组分布（完整逐包见 §6.5）：

| 组 | 包数 | 组内代表（示例） |
|---|---:|---|
| `client` | 67 | `dsh-client-connection`, `dsh-client-ui-chat`, `dsh-client-ui-layout` |
| `experimental` | 58 | `dsh-experimental-agent-team`, `dsh-experimental-voice-input-bundle` |
| `api` | 8 | `dsh-api-account-controller`, `dsh-api-remotes` |
| `test-support` | 8 | `dsh-agent-loop-testkit`, `dsh-llm-mock-server` |
| `host` | 7 | `dsh-host-directory-picker`, `dsh-host-webserver` |
| `context` | 6 | `dsh-file-reference`, `dsh-time-context` |
| `util` | 6 | `dsh-native-command`, `dsh-official-bundles`, `dsh-plugin-detail` |
| `compaction` | 5 | `dsh-command-compact`, `dsh-compaction-basic`, `dsh-compaction-tool-result-pruner` |
| `ssh` | 5 | `dsh-fs-ssh`, `dsh-ssh` |
| `bundle` | 4 | `dsh-acp-app`, `dsh-sdk-app`, `dsh-sdk-minimal`, `dsh-web-app` |
| `extensions` | 4 | `dsh-cordis-client-runner`, `dsh-tool-cordis` |
| `subagent` | 4 | `dsh-subagent-acp`, `dsh-subagent-claude-code`, `dsh-subagent-codex` |
| `core` | 2 | `dsh-tool-executor-native`, `dsh-tool-executor-ptc` |
| `deliverables` | 2 | `dsh-deliverable-file-references`, `dsh-workspace-changes` |
| `preset` | 2 | `dsh-agent-preset`, `dsh-persona` |
| `schedule` | 2 | `dsh-schedule`, `dsh-tool-schedule` |
| `shell` | 2 | `dsh-tool-bash-persistent`, `dsh-tool-pwsh-persistent` |
| `skill` | 2 | `dsh-skill-office`, `dsh-tool-workspace-dependencies` |
| `terminal` | 2 | `dsh-terminal`, `dsh-terminal-bash` |
| `web` | 2 | `dsh-web-search-exa`, `dsh-web-search-perplexity` |
| `lsp` | 3 | `dsh-lsp`, `dsh-lsp-stdio`, `dsh-tool-lsp` |
| `sdk` | 3 | `dsh-sdk-client`, `dsh-sdk-jsonrpc-server`, `dsh-sdk-protocol` |
| `session` | 3 | `dsh-message-quotes`, `dsh-session-stats`, `dsh-session-turn-outline` |
| `acp` | 1 | `dsh-acp` |
| `boot` | 1 | `dsh-plugin-market` |
| `browser-use` | 1 | `dsh-browser-use` |
| `computer-use` | 1 | `dsh-computer-use` |
| `document` | 1 | `dsh-office-to-pdf` |
| `fs` | 1 | `dsh-tool-str-replace-editor` |
| `interaction` | 1 | `dsh-tool-ask-user` |
| `mcp` | 1 | `dsh-mcp-client` |
| `session-query` | 1 | `dsh-session-log-export` |
| `storage` | 1 | `dsh-storage-sqlite` |
| `typert` | 1 | `dsh-typert-generator` |
| **合计** | **218** |  |

### 5.7 无用（可删，2 个）

保守原则下**唯一**进入删除建议的集合，且只有 2 个——都自声明为“临时/弃用”：

| 包 | 组 | 为什么是“完全无用且未来不可能用上” |
|---|---|---|
| `@deepseek-ai/dsh-agent-tool-presentation` | core | `package.json` 自述 `Deprecated ... use dsh-tool-executor-native or dsh-tool-executor-ptc directly`；Step 18 未组合，唯一直接引用是 `apps/cli/package.json`。 |
| `@deepseek-ai/dsh-client-ui-deepseek-model-label-1017` | client | `package.json` 自述 `Temporary 1017 release badge`；引用点是 `packages/bundle/web-app` 的 patch 与 manifest。若 Daniel 要求桌面端保留官方徽章，可移回保留（可删集降为 1）。 |

> 其余“Step 18 未组合/未安装”的包（含全部实验特性、SSH、LSP、SDK/ACP、浏览器/桌面自动化、
> Office、测试夹具等）一律保留或待确认，不列入可删。

## 6. 逐包明细

说明列保留 `package.json` 的 `description` 原文摘要（截断到 110 字符），避免二次翻译失真；
分组说明与分类理由为中文。`组` 列是 `packages/<组>/<包>` 的组名；app 用 `apps/<名>`。

### 6.1 必需（直接 import，3 个）

| 包 | 组 | 说明（package.json 原文摘要） | 分类理由 |
|---|---|---|---|
| `@deepseek-ai/dsh-tools` | core | Tool registry and execution pipeline for the DeepSeek Harness | `src/dsh.ts:19-27` 导入 `defineTool` 与 schema 类型；`:33` 再导出 `ToolRunContext`。工具注册/参数校验/执行都由它承担。 |
| `@deepseek-ai/dsh-llm` | llm | Provider-neutral LLM service interface for the DeepSeek Harness | `src/dsh.ts:28,32` 类型 `ContentBlock`；`src/security.ts:30` 值导入 `HarnessError`（错误映射）。 |
| `@deepseek-ai/dsh-util-values` | util | Duplicate-install-safe value primitives for the DeepSeek Harness | `src/dsh.ts:29` 类型 `JsonValue`（type-only）。 |

### 6.2 必需（Step 18 链路，11 个）

| 包 | 组 | 说明（package.json 原文摘要） | 分类理由 |
|---|---|---|---|
| `@deepseek-ai/dsh-base` | bundle | The shared dsh core as a profile bundle: the first patch layer of base-backed profiles, inserting core rows o… | `step18/home/profiles/aeh-e2e/package.json` 的 `dsh.profile.bundles` 第一个 bundle；`dump-config.txt` 第 1 行起组合。 |
| `@deepseek-ai/dsh-headless` | bundle | The dsh one-shot bundle: a direct core Agent/Session runner over dsh-base with no Host, HTTP, or browser layer | 同上，第二个 bundle；headless 一次性运行器，Step18 的启动形态。 |
| `@deepseek-ai/dsh-agent` | core | Agent interface, registry, initiator scope, and event vocabulary for the DeepSeek Harness | `dump-config.txt` 启用；会话中的 agent 实例由它注册。 |
| `@deepseek-ai/dsh-agent-default-model` | core | Default model selection shared by Agent entry points | `cordis.patch.yml` 配置 `provider=sidrune`、`model=deepseek-v4-1-flash`；`dump-config.txt` 启用。 |
| `@deepseek-ai/dsh-agent-loop` | core | The concrete agent loop plugin for the DeepSeek Harness | `dump-config.txt` 启用；驱动 6 次工具调用的 agent loop。 |
| `@deepseek-ai/dsh-session` | core | Event-sourced session store for the DeepSeek Harness | `dump-config.txt` 启用；`summary.json`/会话日志证明有持久会话。 |
| `@deepseek-ai/dsh-system-prompt` | core | System prompt assembly registry for the DeepSeek Harness | `dump-config.txt` 启用；工具 schema 与提示词组装依赖它。 |
| `@deepseek-ai/dsh-llm-pi-ai` | llm | pi-ai-backed DeepSeek adapter for the DeepSeek Harness LLM seam (design-verification twin of dsh-llm-deepseek) | `cordis.patch.yml` 的 `llm-pi-ai` 路由到 sidrune；合成会话的模型调用经过它。 |
| `@deepseek-ai/dsh-session-log-deepseek` | session | Incremental lossless session-log request extension for the official DeepSeek LLM API | `dump-config.txt` 启用；会话日志请求扩展。 |
| `@deepseek-ai/dsh-session-persistence-jsonl` | session | JSONL durable session persistence backend for the DeepSeek Harness | `dump-config.txt` 启用；`evidence/.../session-log/` 的 JSONL 由它写出。 |
| `@deepseek-ai/dsh-session-projection` | session | Session-projection seam: the merge-extensible projection type table, the provider contract, and the ctx.sessi… | `dump-config.txt` 启用；会话投影缓存与读取依赖它。 |

### 6.3 传递依赖（109 个）

| 包 | 组 | 说明（package.json 原文摘要） | 分类理由 |
|---|---|---|---|
| `@deepseek-ai/dsh-api-gateway` | api | Typert Remote Host dispatcher and Client API endpoint | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-api-remote-access` | api | Method-level Remote access control for non-owner Peers and the per-Peer access snapshot | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-attachment` | attachment | Durable immutable attachment storage seam for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-attachment-local` | attachment | Private content-addressed DSH_HOME attachment storage | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-app-boot` | boot | Shared boot glue for the app bins: .env loading, fail-loud Loader guards, snapshot-aware config resolution, a… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-cmdline` | boot | Immutable command-line handoff from a dsh launcher to any app plugin that injects cmdlineArgs | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-config-editor` | boot | Persist plugin configuration through profile patches and Loader reconciliation | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-scope` | core | Scoped-context registration primitive (scope tags, scope-filtered event dispatch) for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-credentials` | credentials | Abstract credential seam (ctx.credentials): settings carry references to secrets, providers own the values | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-deepseek-account` | credentials | Read account state and resolve official API credentials | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-tool-present` | deliverables | Explicit workspace file delivery declarations for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-command-feedback` | feedback | Log-only session feedback: the record event, the sessionFeedback Host Remote, and the human-facing slash comm… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-message-feedback` | feedback | Canonical Session-log ratings and notes for finalized assistant messages | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-fs` | fs | Abstract filesystem capability seam (ctx.fs) for the DeepSeek Harness — vocabulary types, the FileSystem serv… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-fs-local` | fs | Local-filesystem implementation of the DeepSeek Harness filesystem seam (ctx.fs) | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-fs-observation-policy` | fs | File-context policy plugin for the DeepSeek Harness — observed-state, read-before-edit, and version-guarded w… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-fs-sandbox` | fs | Sandbox-enforcing implementation of the DeepSeek Harness filesystem seam: fences write/edit by the per-call s… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-command-goal` | goal | Human-facing slash command for persisted same-session goals | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-goal` | goal | Event-sourced same-session goal state and lifecycle service for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-goal-round-driver` | goal | Race-fenced same-session goal-round driver | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-repeat-tool-reminder` | guard | Repeat-tool-call guard plugin: advisory reminders when an agent loops on identical tool calls | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-tool-call-timeout-policy` | guard | Tool-call timeout policy: a tools/execute wrapper that arms a per-tool deadline on exec.signal and returns TO… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-host-plugin-inventory` | host | Read-only Remote projection of current Cordis Loader plugin state | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-host-webserver` | host | Web route-registration plugin: HTTP and upgrade routes, per-Peer index transform taps, and static dist fallba… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-anonymous-user-id` | identity | Shared anonymous user identity for DeepSeek Harness telemetry and feedback correlation | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-commands` | interaction | Plugin-owned human command registry for DeepSeek Harness UIs | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-permission-presets` | interaction | User-facing permission presets (ctx.permissionPresets) for the DeepSeek Harness: one product-level Permission… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-user-approval` | interaction | User-approval seam (ctx.approval) for the DeepSeek Harness: one-shot permission decisions dispatched to compo… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-jobs` | jobs | Background job registry (ctx.jobs) for the DeepSeek Harness — shared ids, owner isolation, polling, cancellat… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-jobs-local` | jobs | Process-local implementation of the DeepSeek Harness background job registry seam | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-deepseek-llm-api-extensions` | llm | Additive request-field registry for the official DeepSeek LLM API adapter | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-llm-deepseek` | llm | DeepSeek Messages adapter | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-llm-deepseek-account` | llm | DeepSeek account provider authentication and discovery | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-llm-deepseek-api-key` | llm | DeepSeek api-key provider authentication and discovery | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-llm-retry` | llm | Provider-routed LLM request retry policy for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-plugin-package-inventory-deepseek` | llm | Active Loader-backed plugin package inventory for official DeepSeek LLM API requests | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-token-meter` | llm | Replay-aware token measurement service (ctx.tokenMeter) for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-mcp-resources` | mcp | Scoped MCP resource discovery and reading through shared model tools | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-plan-mode` | plan | Logged per-agent plan mode with deployment guidance, a direct slash command, and a user-reviewed exit | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-agent-preset-registry` | preset | Declarative Agent preset registry and profile-backed editing | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-ptc-runtime` | ptc-runtime | Abstract PTC execution seam (ctx.ptcRuntime) for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-ptc-runtime-node` | ptc-runtime | Node PTC execution with per-call sandboxed processes or in-memory REPL state | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-sandbox` | sandbox | Abstract process-sandbox seam (ctx.sandbox) for the DeepSeek Harness: same-world confinement vocabulary and t… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-sandbox-local` | sandbox | Local process-sandbox backends for the DeepSeek Harness sandbox seam: bwrap, the npm-distributed landlock-run… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-sandbox-policy` | sandbox | Per-call sandbox policy resolver and current model context: deployment fallbacks plus each session's mode and… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-sandbox-windows-acl` | sandbox | Windows ACL write-restriction sandbox backend (restricted-token spawn with capability-SID write allowlist) fo… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-checkpoint-policy` | session | Semantic session durability checkpoints before model requests and tool side effects | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-session-format` | session | Streaming adjacent Session format migration machinery | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-format-catalog` | session | Build-static first-party Session format codec and migration catalog | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-format-v0-to-v1` | session | Frozen released-v0 Session codec and identity migration to v1 | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-format-v1-to-v2` | session | Frozen released-v1 Session codec and assistant-stream migration to v2 | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-format-v2-to-v3` | session | Streaming system-prompt, canonical-envelope and PTC migration into V3 | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-format-v3-to-v4` | session | Streaming tool-role migration and delivery validation from Session V3 to V4 | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-persistence` | session | Abstract durable session persistence seam (ctx.sessionPersistence) for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-projection-cache` | session | Persisted projection cache (ctx.sessionProjectionCache): durable per-session checkpoint records on the sessio… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-session-telemetry` | session | SessionTelemetryBackend seam for the DeepSeek Harness: session-event capture, projection, redaction, and hand… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-telemetry-otel` | session | Feedback-authorized Session logs over byte-bounded OpenTelemetry HTTP requests | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-session-title` | session | Log-backed session title service and provider registry for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-session-title-first-prompt-llm` | session | First-message LLM provider plugin for DeepSeek Harness session titles | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-session-title-llm` | session | Shared LLM generation policy for DeepSeek Harness session-title providers | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-working-directory` | session | Session working directories with durable changes and model context | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-session-query` | session-query | Combined session query service contract with concrete reads, traces, and filters | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-session-query-sqlite` | session-query | Concrete ctx.sessionQuery backend with SQLite FTS5 search | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-settings` | settings | Abstract user-settings seam (ctx.settings) for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-bash-local` | shell | Local-subprocess implementation of the DeepSeek Harness bash executor seam | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-bash-sandbox` | shell | Sandbox-consuming implementation of the DeepSeek Harness bash executor seam (confines every command via ctx.s… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-pwsh-local` | shell | Local PowerShell implementation of the DeepSeek Harness bash executor seam | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-pwsh-sandbox` | shell | Sandbox-consuming implementation of the DeepSeek Harness PowerShell executor seam (confines every command via… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-shell` | shell | Abstract bash executor seam (ctx.shell) for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-shell-env` | shell | Tool-independent managed DSH_* shell environment registry | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-skill` | skill | Agent skill provider registry for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-skill-filesystem` | skill | Local filesystem skill provider for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-spill` | spill | Abstract spill storage seam (ctx.spillStore) for the DeepSeek Harness — save oversized tool text and return a… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-spill-local` | spill | Local-filesystem implementation of the DeepSeek Harness spill storage seam (private session-scoped files) | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-spill-policy` | spill | Token-budgeted tool-result retention with recoverable text and image paths | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-storage` | storage | Storage hub (ctx.storage): named backend registry plus mounted data-form facilities for the DeepSeek Harness | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-storage-domain` | storage | Domain data form (ctx.storage.domain): schema-validated, event-emitting KV domains over storage backends for … | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-storage-json` | storage | JSON file KV storage backend for the DeepSeek Harness storage hub | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-subagent` | subagent | Abstract subagent seam (ctx.subagents): named-provider registry for delegating to child agents | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-subagent-fork-in-process` | subagent | In-process fork subagent backend: runs a child agent seeded with a prefix of the parent's log | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-subagent-spawn-in-process` | subagent | In-process spawn subagent backend: runs a fresh child agent on ctx.agents | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-subprocess` | subprocess | Subprocess seam (ctx.subprocess) for the DeepSeek Harness — managed process groups, bounded spill-backed outp… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-subprocess-local` | subprocess | Local-subprocess implementation of the DeepSeek Harness subprocess seam | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-win32-process` | subprocess | Shared low-level Win32 process, stdio, and Job Object primitives | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-otel` | telemetry | Cordis service for independent ordinary-event and byte-bounded Session-log OTLP channels | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-typert-loader` | typert | Loader integration for generated Typert package contributions | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-typert-protocol` | typert | Compiler-independent Remote metadata and Typert provider protocols | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-typert-registry` | typert | Runtime registry for generated package reflection and Zod schemas | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-atomic-write` | util | Zero-dependency atomic file replacement: exclusive-create random-suffix temp + rename carrying the caller-sta… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-brand` | util | Stateless branded primitive types for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-chunked-list` | util | Persistent append-only chunked lists with bounded copying and JSON checkpoint validation | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-deque` | util | Zero-dependency circular deque with amortized constant-time end operations and bounded vacant storage | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-home-paths` | util | Shared filesystem path helpers for the DeepSeek Harness | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-http-proxy` | util | Process-wide outbound HTTP proxy policy for DeepSeek Harness: resolve it from the launch environment and inst… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-launch-environment` | util | Immutable DeepSeek Harness launch environment that records which layer supplied each value | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-lazy-require` | util | Caller-relative, success-cached lazy loading for CommonJS-compatible Host dependencies | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-output-retention` | util | Zero-dependency bounded-retention primitive: ItemRetainer/TextRetainer + neutral notice helpers (what did we … | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-package-manifest` | util | Shared type declarations for package.json.dsh configuration fields | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-timeout` | util | Zero-dependency timeout/deadline primitive: clampTimeout, deadline, timeoutOf, TimeoutReason (timing + classi… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-util-code-language` | util | Single file-extension to syntax-highlighting language table shared by Client code surfaces and the Host read … | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-util-crypto` | util | Zero-dependency browser-safe UUID and byte-encoding helpers | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-util-time` | util | Time vocabulary shared by the boundaries that accept a caller's zone, a wall-clock selector, or an elapsed ti… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-web` | web | Abstract web access capability seam (ctx.web) for the DeepSeek Harness — search/fetch provider registry, regi… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-web-deepseek-api` | web | DeepSeek Search and Fetch API providers for the DeepSeek Harness web capability seam (ctx.web) | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-web-fetch-http` | web | Anonymous HTTP(S) fetch provider for the DeepSeek Harness web capability seam (ctx.web) | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-web-search-deepseek` | web | DeepSeek-backed search provider (native web_search via the Anthropic-compatible API) for the DeepSeek Harness… | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-workflow` | workflow | Workflow capability seam: ctx.workflowEngine service, run vocabulary, and workflow/* events | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |
| `@deepseek-ai/dsh-workflow-ptc` | workflow | Workflow orchestration in the shared sandboxed Node PTC runtime | Step18 `dump-config` 启用；插件 `src`/`e2e` 无 import，由 base/agent 链路带入。 |
| `@deepseek-ai/dsh-workspace` | workspace | Workspace entity registry (ctx.workspaceRegistry): durable workspace records with validated session attachmen… | 位于必需包的依赖/peer 闭包；Step18 未单独组合；插件无 import。 |

### 6.4 待确认（20 个）

| 包 | 组 | 说明（package.json 原文摘要） | 分类理由 |
|---|---|---|---|
| `@deepseek-ai/dsh-hmr` | boot | Coordinated module and profile configuration hot reload | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-plugin-manager` | boot | Current-profile plugin and bundle management shared by dsh CLI, Web and agent tools | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-agent-instructions` | context | Workspace context loader for AGENTS.md/CLAUDE.md instruction files | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-authorization` | credentials | Authorization seam (ctx.authorization): plugin-owned flows that obtain a credential through a conversation wi… | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-credentials-local` | credentials | File-backed credentials provider ($DSH_HOME/.env under the live process environment) for the DeepSeek Harness | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-deepseek-account-platform` | credentials | Authorize DeepSeek accounts through browser PKCE | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-fs` | fs | Model-facing filesystem tools (read, write, edit) over the DeepSeek Harness filesystem seam (ctx.fs) | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-fs-search` | fs | Model-facing filesystem discovery tools (glob, grep) backed by the packaged ripgrep binary (@vscode/ripgrep) | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-goal` | goal | Model-facing same-session goal tools with execution-time authority checks | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-user-questions` | interaction | Abstract user-questions seam (ctx.userQuestions) for asking the human during agent runs | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-jobs` | jobs | Model-facing background job control tools (job_output, job_list, job_kill) over the ctx.jobs registry | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-working-directory` | session | Read and change the active Session working directory | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-bash` | shell | Model-facing bash tool with optional generic background-job and sandbox-escalation support | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-pwsh` | shell | Model-facing pwsh tool over the bash executor seam | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-skill` | skill | Model-facing skill loading tool for the DeepSeek Harness | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-subagent` | subagent | Model-facing subagent delegation tool over the ctx.subagents seam | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-subagent-control` | subagent | Shared messaging, interruption, and child discovery tools for subagents | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-todo` | todo | Model-facing todo_write tool over the DeepSeek Harness event-sourced session log | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-web` | web | Model-facing web tools (web_search, web_fetch) over the DeepSeek Harness web capability seam (ctx.web) | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |
| `@deepseek-ai/dsh-tool-workflow` | workflow | Model-facing workflow tool: run a JavaScript orchestration script over ctx.workflowEngine | Step18 patch 显式 `disabled`；是否保留通用 dsh 能力需 Daniel 决定。 |

### 6.5 保留（218 个）

> 本表 = 原“无用”215 个中按 Daniel 保守原则改为保留的 213 个 + 明确点名保留的 `compaction` 5 个（列于末尾）。

| 包 | 组 | 说明（package.json 原文摘要） | 保留理由 |
|---|---|---|---|
| `@deepseek-ai/dsh-acp` | acp | Automation-only Agent Client Protocol server for driving DeepSeek Harness agents over JSON-RPC stdio | 保守保留：ACP 自动化接入，未来集成可能用；当前 Step18 用 headless。 |
| `@deepseek-ai/dsh-api-account-controller` | api | Expose safe account operations over authenticated Remote | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-api-job-controller` | api | Job Remote observation stream and the reference-counted client job-output service | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-api-remotes` | api | Remote BFF assembly for application-selected Host capabilities | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-api-session-controller` | api | Session Remote commands, cold reads, and live control transport | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-api-settings-controller` | api | Remote owner for the configuration surfaces over the settings-domain seams | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-api-terminal-controller` | api | Session-owned interactive terminals with shell discovery, screen recovery and typed Remote control | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-api-workspace-controller` | api | Workspace Remote commands and reconnect-safe state transport | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-api-workspace-files` | api | Workspace file service and Client resource provider: bounded reads, directory listing, and live metadata over… | 保守保留（Daniel）：Web/Desktop 桌面端 Remote API；当前 headless 不用。 |
| `@deepseek-ai/dsh-plugin-market` | boot | Configured plugin market indexes for the Web Discover page and the plugin_market agent tool | 保守保留：非 AEH 当前路径，但未来桌面端/产品面可能用；当前未组合。 |
| `@deepseek-ai/dsh-browser-use` | browser-use | Exclusive named browser-use provider registration | 保守保留：浏览器自动化 provider，未来桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-acp-app` | bundle | The dsh ACP profile bundle: automation-only JSON-RPC stdio and process lifecycle over dsh-base | 保守保留（Daniel）：Web/SDK/ACP 等其他 profile bundle，桌面端可能复用；当前 Step18 用 base+headless。 |
| `@deepseek-ai/dsh-sdk-app` | bundle | The dsh SDK profile bundle: stdio JSON-RPC serving and process lifecycle over dsh-base | 保守保留（Daniel）：Web/SDK/ACP 等其他 profile bundle，桌面端可能复用；当前 Step18 用 base+headless。 |
| `@deepseek-ai/dsh-sdk-minimal` | bundle | The standalone minimal SDK profile bundle: JSON-RPC, one DeepSeek adapter, persistent shell, and JSONL sessio… | 保守保留（Daniel）：Web/SDK/ACP 等其他 profile bundle，桌面端可能复用；当前 Step18 用 base+headless。 |
| `@deepseek-ai/dsh-web-app` | bundle | The dsh browser-surface bundle: the web patch layer over dsh-base plus the runtime glue plugin (frontend dist… | 保守保留（Daniel）：Web/SDK/ACP 等其他 profile bundle，桌面端可能复用；当前 Step18 用 base+headless。 |
| `@deepseek-ai/dsh-client-connection` | client | Authenticated RPC transport and generation lifecycle | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-file-upload` | client | Agent-scoped browser file upload, streaming intake, and staged receipt service | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-hmr` | client | Web client graph synchronization and rebuilt-bundle reload transport | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-locale` | client | Locale plugin: Host-backed preference, extensible language catalog, browser fallback, and typed built-in dict… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-modules` | client | Client module system, dual-face: node half composes the __DSH_BOOT__ entry graph (incremental dsh.client scan… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-product-analytics` | client | Desktop product event collection and authenticated Host reporting | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-resources` | client | Unified client resource model: protocol-registered providers turn URL addresses into live values, consumed th… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-shortcuts` | client | Application keyboard command registry and physical-key routing | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-store` | client | React-free observable and snapshot-store contracts with the shared Zustand/Immer engine | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-agent-preset` | client | Agent-preset surfaces: the default for later sessions, this session's seat, and the composition editor | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-approval` | client | Approval composer takeover over the scoped Remote Event waterfall | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-attachment` | client | Dynamic attachment presentation plugin for conversation input, message-image, and trajectory image slots | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-brand-official` | client | Official DeepSeek Harness brand occupants for the Web client's sidebar slots | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-chat` | client | Chat Conversation target, node definitions, renderers, and details surface | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-commands` | client | Client command surface: global directory cache, '/' source, three command UI kinds, popupSelect registry | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-conversation` | client | Target-neutral Conversation assembly, shell, composer, queue, and view navigation | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-deliverables` | client | Changed-files card with per-file comparison tabs, delivery cards, and clickable final-response file reference… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-directory-picker-browse` | client | In-app directory browsing surface: the workspace directory-flow owner rendering the host's listing and creati… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-directory-picker-native` | client | Native directory-picker surface: the renderless workspace directory-flow occupant driving the local Desktop o… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-dockkit` | client | Docking layout kit: split-tree engine with invertible operations, and the React components that render and dr… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-entry-customization` | client | Customize plugin entries in the left sidebar, conversation views, and right sidebar, and quickly create new p… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-file-drag` | client | Application-owned file drag transfers and localized failure feedback | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-goal` | client | Session goal surface: GoalBar docked above the composer, read from the goal session projection | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-input-trigger` | client | Input trigger pipeline: '/' and '@' detection, candidate menu, pick routing to registered sources | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-jobs` | client | Session-header background-job list with on-demand streaming record panels | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-layout` | client | Shell plugin: three-column AppFrame with drag handles, ctx.layout viewing-state service (navigation + panels) | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-message-feedback` | client | The Web feedback surface: per-message Like/Dislike in the assistant-message action strip and the feedback dia… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-model-selection` | client | Model selection over the shared model catalog, Session projection, and session.selectModel | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-open-in-app` | client | Web "Open In..." controls: the Session-header split button opening the workspace directory in an installed ap… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-permission-presets` | client | Permission surfaces: a new-session default in General settings and a current-session /permission popup over t… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-plan` | client | Plan mode controls, persistent transcript plan cards, and sidebar Markdown previews | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-plugin-manager` | client | Plugin management for the dsh web client: the sidebar Plugins panel installs, enables, disables, retries, and… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-plugin-market` | client | Discover tab of the dsh web Plugins page: browse configured plugin market indexes and install their bundles | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-primitives` | client | Pure React atoms for the dsh web UI: controls, icons, markdown, and JSON inspectors (zero cordis) | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-reference` | client | Unified Web @file and @session reference source | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-renderer` | client | Browser UI renderer: React slot bindings, ctx.uiRenderer, and the assembled application root | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-schedule` | client | Host task management page and Session reminder catalog | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-secret-mask` | client | Web display masking for recognized credentials in sent user text | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-session` | client | Session Controller adapter for React and session-scoped slots | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings` | client | Settings domain base plugin: shared configuration forms and the canonical settings slot-type contract | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-account` | client | Manage DeepSeek login and open Platform billing pages | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-agent-loop` | client | Settings page of the agent loop on the dsh web client's Plugins page: the parallel tool-call cap of the agent… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-general` | client | Settings ownerless-copy and product onboarding plugin: the General section, shell trigger/header chrome conte… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-models` | client | Models settings and shared product-onboarding dialogs over existing settings and credential joins | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-plugin-inventory` | client | Read-only Cordis Loader inventory tab in Web Plugins settings | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-plugins` | client | Built-in plugins settings section for the dsh web client: the Settings navigation entry and the tab chrome fe… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-session-log` | client | General settings control for Session-log upload with DeepSeek API requests | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-shell` | client | Settings page of the shell executor on the dsh web client's Plugins page: the command timeout and the per-str… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-subagent` | client | Settings page of Subagent delegation on the dsh web client's Plugins page: recursion depth, parallel capacity… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-settings-web-search` | client | Settings page of the DeepSeek web-search provider on the dsh web client's Plugins page: its API key, endpoint… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-shortcuts` | client | Keyboard shortcut reference, recording, and local preference editing | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-sidebar` | client | Sidebar plugin: session multi-level tree, search, grouping, state dots | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-sidebar-browser` | client | Sandboxed Web browser tabs for the right Sidebar | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-sidebar-documentpreview` | client | Extensible Sidebar previews for Office documents, spreadsheets, Markdown, code, images, PDF, HTML, and plain … | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-sidebar-files` | client | Workspace file tree tab type for the right Sidebar: lazy directory listing over the workspaceFiles Remote nam… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-sidebar-right` | client | Right Sidebar: the docking surface's session-bound state, its panel and header expand control, and the naviga… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-sidebar-terminal` | client | Interactive shell tabs for the right Sidebar | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-skill` | client | Web skill references and the dedicated skill tool row | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-slots` | client | Slot registry pure core: typed ordinary Slots and reusable Component Factories, derived props, Store seats, a… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-subagent` | client | Subagent conversation catalog, continuation routing UI, and '@' reference source | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-theme` | client | Theme plugin: Host bootstrap for the pre-plugin palette; ThemeRuntime for light/dark/system state and icon re… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-tool` | client | Client Tool call-tree renderer and keyed per-tool presentation slot | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-trajectory` | client | Trajectory event ledger with an interactive timing overview: pure-consumer plugin registering into the conver… | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-user-questions` | client | Web ask_user_question composer takeover and plan-review presentation UI | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-workflow-run` | client | Durable workflow-run Conversation Node and nested member disclosure for dsh web | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-workspace` | client | Workspace picker plugin: one WorkspacePicker registered into the sidebar and empty-state workspace slots | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前 headless 不加载，插件无 import。 |
| `@deepseek-ai/dsh-client-web` | client | Web boot kernel: static module table, Cordis loader, framework-free boot page, and UI-renderer handoff | 保守保留（Daniel）：未来桌面端将复用 Web/Desktop 前端 UI；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-computer-use` | computer-use | Exclusive named computer-use provider registration | 保守保留：桌面自动化 provider，未来桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-file-reference` | context | File-reference discovery contract and shared @file grammar | 保守保留：上下文注入（文件/时间/tmux），未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-file-reference-local` | context | Local-filesystem ctx.fileReferences provider with bounded fuzzy indexes | 保守保留：上下文注入（文件/时间/tmux），未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-harness-dev-context` | context | Model context naming the DeepSeek Harness checkout and Web GUI URL without letting either change the system p… | 保守保留：上下文注入（文件/时间/tmux），未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-session-reference` | context | Cross-session snapshot references and durable untrusted model context (ctx.sessionReferenceResolver) | 保守保留：上下文注入（文件/时间/tmux），未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-time-context` | context | Durable per-step context with the current time and elapsed time | 保守保留：上下文注入（文件/时间/tmux），未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-tmux-context` | context | Opt-in durable per-step context with this agent's tmux pane and window location | 保守保留：上下文注入（文件/时间/tmux），未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-tool-executor-native` | core | Native tool execution plugin | 保守保留：工具执行路径（native/PTC），未来真实会话可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-tool-executor-ptc` | core | PTC program execution, tool bindings, and generated SDK prompts | 保守保留：工具执行路径（native/PTC），未来真实会话可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-deliverable-file-references` | deliverables | Shared model guidance for file links and deliverables across DeepSeek Harness hosts | 保守保留：文件交付/变更记录，未来真实会话可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-workspace-changes` | deliverables | Per-turn workspace file changes recorded from git working-tree snapshots and whole-file captures, with per-fi… | 保守保留：文件交付/变更记录，未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-office-to-pdf` | document | Shared Office-to-PDF conversion with bounded queues and caching | 保守保留：Office 转 PDF，教育文档场景可能用；当前未组合。 |
| `@deepseek-ai/dsh-action-cards` | experimental | Optional action cards below answers: one shared proposal tool, card state, user actions and status notices | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-action-cards` | experimental | Action cards below completed answers: the shared card frame, kind bodies and the compact tool row | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-creation-recommendations` | experimental | Body of the personalized page card: location choice, creation progress, Keep, Undo and Restore | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-plugin-recommendations` | experimental | Official plugin card body with catalog text and enabling | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-creation-recommendations` | experimental | Create persistent removable interface plugins from explicit conversation needs | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-cua` | experimental | Shared Computer Use application objects, authorization, and logged tool execution | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-cua-bundle` | experimental | Optional macOS Computer Use and permission setup | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-agent-team` | experimental | Implicit-root Agent Teams roster, direct peer messaging, and shared task DAG | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-agent-team-profile` | experimental | Agent Teams collaboration, tools, and Web UI in one experimental bundle | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-api-speech-to-text` | experimental | Authenticated experimental speech transcription for browser clients | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-auto-review` | experimental | Per-tool LLM authorization review for the DeepSeek Harness Auto permission preset | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-badge-skill-bundle` | experimental | Let agents add a “powered by dsh” badge to documents, pull requests, and other outputs. | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-browser-use-chrome-devtools-mcp` | experimental | Experimental per-Session Chromium browser tools through chrome-devtools-mcp | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-browser-use-playwright-mcp` | experimental | Experimental per-Session Chromium browser tools through @playwright/mcp | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-browser-use-runtime` | experimental | Session-owned browser resource lifecycles and MCP integration for experimental providers | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-browser-use-stagehand-native` | experimental | Experimental Stagehand browser tools with separately configured native models | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-claude-code-mods` | experimental | Experimental bridge: load Claude Code mods (hooks modules) and run their hook chains on DeepSeek Harness exte… | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-client-ui-agent-team` | experimental | Web Agent Teams roster, task board, and teammate navigation | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-client-ui-claude-code-mods` | experimental | Web band above the prompt for Claude Code mods: draws each session's mod tree and sends button presses back t… | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-client-ui-cot-translation` | experimental | Optional machine translation of expanded reasoning, preserving original Session text | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-client-ui-voice-input` | experimental | Record speech and insert editable text into the conversation draft | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-computer-use-cua-driver-mcp` | experimental | Experimental computer use through an installed Cua Driver MCP executable | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-computer-use-cua-driver-native` | experimental | Experimental computer-use provider embedding the Cua Driver native npm SDK | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-cot-translation-bundle` | experimental | Experimental machine translation of expanded reasoning | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-cua-macos` | experimental | macOS native provider for shared Computer Use application and window objects | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-inspector` | experimental | Experimental cross-realm CDP hub for Host debugging and Client Runtime inspection | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-inspector-profile` | experimental | Optional Web bundle for raw Session logs and Chat node inspection | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-liveshare-protocol` | experimental | Liveshare wire frames and the identity contract shared by the owner bundle and the Relay | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-plugin-market-bundle` | experimental | Experimental custom plugin indexes: a Discover tab that browses and installs bundles from plugin indexes | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-ptc-runtime-python` | experimental | CPython subprocess implementation of the DeepSeek Harness PTC execution seam | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-ralph-bundle` | experimental | Run explicitly requested repeated work with fresh agents. | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-session-inspector` | experimental | Experimental virtualized Session log and live Chat group/node inspectors | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-session-search` | experimental | Give agents tools to search and read earlier sessions from the current workspace. | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-session-titles-bundle` | experimental | Refresh session titles as new human prompts arrive. | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-speech-to-text` | experimental | Experimental speech recognition with independently selectable providers | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-speech-to-text-sensevoice` | experimental | Local SenseVoice ONNX transcription with a managed sherpa-onnx process | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-subagent-oar` | experimental | Experimental one-shot subagents through OAR runtimes | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-terminal-bundle` | experimental | Keep shell processes alive across tool calls. | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-tool-agent-team` | experimental | Scoped model-facing Agent Teams tools over ctx.agentTeams | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-tool-subagent-oar` | experimental | Delegate standalone tasks to configured external subagent providers | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-tool-worktree` | experimental | Model tool that creates and enters a new Git worktree | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-translator` | experimental | Machine translation with reusable Session results | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-voice-input-bundle` | experimental | Experimental voice input with local SenseVoice; downloads its runtime on first use | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-experimental-webworker-packer` | experimental | Build-time packer for the browser runtime's base VFS image and ordered data-overlay archives | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-webworker-runtime` | experimental | Browser-only harness runtime: in-memory VFS, module transform and loader, postMessage tunnel, and the dedicat… | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-experimental-worktree` | experimental | Creates a named Git worktree and changes the calling Session working directory | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-hook-protocol` | experimental | Shared Claude Code / Codex hook wire protocol: matcher engine, stdin/exit-code/stdout codec, multi-hook merge… | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-hooks-claude-code` | experimental | Bridge plugin: run a Claude Code hooks.json / settings hook config on the DeepSeek Harness interception seams | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-hooks-codex` | experimental | Bridge plugin: run a Codex hooks.json hook config on the DeepSeek Harness interception seams | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-personalized-recommendations` | experimental | Personalized pages and built-in plugin recommendations offered as cards below answers | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-plugin-recommendations` | experimental | Official plugin suggestions with explicit user activation and persistent conversation decisions | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-session-title-all-prompts-llm` | experimental | All-user-messages LLM provider plugin for DeepSeek Harness session titles | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-skill-badge` | experimental | Bundled dsh badge skill provider for DeepSeek Harness | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-tool-ralph` | experimental | Model-facing fresh-agent Ralph loop over the workflow and subagent seams | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-tool-session-query` | experimental | Workspace-authorized model-facing session history search, trace, and event read tools | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-tool-terminal` | experimental | Six model-facing persistent PTY tools with owner isolation and generic background-job integration | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未启用，插件无 import。 |
| `@deepseek-ai/dsh-webhook` | experimental | Fire-and-forget webhook rule runtime that creates Workspace-backed DeepSeek Harness Sessions | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-webhook-github` | experimental | Signed GitHub HTTP webhook adapter for the DeepSeek Harness webhook runtime | 保守保留：实验特性，未来桌面端/真实会话可能用；当前未安装进 Step18 运行时，插件无 import。 |
| `@deepseek-ai/dsh-client-ui-cordis` | extensions | Cordis dynamic-plugin definition card: the keyed cordis_define tool row with its run/stop switch | 保守保留：Cordis 动态插件/运行时检查，未来插件开发可能用；当前未组合。 |
| `@deepseek-ai/dsh-cordis-client-runner` | extensions | Browser half of dynamic dual-half plugin packages: event subscription, closure evaluation, guard facade, and … | 保守保留：Cordis 动态插件/运行时检查，未来插件开发可能用；当前未组合。 |
| `@deepseek-ai/dsh-cordis-host-runner` | extensions | Dynamic package definition registry, host-half sandbox lifecycle, and invoke handler table for model-mounted … | 保守保留：Cordis 动态插件/运行时检查，未来插件开发可能用；当前未组合。 |
| `@deepseek-ai/dsh-tool-cordis` | extensions | Read-only runtime API inspection for Harness plugin development | 保守保留：Cordis 动态插件/运行时检查，未来插件开发可能用；当前未组合。 |
| `@deepseek-ai/dsh-tool-str-replace-editor` | fs | Model-facing view, create, literal replace, and line insert tool over the Harness filesystem service | 保守保留：文件编辑工具，未来真实会话可能用；当前 Step18 禁用 fs 工具。 |
| `@deepseek-ai/dsh-host-directory-picker` | host | Abstract workspace-directory picking seam (ctx.directoryPicker) for the DeepSeek Harness web GUI host | 保守保留（Daniel）：Web/Desktop 桌面端宿主服务；当前 headless 不用。 |
| `@deepseek-ai/dsh-host-directory-picker-auto` | host | Adaptive chooser of the directory-picker seam: resolves the host situation at boot and mounts the native or b… | 保守保留（Daniel）：Web/Desktop 桌面端宿主服务；当前 headless 不用。 |
| `@deepseek-ai/dsh-host-directory-picker-browse` | host | In-app browsing backend of the directory-picker seam (listing/creation primitives over the host filesystem) | 保守保留（Daniel）：Web/Desktop 桌面端宿主服务；当前 headless 不用。 |
| `@deepseek-ai/dsh-host-directory-picker-native` | host | Native-OS-chooser backend of the directory-picker seam for the DeepSeek Harness web GUI host | 保守保留（Daniel）：Web/Desktop 桌面端宿主服务；当前 headless 不用。 |
| `@deepseek-ai/dsh-host-frontend-static` | host | SPA dist server for the Web shell: owns the webserver fallback seat, serving explicit index entries and stati… | 保守保留（Daniel）：Web/Desktop 桌面端宿主服务；当前 headless 不用。 |
| `@deepseek-ai/dsh-host-open-in-app` | host | Host half of open-in-app: resolved application catalog, icons, and the launch endpoint as three webServer rou… | 保守保留（Daniel）：Web/Desktop 桌面端宿主服务；当前 headless 不用。 |
| `@deepseek-ai/dsh-host-product-telemetry-otel` | host | Explicit product usage events exported through OpenTelemetry HTTP logs | 保守保留（Daniel）：Web/Desktop 桌面端宿主服务；当前 headless 不用。 |
| `@deepseek-ai/dsh-tool-ask-user` | interaction | Model-facing ask_user_question tool over the ctx.userQuestions seam | 保守保留：ask_user 工具，未来真实会话可能用；当前 Step18 禁用用户提问。 |
| `@deepseek-ai/dsh-lsp` | lsp | Abstract LSP capability seam (ctx.lsp) for the DeepSeek Harness — language-server provider registry keyed by … | 保守保留：LSP 编辑器能力，未来桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-lsp-stdio` | lsp | Generic stdio language-server provider for the DeepSeek Harness LSP capability seam (ctx.lsp) — spawns config… | 保守保留：LSP 编辑器能力，未来桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-tool-lsp` | lsp | Model-facing lsp tool over the DeepSeek Harness LSP capability seam (ctx.lsp) — one read-only tool with goToD… | 保守保留：LSP 编辑器能力，未来桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-mcp-client` | mcp | MCP client bridge: connects to MCP servers and registers their tools on ctx.tools | 保守保留：MCP 接入，未来真实会话可能用；当前未启用。 |
| `@deepseek-ai/dsh-agent-preset` | preset | Declare an Agent capability composition in Cordis YAML | 保守保留：Agent 预设/人设，未来真实会话可能用；当前 Step18 用固定 profile。 |
| `@deepseek-ai/dsh-persona` | preset | Composition-authored deployment persona section for the DeepSeek Harness | 保守保留：Agent 预设/人设，未来真实会话可能用；当前 Step18 用固定 profile。 |
| `@deepseek-ai/dsh-schedule` | schedule | Host-wide durable reminders with shared management and original-Session delivery | 保守保留：宿主定时提醒，未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-tool-schedule` | schedule | Model-facing reminder management tools (schedule_create, schedule_list, schedule_update, schedule_delete) ove… | 保守保留：宿主定时提醒，未来真实会话可能用；当前未组合。 |
| `@deepseek-ai/dsh-sdk-client` | sdk | TypeScript client SDK for driving a DeepSeek Harness runtime subprocess over stdio JSON-RPC: the DeepSeekHarn… | 保守保留：SDK 接入形态，未来桌面端/集成可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-sdk-jsonrpc-server` | sdk | Stdio JSON-RPC server plugin for out-of-process DeepSeek Harness SDK clients | 保守保留：SDK 接入形态，未来桌面端/集成可能用；当前 Step18 用 CLI/headless。 |
| `@deepseek-ai/dsh-sdk-protocol` | sdk | Shared wire protocol for the DeepSeek Harness SDK runtime: the newline-delimited JSON-RPC stdio transport and… | 保守保留：SDK 接入形态，未来桌面端/集成可能用；当前 Step18 用 CLI/headless。 |
| `@deepseek-ai/dsh-message-quotes` | session | Selected-text quotation and Markdown blockquote presentation | 保守保留（Daniel）：Web 侧会话统计/大纲，桌面端 UI 可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-session-stats` | session | Whole-log conversation counts and wall times projection (sessionStats) for the DeepSeek Harness | 保守保留（Daniel）：Web 侧会话统计/大纲，桌面端 UI 可能用；当前未组合。 |
| `@deepseek-ai/dsh-session-turn-outline` | session | Whole-log turn outline projection (turnOutline) for the DeepSeek Harness | 保守保留（Daniel）：Web 侧会话统计/大纲，桌面端 UI 可能用；当前未组合。 |
| `@deepseek-ai/dsh-session-log-export` | session-query | Web Session-log ZIP export and Session Markdown copy | 保守保留：非 AEH 当前路径，但未来桌面端/产品面可能用；当前未组合。 |
| `@deepseek-ai/dsh-tool-bash-persistent` | shell | Model-facing owner-scoped persistent Bash tool backed by the Harness PTY service | 保守保留：持久 shell 工具，未来真实会话可能用；当前 Step18 禁用 shell 工具。 |
| `@deepseek-ai/dsh-tool-pwsh-persistent` | shell | Model-facing owner-scoped persistent PowerShell tool backed by the Harness PTY service | 保守保留：持久 shell 工具，未来真实会话可能用；当前 Step18 禁用 shell 工具。 |
| `@deepseek-ai/dsh-skill-office` | skill | Bundled Word, PowerPoint, and Excel workflows and LibreOffice Kit operations | 保守保留：Office 技能/工作区依赖，教育文档场景可能用；当前未组合。 |
| `@deepseek-ai/dsh-tool-workspace-dependencies` | skill | The load_workspace_dependencies tool: absolute paths into a bundled Python, Node.js, and pnpm payload | 保守保留：Office 技能/工作区依赖，教育文档场景可能用；当前未组合。 |
| `@deepseek-ai/dsh-fs-ssh` | ssh | Filesystem provider over the shared POSIX SSH helper | 保守保留：SSH 远程能力，未来桌面端/远程场景可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-sandbox-ssh` | ssh | Remote POSIX sandbox argv provider over the shared SSH helper | 保守保留：SSH 远程能力，未来桌面端/远程场景可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-ssh` | ssh | Shared OpenSSH connection and versioned POSIX remote helper | 保守保留：SSH 远程能力，未来桌面端/远程场景可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-ssh-helper-runtime` | ssh | Private executable carrier for the POSIX SSH helper and managed workers | 保守保留：SSH 远程能力，未来桌面端/远程场景可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-subprocess-ssh` | ssh | Subprocess and terminal provider over the shared POSIX SSH helper | 保守保留：SSH 远程能力，未来桌面端/远程场景可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-storage-sqlite` | storage | SQLite storage backend (kv facet) for the DeepSeek Harness storage hub | 保守保留：SQLite 存储后端，未来可能用；当前 Step18 用 JSON。 |
| `@deepseek-ai/dsh-subagent-acp` | subagent | Out-of-process ACP subagent backend: drives a child agent in a spawned subprocess over the Agent Client Proto… | 保守保留：外部子代理后端，未来真实会话可能用；当前未安装且 Step18 禁用子代理。 |
| `@deepseek-ai/dsh-subagent-claude-code` | subagent | One-shot Claude Code subagent provider over the official Agent SDK | 保守保留：外部子代理后端，未来真实会话可能用；当前未安装且 Step18 禁用子代理。 |
| `@deepseek-ai/dsh-subagent-codex` | subagent | One-shot Codex subagent provider over the official app-server protocol | 保守保留：外部子代理后端，未来真实会话可能用；当前未安装且 Step18 禁用子代理。 |
| `@deepseek-ai/dsh-subagent-dsh-sdk` | subagent | Out-of-process SDK subagent backend: drives a child DeepSeek Harness runtime subprocess over stdio JSON-RPC t… | 保守保留：外部子代理后端，未来真实会话可能用；当前未安装且 Step18 禁用子代理。 |
| `@deepseek-ai/dsh-terminal` | terminal | Persistent PTY session seam for the DeepSeek Harness — owner-scoped ids, backend registry, interactive sends,… | 保守保留：持久 PTY，未来桌面端/真实会话可能用；当前 Step18 禁用终端工具。 |
| `@deepseek-ai/dsh-terminal-bash` | terminal | Persistent shell PTY backend over the DeepSeek Harness subprocess terminal primitive | 保守保留：持久 PTY，未来桌面端/真实会话可能用；当前 Step18 禁用终端工具。 |
| `@deepseek-ai/dsh-agent-loop-testkit` | test-support | Prerequisite mounting, production AgentLoop drivers, and Inbox stubs for tests | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-client-test-runtime` | test-support | Browser test runtimes: a jsdom slot bench with test-owned Session and Workspace doubles, and a whole-client t… | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-llm-mock-server` | test-support | Scriptable Messages HTTP/SSE fault server for LLM recovery tests | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-llm-replay` | test-support | Replay LLM plugin: short-circuits llm/stream with model chunks reconstructed from a recorded session JSONL (k… | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-loader-smoke` | test-support | Shared subprocess and direct-agent harness for keyless real-Loader example smoke tests | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-remote-mock` | test-support | Endpoint-named mock for Typert Remote traffic: unary answers and stream scripts per <namespace>/<method>, liv… | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-session-snapshot` | test-support | Session-log snapshot core with an ACP protocol adapter, expected-output normalization, and fixture invariants | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-tool-testkit` | test-support | Tool definition and execution fixtures for tests and benchmarks | 保守保留：上游测试/基准夹具，AEH 集成测试/回归未来可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-typert-generator` | typert | TypeScript project analyzer and model-driven Typert artifact generator | 保守保留：Typert 构建期生成器，未来升级/构建可能用；当前运行时不需要。 |
| `@deepseek-ai/dsh-native-command` | util | Host-native command and path-opening utilities with shell-free execution, cancellation, desktop detection, an… | 保守保留（Daniel）：Web/Desktop/插件市场辅助库，桌面端可能用；当前未组合。 |
| `@deepseek-ai/dsh-official-bundles` | util | Installation-owned lists of official dsh bundles (shipped profile templates, optional, on-demand, and retired… | 保守保留（Daniel）：Web/Desktop/插件市场辅助库，桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-plugin-detail` | util | Plugin detail documents: meta.detail or README selection, image paths, and local and npm CDN file sources | 保守保留（Daniel）：Web/Desktop/插件市场辅助库，桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-plugin-market-index` | util | Plugin market index format 1: JSON validation, relative icon resolution, and pinned install arguments | 保守保留（Daniel）：Web/Desktop/插件市场辅助库，桌面端可能用；当前未组合。 |
| `@deepseek-ai/dsh-util-file-drag` | util | Shared file drag names and native transfer requests | 保守保留（Daniel）：Web/Desktop/插件市场辅助库，桌面端可能用；当前未安装进 Step18 运行时。 |
| `@deepseek-ai/dsh-util-workspace-path` | util | Browser-safe Workspace path and display helpers | 保守保留（Daniel）：Web/Desktop/插件市场辅助库，桌面端可能用；当前未组合。 |
| `@deepseek-ai/dsh-web-search-exa` | web | Exa-backed search provider for the DeepSeek Harness web capability seam (ctx.web) | 保守保留：其他搜索 provider，未来可能用；当前未安装且 Step18 禁用 web 工具。 |
| `@deepseek-ai/dsh-web-search-perplexity` | web | Perplexity-backed search provider for the DeepSeek Harness web capability seam (ctx.web) | 保守保留：其他搜索 provider，未来可能用；当前未安装且 Step18 禁用 web 工具。 |
| `@deepseek-ai/dsh-command-compact` | compaction | Human-facing slash command for explicit session compaction | 保守保留（Daniel）：长会话上下文压缩，未来桌面版与真实会话都需要；当前 Step18 已启用/为 seam，插件无 import。 |
| `@deepseek-ai/dsh-compaction` | compaction | Abstract compaction service seam (ctx.compaction) for the DeepSeek Harness | 保守保留（Daniel）：长会话上下文压缩，未来桌面版与真实会话都需要；当前 Step18 已启用/为 seam，插件无 import。 |
| `@deepseek-ai/dsh-compaction-basic` | compaction | Token-meter-driven compaction policy and LLM summarization backend for the DeepSeek Harness | 保守保留（Daniel）：长会话上下文压缩，未来桌面版与真实会话都需要；当前 Step18 已启用/为 seam，插件无 import。 |
| `@deepseek-ai/dsh-compaction-image-offload` | compaction | Durable image offload for image-capable routes: replace over-budget request images with placeholders and retry | 保守保留（Daniel）：长会话上下文压缩，未来桌面版与真实会话都需要；当前 Step18 已启用/为 seam，插件无 import。 |
| `@deepseek-ai/dsh-compaction-tool-result-pruner` | compaction | Replay-safe model-free head/middle/tail pruning for tool-result surface nodes | 保守保留（Daniel）：长会话上下文压缩，未来桌面版与真实会话都需要；当前 Step18 已启用/为 seam，插件无 import。 |

### 6.6 无用（可删，2 个）

| 包 | 组 | 说明（package.json 原文摘要） | 可删理由 |
|---|---|---|---|
| `@deepseek-ai/dsh-agent-tool-presentation` | core | Deprecated tool presentation selector; use dsh-tool-executor-native or dsh-tool-executor-ptc directly | 自声明 `Deprecated` 且被 `dsh-tool-executor-*` 取代；Step 18 未组合；唯一直接引用是 `apps/cli/package.json`。 |
| `@deepseek-ai/dsh-client-ui-deepseek-model-label-1017` | client | Temporary 1017 release badge for official DeepSeek Flash model labels | 自声明 `Temporary` 发布徽章；`client` 组唯一例外；引用点是 `packages/bundle/web-app` 的 `cordis.patch.yml` 与 `package.json`。若 Daniel 要桌面端保留官方徽章，移回保留即可（可删集降为 1）。 |

### 6.7 apps（5 个）

| app | 包名 | 说明（package.json description） | 分类 | 理由 |
|---|---|---|---|---|
| `apps/cli` | `@deepseek-ai/dsh` | dsh CLI：profile 启动、插件管理、配置检查；`bin.dsh=lib/bin.js`。 | **必需（Step18）** | Step 18 隔离运行时安装并由 `dsh --profile aeh-e2e` 启动；`step18/runtime/node_modules/@deepseek-ai/dsh`。 |
| `apps/desktop` | `@deepseek-ai/dsh-desktop` | Electron 桌面壳，内嵌 dsh 运行时与外部插件。 | **保留（未来桌面版）** | Daniel：AEH 未来要做桌面版软件；桌面壳是桌面版入口，删了等于未来重造。 |
| `apps/desktop-host` | `@deepseek-ai/dsh-desktop-host` | Electron 的私有 Node 模式宿主进程。 | **保留（未来桌面版）** | Daniel：桌面宿主进程与 `apps/desktop` 配套，未来桌面版需要。 |
| `apps/plugin-market-generator` | `@deepseek-ai/dsh-plugin-market-generator` | 从 npm 包/Git 仓库列表生成插件市场索引的参考工具。 | **保留（产品面）** | 保守原则：桌面版若带插件市场/发布流程会用到；当前不分发不等于未来不用。 |
| `apps/web` | `@deepseek-ai/dsh-web-frontend` | Web 前端入口：vite 构建 `@deepseek-ai/dsh-client-web`，dist 由 `dsh web` 提供。 | **保留（桌面版前端可复用）** | Daniel：Web 前端与桌面端共用 `client`/`host` 栈，按“桌面版可能复用”保留。 |

## 7. 删除建议（保守版）

> 与上一版相比，**删除集由 219 个大幅缩小到 2 个**。任何“有用或未来可能用”的包都不再进入
> 删除建议；桌面端、上下文压缩、实验特性、产品面与全部传递依赖都不删。以下顺序只在
> **fork/裁剪副本** 上执行；运行中的 dsh 一律不动。

### 7.1 五条原则

1. **不在运行中的 dsh 上删**：不碰 `~/.dsh/`、npx 安装、`step18/runtime`、正在跑本任务的
   harness；所有删除只在一个 **fork/裁剪副本** 上做。
2. **保守删除**：只有“完全无用且未来也不可能用上”的包才列为可删；拿不准的一律保留或待确认。
   当前符合该口径的只有自声明 `Deprecated`/`Temporary` 的 2 个包。
3. **先删引用者，再删被引用者**：先移除删除目标在 `package.json` 与 profile patch 里的引用，
   再删包；否则 `pnpm install` 会因 workspace 依赖缺失直接失败。
4. **一阶段一提交一验证**：每个阶段结束都跑 §8 的三件套（隔离实例加载插件 + loader 证据 +
   Step 18 合成会话），失败就回滚该阶段。
5. **保留证据**：保存 `dump-config`、loader 输出、`summary.json` 与 `git diff --stat`。

### 7.2 建议顺序（删除集 2 个）

| 阶段 | 删什么 | 为什么在这个位置 | 验证重点 |
|---|---|---|---|
| **P0 基线** | 不删 | 固定 363/368/306/86/5 与 Step 18 `summary.json` 的哈希 | 记录基线，确认隔离 |
| **P1 自声明死包（本版唯一推荐删除阶段）** | `dsh-agent-tool-presentation`、`dsh-client-ui-deepseek-model-label-1017`（2 个） | 唯一两个自声明“弃用/临时”的包，未来无使用路径；先删引用者（`apps/cli/package.json`、`packages/bundle/web-app` 的 `package.json`+`cordis.patch.yml`）再删包 | §8 三件套不变：`dump-config` 只少对应条目；loader 仍挂 6 个工具；Step 18 合成会话仍通过 |
| **P2 待确认（不删，仅决策）** | 0 个 | §5.4 的 20 个保留待 Daniel 决定是否启用；不删除 | 若决定启用，按单包提交单独验证 |
| **P3 其余保留/传递** | 0 个 | 保守原则：桌面端、上下文压缩、实验特性、产品面与传递依赖都不删；真要收缩应先换 `dsh-base` 再重算闭包 | 不适用 |

### 7.3 为什么不再有大规模删除

- **桌面端**：`apps/desktop`、`apps/desktop-host`、`client`/`host`/`api` 与 `apps/web` 是桌面版
  资产，删了要重造（Daniel 明确要求保留）；
- **上下文压缩**：`compaction` 5 个是长会话必需，删除会直接掉能力；
- **实验/产品面**：`experimental`、SDK、ACP、SSH、LSP、浏览器/桌面自动化、Office、插件市场等
  都可能在未来版本用上；
- **传递依赖**：仍必须先换 bundle，不能逐包删；本版不把传递依赖列为删除对象。

### 7.4 绝对不要删的

- §5.3 的 15 个 workspace 包 + 2 个外部包（cordis、schemastery）；
- §5.5 的“硬约束环”约 20 个（dsh-brand、dsh-timeout、dsh-util-crypto、dsh-typert-protocol、
  dsh-scope、dsh-sandbox、dsh-sandbox-policy、dsh-working-directory、dsh-ptc-runtime、
  dsh-user-approval 等）；
- **§5.6 的全部“保留”（222 个）与 §5.4 的“待确认”（20 个）**；
- 插件 `package.json` 的 17 个 `@deepseek-ai/*` 声明，除非你同时验证了 peer 解析与
  `npm ls` 仍然干净；
- `references/`、`spec/`、`step18/evidence/`（证据是只读基线）。

## 8. 删完如何验证

### 8.1 三件套（缺一不可）

#### A. 隔离实例加载插件

目的：证明裁剪后的 profile 仍能把 AEH 入口 `insert` 进去，且没有缺失插件。

```bash
# 只在 AEH 的隔离 home 下，不碰 ~/.dsh
mkdir -p step18/home-verify
cp -r step18/home/profiles step18/home-verify/
DSH_HOME="$PWD/step18/home-verify" \
  step18/runtime/node_modules/.bin/dsh --profile aeh-e2e --dump-config
```

期望：
- `dump-config` 中出现 `aeh-education-e2e` 与 `name: file:///.../dsh-plugin/e2e/aeh-e2e-entry.ts`；
- 没有 `cannot find plugin` / `unknown id` / peer 解析错误；
- 组合条目数与基线 99 的差异只来自你本阶段删掉的条目。

#### B. loader 证据

目的：证明 `cordis` + `dsh-tools` + `dsh-system-prompt` + `cordis-plugin-loader` +
`dsh-tool-call-timeout-policy` 仍能把 6 个工具挂上、校验 schema、取消/超时、卸载归零。

```bash
cd dsh-plugin
node scripts/loader-evidence.mjs
```

期望输出（与 `docs/dsh-integration.md` §9 的记录一致）：
- `mounted tools` 恰好 6 个：`aeh_check_curriculum`、`aeh_generate_report`、
  `aeh_prepare_intervention`、`aeh_schedule_review`、`aeh_select_probe`、`aeh_update_hypotheses`；
- `invalid-argument code: INVALID_ARGS`；
- `cancellation code: ABORTED_BEFORE_DISPATCH`；
- `timeout code: TOOL_TIMEOUT`；
- `tools after unload: 0`；
- 退出码 0。

如果要验证“裁剪后的 step18 运行时”而不是 `dsh-plugin/node_modules`，在一个临时目录里
复制 `src`/`scripts`/`package.json`，把 `node_modules` 软链到裁剪后的
`step18/runtime/node_modules`，再跑同一个脚本（ESM 的 bare import 会按脚本所在目录解析）：

```bash
tmp=$(mktemp -d)
cp -r dsh-plugin/src dsh-plugin/scripts dsh-plugin/package.json "$tmp/"
ln -s "$PWD/step18/runtime/node_modules" "$tmp/node_modules"
node "$tmp/scripts/loader-evidence.mjs"
```

#### C. Step 18 合成会话

目的：证明真实 dsh 运行时 + 真实 profile + 真实 loader + 6 个工具仍能跑完一次合成会话。

```bash
python3 step18/run-e2e.py --dry-run          # 先看组合结果
python3 step18/run-e2e.py --run-id "verify-<阶段>"
```

期望（对照基线 `20261027T110556Z`）：
- `exit-code.txt` = `0`；
- `summary.json` 的 `events` = 39，`tool_calls` = 6；
- 0 个错误事件；
- 门禁：`item.fraction.add.001` allowed=true；`item.fraction.multiply.001` allowed=false，
  reason `kcs_not_allowed:kc.fraction.multiply`；
- 复习：`nextIntervalDays` = 3.2，`stabilityDays` = 3.2，`difficultyState` = 4.8；
- 报告：attempts 4、independent correct 3、hints 1、minutes 10、independent accuracy 0.75。

任何一项偏离，先回滚本阶段，再二分定位到具体包。

### 8.2 每个阶段的附加检查

```bash
# 1) 依赖图完整（缺 workspace 包会在这里失败）
pnpm install --frozen-lockfile

# 2) 类型与测试（按仓库根 package.json 的 scripts 执行）
pnpm -r exec tsc --noEmit
pnpm -r test

# 3) 没有残留引用（本版只删 2 个自声明死包）
grep -R "dsh-agent-tool-presentation\|dsh-client-ui-deepseek-model-label-1017" \
  --include=package.json --include=*.yml packages apps
```

### 8.3 要留下的证据

- 每个阶段的 `dump-config.txt`（前后 diff）；
- 每个阶段的 loader 输出（stdout 全文）；
- 每个阶段的 `summary.json` / `summary.md` / `exit-code.txt`；
- `pnpm-lock.yaml` 的 diff 与 `git diff --stat`；
- 一份“删了哪些包、为什么、对应哪个分类”的清单（可直接从 §6 勾选）。

### 8.4 回滚

- 每个阶段一个 commit；失败时 `git revert` 该 commit，不要手工反向删；
- 如果已经改了 lockfile，先恢复 `pnpm-lock.yaml` 与相关 `package.json`，再 `pnpm install`；
- 回滚后重跑 §8.1 三件套，确认回到基线。

## 9. 风险、未声称与待确认

1. **只读静态分类**：没有做“删包后运行”的实验。本次按 Daniel 保守原则重判后，可删集仅
   **2** 个，其余“保留/待确认”都是“有理由不删”的判断，不是运行证明。
2. **分类是相对 AEH 当前与未来桌面版**：不是对 dsh 的价值判断；桌面/Web/浏览器/Office 等对
   dsh 用户是正式能力，对 AEH 也是保留项，不能因为“当前 headless 不用”就归为无用。
3. **12 个声明未 import 的包**：无法只凭源码判断作者意图（peer 锁定、历史遗留、还是预留），
   已在 §3.2 标为待确认/冗余；删声明前必须跑 `npm ls`/`pnpm install` 与 loader 证据。
4. **Step 18 覆盖面**：只验证了一个合成会话、一个模型（Sidrune `deepseek-v4-1-flash`）、
   一个 profile；没有多进程/崩溃恢复/配额/真实身份/LMS。
5. **peer 解析**：`dsh-tools`/`dsh-llm` 有较多 peerDependencies；pnpm 严格 peer 下，删包可能是
   “安装期失败”而不是“运行时报错”。这也是 P1 只删自声明死包的原因。
6. **许可证/第三方告知**：删包后 `THIRD_PARTY_NOTICES.md` 可能需要同步更新；本文未展开。
7. **数字口径**：363 是 `packages/*/*` 的 workspace 包；如果把 9 个测试夹具/模板也算进去，
   `find` 会得到 372。本文统一用 363，并在 §2.2 注明差异。
8. **版本时效**：分类相对 `0.2.1-rc.3` + Step 18 profile；源码克隆里有些包是发布后才有的
   重构/实验（例如 `dsh-tool-executor-native`、`dsh-tool-executor-ptc`、
   `dsh-experimental-auto-review`、`dsh-official-bundles`），它们不在本次安装的 306 个条目里；
   升级 dsh 版本后，本文的分类需要按新的 `dump-config` 重新核对。
9. **2 个可删项都有引用者**：`dsh-agent-tool-presentation` 被 `apps/cli` 直接依赖，
   `dsh-client-ui-deepseek-model-label-1017` 被 `packages/bundle/web-app` 引用；执行 P1 时必须先删
   引用再删包，并重跑 §8 三件套。

## 10. 数字对账表

| 数字 | 来源 / 复现命令 |
|---:|---|
| 363 | `find packages -maxdepth 3 -name package.json | wc -l`（`packages/*/*/package.json`） |
| 52 | `ls -d packages/*/ | wc -l` |
| 5 | `ls apps | wc -l` |
| 368 | 363 + 5 |
| 306 | `ls step18/runtime/node_modules/@deepseek-ai | wc -l` |
| 293 | 306 个安装项中与 `packages/` 363 个包同名的数量 |
| 86 | `python3 -c "import json;print(len(json.load(open('step18/runtime/node_modules/@deepseek-ai/dsh/package.json'))['dependencies']))"` |
| 83 | 上述 86 个里以 `@deepseek-ai/` 开头的数量 |
| 5 | `grep -rhoE "from ['\"]@deepseek-ai/[^'\"]+" dsh-plugin/src dsh-plugin/e2e | sort -u | wc -l` |
| 17 | `dsh-plugin/package.json` 的 `dependencies` 里 `@deepseek-ai/*` 的数量（+ `zod` = 18） |
| 99 | `grep -cE '^- id: ' step18/evidence/20261027T110556Z/dump-config.txt` |
| 76 / 22 | 上述 99 条中未 disabled / 显式 `disabled: true` 的 dsh 条目数 |
| 75 / 20 | 上述启用 / disabled 的唯一包名数 |
| 15 / 222 / 109 / 20 / 2 | §5.2 的分类计数（必需/保留/传递/待确认/无用）；合计 368 |

---

**最终声明**：本次只修订了 `docs/dsh-function-inventory.md` 一个文件；没有删除任何文件、包或
依赖声明，没有修改任何代码，没有修改 `~/.dsh/`、`~/workspace/deepseek-harness`、npx 安装的
dsh、`step18/runtime`、`references/`、`spec/`，也没有把 AEH 插件加载进正在执行本任务的
harness 会话。**运行用 dsh（正在执行本任务的 harness）自始至终没有被改动；本次没有任何删除。**
