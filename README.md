# bootstrap-project

面向 AI 协作的项目初始化与文档体检 skill。创建 Git 仓库与协作文档、配置 `AGENTS.md` 自动入口，并只读检查文档缺漏和结构变化。

Project scaffolding and documentation checks for AI-assisted development.

脚本负责确定性的文件和 Git 操作；Agent 根据项目与对话补齐内容。它生成项目协作文档，应用代码仍由所选语言或框架的工具创建。独立的一次性 HTML 交接/审计报告已拆分为同级 skill `project-report`。

## 环境要求

- Python 3.10 或更高版本，运行脚本只用标准库。
- 初始化、检查和提交需要 Git。
- 模板默认中文。Agent 可按用户指定的语言填写和翻译，文档检查支持中英文整理日期字段。
- 运行时不访问网络。测试额外需要 [PyYAML](tests/requirements.txt)。

## 安装和卸载

下载或克隆本项目，将完整目录命名为 `bootstrap-project`，放进所用 Agent 客户端的 skills 目录。具体搜索路径和重新加载方式以客户端文档为准。

运行 skill 所需的文件是 `SKILL.md`、`scripts/` 和 `references/`；分发时同时保留 `LICENSE`。不要只复制 `SKILL.md`。

安装后，可以这样发出请求：

```text
用 bootstrap-project 在 ./demo 创建一个小型 Python 项目所需的协作文档。
用途是汇总本地 CSV，运行命令是 python main.py；使用 lite 模式。
```

更新时替换安装目录中的发布文件，并保留需要的个人修改。卸载时删除安装的 `bootstrap-project` 目录；以前生成到各项目中的文档由对应项目继续维护。

## 直接使用脚本

在本项目目录下运行以下命令。将目标路径替换为自己的项目目录；按环境使用 `python`、`python3` 或 Windows 的 `py`。

```bash
python scripts/bootstrap_project.py "../demo-project" --dry-run
python scripts/bootstrap_project.py "../demo-project"
python scripts/bootstrap_project.py "../demo-project" --check --json
```

如果项目同时使用框架脚手架（如 `npm create`、`cargo new`、`uv init`），应**先运行框架工具**再运行 `bootstrap-project`，这样框架生成的 `.gitignore` 和目录结构不会被提前占坑。

第一次默认创建 `.git/`（除非目标位于父级 Git 仓库中）、`PROJECT_CONTEXT.md`、`PLANS.md`、`README.md`、`AGENTS.md`（若已存在 `GEMINI.md` 或 `CLAUDE.md` 则不额外创建）和 `.gitignore`。重复运行会跳过已有的普通文件。

| 模式 / 参数 | 用法 | 产物或行为 |
| --- | --- | --- |
| 默认 | `TARGET` | Git、三份协作文档、`AGENTS.md`（按需）和 `.gitignore`，使用简短模板 |
| 详细 | `TARGET --full` | 相同文件，包含字段示例与更详细的协作提示 |
| 轻量 | `TARGET --lite` | Git、`README.md` 和 `.gitignore` |
| 检查 | `TARGET --check` | 只读检查，不自动修复 |
| `--nested-git` | `TARGET --nested-git` | 仅初始化可用；即使目标在父仓库子目录内也执行 `git init` |
| `--agents-md` | `TARGET --agents-md` | 仅初始化且非 `--lite` 可用；向缺少文档指引的已有入口文件追加短指引 |
| `--commit` | `TARGET --commit` | 仅初始化可用；立即提交本次新建的模板文件 |

长参数必须完整拼写，不接受缩写。`--dry-run` 预览操作，不创建目录、写文件或提交。`--json` 输出一个 UTF-8 JSON 对象，包含操作、创建/跳过/冲突路径、Git 与 `agents` 状态、检查项、错误和退出码；正常执行时 `created` 只包含成功创建的文件，预览模式下表示计划创建的文件。

**模板生成后需要填写。** 直接执行脚本会留下“待补充”，因此立即执行默认检查通常会失败。通过 Agent 使用时，应根据实际信息补齐内容，再运行检查；未知信息保留并说明。

## 协作文档与入口分工

| 文档 | 内容与维护方式 |
| --- | --- |
| `AGENTS.md` | Agent 客户端自动加载的入口；指向 `PROJECT_CONTEXT.md`、`PLANS.md` 和 `README.md` |
| `PLANS.md` | 当前任务保留编号、状态、范围与验收、验证与下一步；自带精简规则摘要（约 0.8 KB），未结束任务不随会话或任务切换移入历史 |
| `PROJECT_CONTEXT.md` | 核实后的稳定事实、实际结构、开发与测试约定；事实变化时修订，长说明保留结论和链接 |
| `README.md` | 项目简介、通用安装与启动命令、文档导航；上下文链接运行说明，减少重复维护 |

- 新目录在默认/`--full` 模式下会自动生成 `AGENTS.md`；若项目已使用 `GEMINI.md` 或 `CLAUDE.md`，则不再生成第二份 `AGENTS.md`。
- 若既有的 `AGENTS.md` / `GEMINI.md` / `CLAUDE.md` 尚未提及 `PROJECT_CONTEXT.md`，脚本会保留原文件并输出 `hint:`；经用户确认后可加 `--agents-md` 在末尾安全追加一段 `<!-- bootstrap-project: entry -->` 指引。
- 完整的计划编写、审阅及 `docs/plans/archive-YYYY.md` 归档规范集中维护在 [项目文档约定](references/project-docs.md)，不再全文复制到每个项目仓库中。

## 文档检查

| 级别 | 检查内容 |
| --- | --- |
| `basic` | 路径类型、文件可读性与 UTF-8 编码、Git 仓库有效性（含父仓库识别 `parent_git`） |
| `standard`（默认） | basic，加 Markdown 非空、占位符、整理日期、顶层结构变化、PLANS.md 体积、Agent 入口指引和 HEAD 检查 |
| `strict` | standard，加全部文档齐全、结构树可解析、已有提交、工作区干净（含未跟踪文件，不受 Git 显示配置影响）；所有警告也会阻止通过 |

在 `standard` 下区分阻塞项（`issue`，退出码 `1`）和警告（`warning`，汇总报告但退出码仍为 `0`）：

- **issue（阻塞）：** 路径冲突、缺失必需文件（lite 布局除外）、无效 UTF-8/不可读、Markdown 为空、含占位符、整理日期缺失/无法解析/为未来日期、`PLANS.md` 超出体积上限、本地和父级均无 Git 仓库、`.git` 损坏。
- **warning（提醒，仅 strict 阻塞）：** 整理日期超过时效（`stale_context`）、顶层结构偏差（`structure_drift`）、缺少结构树（`structure_missing`）、缺少指向 `PROJECT_CONTEXT.md` 的入口文件（`agent_entry_missing`）、仓库尚无提交（`no_head`）。
- **info：** 目标位于父级 Git 仓库子目录中时，跳过无本地仓库告警并报告 `parent_git`（同时跳过 HEAD 与工作区状态检查）。

UTF-8 BOM 可以使用，空的 `.gitignore` 也有效。无效编码会明确报错，不会丢弃字节后继续判定文档健康。

整理日期支持 `最后整理：YYYY-MM-DD` 或 `Last reviewed: YYYY-MM-DD`，未来日期会报错。结构检查读取第一个含树形条目的 `text` 代码块，只比较顶层名称；常见构建与依赖目录可以省略。

默认整理日期上限为 90 天，可按项目节奏调整。`0` 关闭过期限制，但仍要求日期可解析且不在未来；只有实际核实内容后才应更新整理日期。占位符按大小写敏感的字面文本匹配，可以追加多个值；默认“待补充”始终保留。

`PLANS.md` 默认上限 16 KB，超出时报告 `plans_growth`，提示按 [项目文档约定](references/project-docs.md) 归档较早的已结束记录。脚本不会自动归档。`--plans-max-kb N` 调整上限，`0` 关闭体积限制。

```bash
python scripts/bootstrap_project.py "../demo-project" --check --stale-days 30
python scripts/bootstrap_project.py "../demo-project" --check --plans-max-kb 64
python scripts/bootstrap_project.py "../demo-project" --check --placeholder TBD --placeholder TODO --json
python scripts/bootstrap_project.py "../demo-project" --check --check-level strict --stale-days 0
```

`--stale-days`、`--plans-max-kb` 和 `--placeholder` 只适用于检查模式；basic 不执行内容、日期或体积检查。检查结果的 JSON 会记录实际使用的 `stale_days`、`plans_max_kb` 和 `placeholders`。

退出码：`0` 通过（可能含 warning），`1` 操作失败或存在阻塞项，`2` 参数错误。检查通过只代表满足自动检查项；五条历史的数量限制、任务状态、验收证据、运行命令和链接需要另行审阅。

## Git 与已有文件

已有普通文件会保留；文档路径被目录或符号链接占用时报告冲突。Git worktree 和 submodule 的 `.git` 文件可以正常使用，损坏的 `.git` 不会被自动修复。

若目标目录没有自己的 `.git`，但位于父级 Git 仓库内（如 monorepo 子目录），脚本默认**跳过 `git init`**，避免意外产生嵌套仓库；确实需要独立嵌套仓库时，传入 `--nested-git`。如果在父仓库子目录内不带 `--nested-git` 请求 `--commit`，脚本会拒绝提交并报错，避免误向父仓库创建提交。

Git 操作固定使用目标的 `.git`，隔离继承的仓库、工作区、索引、对象目录及单次调用配置覆盖。用户/系统 Git 配置和作者、提交者身份仍然生效。检查关闭 Git 的可选锁，避免刷新索引。

默认不提交。`--commit` 会立即提交本次新建的模板文件，并保留其他已暂存改动；Git hook、身份或签名失败会报告为错误。若需要提交填写完成的文档，应在填写和检查后单独提交目标文件；重新运行 `--commit` 不会提交之前已存在文件的后续编辑。

如果 Git 缺失或初始化失败，脚本仍尝试生成文档，并以非零退出码报告 Git 错误。

`.gitignore` 在首次创建时检测已有技术栈，后续不会覆盖用户的忽略规则。通用 `dist/`、`build/` 等建议保留为注释；PHP 的 `vendor/`、Ruby 的 `/vendor/bundle/`、.NET 的 `bin/` 和 `obj/` 使用对应技术栈的常规忽略规则，需要按项目实际目录复核。

## 升级 lite 项目

对原目录重新运行默认模式，会补上缺失的 `PROJECT_CONTEXT.md`、`PLANS.md` 和 `AGENTS.md`（若项目尚未有 `GEMINI.md` / `CLAUDE.md`）。原 `README.md` 和 `.gitignore` 保留；填写新文档后，还需在 `README.md` 的文档入口加入链接。

## HTML 报告

一次性离线 HTML 交接、审计与排查报告功能已独立为同级 skill `project-report`（位于相邻 skills 目录 `project-report/`），不在本脚本内生成。

## 开发和验证

```bash
python -m pip install -r tests/requirements.txt
python -B -m unittest discover -s tests -v
```

测试使用临时目录，覆盖创建与重复运行、文件冲突、Git worktree、外部 Git 环境干扰、父仓库子目录防护、`AGENTS.md` 入口生成与追加、暂存区保护、只读检查、编码与 JSON 契约。

[GitHub Actions 配置](.github/workflows/ci.yml)覆盖 Linux、Windows、macOS，使用 Python 3.10、3.12、3.14。涉及 Agent 指令的改动，还应执行 [实际使用场景](tests/agent-scenarios.md)，验证触发、内容填写和用户意图的保持；脚本测试不能替代这一步。

## 许可证

代码和文档采用 [MIT License](LICENSE)。生成器不会替目标项目选择或写入许可证。
