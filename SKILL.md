---
name: bootstrap-project
description: >-
  Set up collaboration docs for a new or existing project (README.md,
  PROJECT_CONTEXT.md, PLANS.md, AGENTS.md entry, stack-aware .gitignore, git
  init), or health-check those docs for placeholders and drift. Use for
  "初始化项目", "新建项目脚手架", "补齐项目文档", "检查项目文档". Preserves existing files.
  Not for HTML reports (use project-report) or for generating application code.
license: MIT
---

# Bootstrap Project

A bundled script creates missing starter docs; you then fill them from what is actually known. It never overwrites existing files.

## 1. Pick a mode

| Situation | Mode | Creates |
| --- | --- | --- |
| Small project, one-off script, solo short-lived work | `--lite` | `README.md`, `.gitignore` |
| Multi-session or handover work (default) | *(none)* | + `PROJECT_CONTEXT.md`, `PLANS.md`, `AGENTS.md` |
| Same, with field examples and filling hints | `--full` | same files as default |
| Audit existing docs, change nothing | `--check` | nothing |

If unsure, prefer `--lite`; re-running later without `--lite` upgrades in place. If the project already has a mature `AGENTS.md` / `README` structure, consider not using this skill at all.

When a framework generator is involved (`npm create`, `cargo new`, `uv init`, …), run it **first**, so its own `.gitignore` and layout win.

## 2. Run the script

`<skill-dir>` is the folder containing this file; quote both paths (also on Windows). Use `python3` or `py` if needed.

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target>" [--lite|--full] [--dry-run] [--json]
python "<skill-dir>/scripts/bootstrap_project.py" "<target>" --check [--check-level basic|standard|strict]
```

Read the `created` / `skipped` / `conflicts` / `git` / `agents` lines of the output.

- **git**: initializes a repo only if the target has no `.git` **and** is not inside a parent repository. Inside a parent repo (e.g. a monorepo subfolder) it skips `git init`; pass `--nested-git` only if the user really wants a nested repo.
- **agents**: the docs only take effect if an auto-loaded instruction file points to them. The script creates `AGENTS.md` unless `GEMINI.md` / `CLAUDE.md` already exists. If an existing entry file lacks a pointer, it prints a `hint:`; ask the user, then rerun with `--agents-md` to append a short pointer block.
- **commit**: none by default. Commit only when the user asks. `--commit` commits the untouched templates immediately; to commit filled docs, fill and check first, then `git add`/`git commit` those paths yourself.

## 3. Fill the docs

Read [references/project-docs.md](references/project-docs.md) before filling or reviewing.

- Fill only what is known from the user, code, and config, in the user's language (templates are Chinese). Leave unknowns as `待补充`; never invent facts. Mark planned-but-unbuilt items as planned.
- `README.md`: summary + install/run commands. `PROJECT_CONTEXT.md`: verified stable facts + actual top-level structure tree; keep the `最后整理：YYYY-MM-DD` (or `Last reviewed:`) line. `PLANS.md`: start empty; add an entry only for real multi-step work.
- After a lite → default upgrade, add links to the new docs in the README.

## 4. Verify

Run `--check` (default `standard`) and report findings. Placeholders and empty docs are **issues**; stale review date (default 90 days), structure drift, missing structure tree, and a missing agent entry are **warnings** (only `strict` blocks on warnings). A passing check does not prove the content is correct — say so when reporting.

Options for `--check`: `--stale-days N` (0 disables), `--plans-max-kb N` (default 16, 0 disables), `--placeholder TEXT` (repeatable). Exit codes: 0 ok, 1 failure/blocking findings, 2 bad arguments.

Never write passwords, API keys, tokens, cookies, or private URLs into any generated file.
