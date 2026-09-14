# bootstrap-project

面向 AI 协作的项目初始化与文档体检 skill。创建 Git 仓库与协作文档、检查文档缺漏和结构变化，并生成离线 HTML 交接报告。

Project scaffolding and documentation checks for AI-assisted development, with an optional offline report template.

脚本负责确定性的文件和 Git 操作；Agent 根据项目与对话补齐内容。它生成项目协作文档，应用代码仍由所选语言或框架的工具创建。

## 环境要求

- Python 3.10 或更高版本，运行脚本只用标准库。
- 初始化、检查和提交需要 Git；生成 HTML 报告不需要 Git。
- 模板默认中文。Agent 可按用户指定的语言填写和翻译，文档检查支持中英文整理日期字段。
- 运行时不访问网络。测试额外需要 [PyYAML](tests/requirements.txt)。

## 安装和卸载

下载或克隆本项目，将完整目录命名为 `bootstrap-project`，放进所用 Agent 客户端的 skills 目录。具体搜索路径和重新加载方式以客户端文档为准。

运行 skill 所需的文件是 `SKILL.md`、`scripts/`、`assets/` 和 `references/`；分发时同时保留 `LICENSE`。不要只复制 `SKILL.md`。

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

第一次默认创建 `.git/`、`PROJECT_CONTEXT.md`、`PLANS.md`、`README.md` 和 `.gitignore`。重复运行会跳过已有的普通文件。

| 模式 | 用法 | 产物或行为 |
| --- | --- | --- |
| 默认 | `TARGET` | Git 和四个基础文件，使用简短模板 |
| 详细 | `TARGET --full` | 相同文件，包含更详细的协作提示 |
| 轻量 | `TARGET --lite` | Git、README 和 .gitignore |
| 检查 | `TARGET --check` | 只读检查，不自动修复 |
| 报告 | `TARGET --report handover` | `docs/reports/YYYY-MM-DD-handover.html` |

初始化、检查、报告互斥；`--full`、`--lite`、`--commit` 只适用于初始化。

`--dry-run` 预览操作，不创建目录、写文件或提交。`--json` 输出一个 UTF-8 JSON 对象，包含操作、创建/跳过/冲突路径、检查项、错误和退出码；预览模式的 `created` 表示计划创建的文件。

**模板生成后需要填写。** 直接执行脚本会留下“待补充”，因此立即执行默认检查通常会失败。通过 Agent 使用时，应根据实际信息补齐内容，再运行检查；未知信息保留并说明。

## 文档检查

| 级别 | 检查内容 |
| --- | --- |
| `basic` | 路径类型、文件可读性与 UTF-8 编码、Git 仓库有效性 |
| `standard`（默认） | basic，加 Markdown 非空、占位符、整理日期、顶层结构变化和 HEAD 检查 |
| `strict` | standard，加全部文档齐全、结构树可解析、已有提交、工作区干净；警告也会阻止通过 |

UTF-8 BOM 可以使用，空的 `.gitignore` 也有效。无效编码会明确报错，不会丢弃字节后继续判定文档健康。有效但尚未提交的仓库在 standard 下产生警告，在 strict 下产生问题。

整理日期支持 `最后整理：YYYY-MM-DD` 或 `Last reviewed: YYYY-MM-DD`。结构检查读取第一个含树形条目的 `text` 代码块，只比较顶层名称；常见构建与依赖目录可以省略。

默认整理日期上限为 30 天，可按项目节奏调整。`0` 关闭过期限制，但仍要求日期可解析。占位符按大小写敏感的字面文本匹配，可以追加多个值；默认“待补充”始终保留。

```bash
python scripts/bootstrap_project.py "../demo-project" --check --stale-days 90
python scripts/bootstrap_project.py "../demo-project" --check --placeholder TBD --placeholder TODO --json
python scripts/bootstrap_project.py "../demo-project" --check --check-level strict --stale-days 0
```

`--stale-days` 和 `--placeholder` 只适用于检查模式；basic 不执行内容或日期检查。检查结果的 JSON 会记录实际使用的 `stale_days` 和 `placeholders`。

退出码：`0` 通过，`1` 操作失败或存在阻塞项，`2` 参数错误。检查通过只代表满足这些规则；内容是否准确、运行命令是否可用，需要另外验证。

## Git 与已有文件

已有普通文件会保留；文档路径被目录或符号链接占用时报告冲突。Git worktree 和 submodule 的 `.git` 文件可以正常使用，损坏的 `.git` 不会被自动修复。目标目录没有自己的 `.git` 时会创建独立仓库，即使父目录已经是仓库。

Git 操作固定使用目标的 `.git`，隔离继承的仓库、工作区、索引、对象目录及单次调用配置覆盖。用户/系统 Git 配置和作者、提交者身份仍然生效。检查关闭 Git 的可选锁，避免刷新索引。

默认不提交。`--commit` 会立即提交本次新建的模板文件，并保留其他已暂存改动；Git hook、身份或签名失败会报告为错误。若需要提交填写完成的文档，应在填写和检查后单独提交目标文件；重新运行 `--commit` 不会提交之前已存在文件的后续编辑。

如果 Git 缺失或初始化失败，脚本仍尝试生成文档，并以非零退出码报告 Git 错误。

`.gitignore` 在首次创建时检测已有技术栈，后续不会覆盖用户的忽略规则。通用 `dist/`、`build/` 等建议保留为注释；PHP 的 `vendor/`、Ruby 的 `/vendor/bundle/`、.NET 的 `bin/` 和 `obj/` 使用对应技术栈的常规忽略规则，需要按项目实际目录复核。

## 升级 lite 项目

对原目录重新运行默认模式，会补上缺失的 `PROJECT_CONTEXT.md` 和 `PLANS.md`。原 README 和 .gitignore 保留；填写新文档后，还需在 README 的文档入口加入链接。

## HTML 报告

报告是带日期的历史快照，使用系统字体，随系统偏好切换深浅色，离线即可打开。生成后仍需填写内容、删除不适用的章节并检查成品。

```bash
python scripts/bootstrap_project.py "../demo-project" --report deploy-handover
```

同日同名报告会跳过；需要新的快照时使用新的 slug。对当前目录指定名称时使用 `--report=deploy-handover`。详细步骤见 [报告工作流](references/reports.md)。

## 开发和验证

```bash
python -m pip install -r tests/requirements.txt
python -B -m unittest discover -s tests -v
```

测试使用临时目录，覆盖创建与重复运行、文件冲突、Git worktree、外部 Git 环境干扰、暂存区保护、只读检查、编码、JSON 和报告生成。

[GitHub Actions 配置](.github/workflows/ci.yml)覆盖 Linux、Windows、macOS，使用 Python 3.10、3.12、3.14。涉及 Agent 指令的改动，还应执行 [实际使用场景](tests/agent-scenarios.md)，验证触发、内容填写和用户意图的保持；脚本测试不能替代这一步。

## 许可证

代码、文档和随附 HTML 模板采用 [MIT License](LICENSE)。生成器不会替目标项目选择或写入许可证。
