# Agent 使用场景

修改 SKILL.md 或报告工作流时，在已加载此 skill 的客户端中验证以下场景。
每个场景使用独立临时目录；自动化脚本测试不能证明 Agent 已正确执行这些步骤。
记录使用的客户端、模型、实际命令、生成文件和检查结果。

## 新建项目并填写已知信息

请求：

> 用 bootstrap-project 初始化这个空目录。项目叫 csv-summary，用 Python 标准库汇总本地 CSV，
> 入口计划为 main.py，运行命令是 python main.py。不需要提交。

观察：默认文档和 Git 仓库创建成功；名称、用途、语言从请求中填写；计划中的入口和命令标明尚未实现；
未知信息不被编造；检查结果如实报告；没有产生提交。

## 保留既有内容并从 lite 升级

准备：先用 CLI 创建 lite 项目，填写 README，添加一个代码文件并记录它们的内容。

请求：

> 项目需要完整协作文档了，帮我从 lite 升级。保留 README 现有的运行说明。

观察：补齐 context 和 plans，README 增补文档入口；原运行说明、源文件和 .gitignore 保留。
新文档依据现有代码填写，随后执行检查。

## 只读检查

准备：一份含占位符和过期整理日期的项目，记录文件内容及 Git 索引的字节和修改时间。

请求：

> 检查这个项目的文档，日期上限用 90 天，把 TBD 也算占位符。只报告问题。

观察：使用 `--check --stale-days 90 --placeholder TBD`，不修改文件或刷新索引，
分别报告占位符、日期和结构问题，不把脚本检查描述为业务正确性验证。

## 按指定语言填写

请求：

> Use bootstrap-project to initialize a small Python CLI project. Write the documentation in English.
> Its purpose is to summarize local CSV files. Do not commit anything.

观察：Agent 填写的文档使用英文；需要整理日期时保留可解析的 `Last reviewed: YYYY-MM-DD` 字段；
结构树与实际文件一致；未知信息明确标记并纳入检查；没有提交。

## 交接报告与历史快照

准备：项目中保留一份已有的同日同名报告，并记录内容。

请求：

> 按当前代码和本次验证结果生成新的交接报告，保留已有报告。

观察：同名冲突时换用新的 slug；新报告使用真实内容、删除未用章节、说明未验证部分；
保留日期和既有报告；浏览器打开后不依赖外部字体或网络资源。
