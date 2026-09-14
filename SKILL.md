---
name: bootstrap-project
description: >-
  Initialize project workspaces with Git and starter documents, audit existing
  project docs for missing content and drift, or scaffold HTML reports for
  project handovers, audits, and investigations. Use for project scaffolding,
  new repositories, PROJECT_CONTEXT.md / PLANS.md / README.md / .gitignore setup,
  or project documentation checks — e.g. "初始化项目", "新建项目脚手架",
  "检查项目文档", "项目交接报告". Preserves existing files.
license: MIT
---

# Bootstrap Project

## Overview

Use this skill to prepare a new project directory before implementation work begins, or to health-check the docs of an existing one. It initializes `git` when needed and creates missing starter documents with concise defaults; `--full` gives a more detailed template, `--lite` a two-doc setup for small projects, and `--check` audits existing docs without creating anything.

Requires Python 3.10+ and Git for repository operations. Report generation works offline without Git; the script has no third-party runtime dependencies.

## Workflow

1. Use the target project directory named by the user, or the current working directory if none is named.
2. Pick the mode: default minimal; `--full` for the detailed template; `--lite` for small projects and one-off scripts (only `README.md`, `.gitignore`); `--check` for auditing existing project docs; `--report` for a project handover, audit, or investigation write-up.
3. Run the bundled script by absolute path: `python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>" [options]`, where `<skill-dir>` is the folder containing this `SKILL.md`. Resolve that actual location instead of assuming a particular agent's installation path. Initialization, check, and report are mutually exclusive; `--full` / `--lite` / `--commit` are initialization-only. When the deliverable includes completed docs and a commit, defer the commit until step 8; the script's `--commit` flag commits templates immediately.
4. Read the script output to identify created, skipped, and failed paths. For a check-only task, relay the findings and fix them when requested. For reports, read [the report workflow](references/reports.md).
5. After creating files, fill every placeholder you can from information already at hand, in the user's requested language. The bundled templates start in Chinese. For an existing codebase, scan it and fill in the stack, run commands, and structure tree in `PROJECT_CONTEXT.md` / `README.md`; for a new project, use the user's stated purpose. Leave placeholders only for unknown information. Preserve a parseable `最后整理：YYYY-MM-DD` or `Last reviewed: YYYY-MM-DD` field and the structure tree when translating the context document.
6. When upgrading a lite project (re-running without `--lite`), update the `文档入口`/docs section in `README.md` afterwards so it points to the newly added `PROJECT_CONTEXT.md` and `PLANS.md`.
7. After filling or updating the Markdown docs, rerun `--check --check-level standard`, preserving any user-selected `--stale-days` / `--placeholder` settings. Fix findings that can be resolved from the available information, and report unknown placeholders or other remaining findings. Use `basic` for a structural check of unfinished scaffolding; use `strict` after a requested commit when complete docs and a clean worktree are required. These checks verify structure and explicit markers; review factual content and run commands separately.
8. Commit only when the user explicitly asks (including a request to use `--commit`). For completed docs, commit the generated or intentionally updated documentation paths after filling and checking them, preserving unrelated staged changes. Do not rerun the script with `--commit` to commit later edits: it commits only files newly created in that run. Finish by reporting the changes, verification, and any unresolved findings.

## Reports (`--report`)

Use reports for dated handovers, audits, and investigations. `TARGET --report [SLUG]` creates only
`docs/reports/<YYYY-MM-DD>-<slug>.html` and its missing parent directories. For a custom slug in
the current directory use `--report=SLUG`. Read [references/reports.md](references/reports.md)
when a report is requested; it covers filling, preserving historical reports, and the offline template.

## Default Behavior

- Initialize `git` only when the target directory has no `.git` entry, then verify the new repository belongs to the target. Validate existing repositories through Git, including worktree and submodule `.git` files; reject malformed or symlinked `.git` paths. A repository in a parent directory does not count as the target's repository. All Git calls isolate repository-local environment overrides; normal author/committer settings and user/system configuration remain available.
- Create only missing files; never overwrite existing `PROJECT_CONTEXT.md`, `PLANS.md`, `README.md`, or `.gitignore`.
- Keep the generated documents brief by default. Replace obvious placeholders only when the project name, purpose, stack, or run commands are already known.
- Use `--full` only for a more verbose template with extra usage rules and prompts.
- `--lite` creates only `README.md` and `.gitignore` for small projects. Because existing files are never overwritten, re-running without `--lite` later upgrades in place by adding the missing `PROJECT_CONTEXT.md` and `PLANS.md`.
- `--check` is read-only and accepts `--check-level basic|standard|strict` (default `standard`). Basic checks paths, UTF-8 readability (with optional BOM), and repository validity; standard also rejects blank Markdown docs and checks placeholders, last-tidy age, structure drift, and HEAD; strict additionally requires all docs, a parseable structure tree, a commit, and a clean worktree. An empty `.gitignore` is valid. Invalid repositories fail at every level; a valid repository without commits is a warning at standard and an issue at strict. Git probes disable optional locks so checks do not refresh the index. Issues return 1; strict also blocks on warnings.
- Check settings: `--stale-days N` changes the default 30-day age limit; `0` disables the age limit but still requires a parseable date. Repeat `--placeholder TEXT` to check additional literal, case-sensitive markers such as `TBD`; the built-in `待补充` marker remains active. These options are check-only; basic skips content and age checks.
- `--json` makes stdout exactly one UTF-8 JSON object with stable result fields, including errors and `exit_code`.
- `--dry-run` plans bootstrap, check, or report without creating directories, initializing Git, writing files, staging, or committing. It may be combined with `--commit` to preview the commit action.
- `--report` creates only the HTML report (plus `docs/reports/` if missing); it does not touch git or the Markdown docs, and never overwrites an existing report with the same date and slug.
- Keep secrets out of all generated files. Do not include passwords, API keys, tokens, cookies, private URLs, or full sensitive data.
- `.gitignore` is generated by detecting existing stack markers (`package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, …). For a brand-new empty directory it falls back to a minimal common set; append stack-specific entries later as code is added. Generic `dist/`, `build/`, `bin/`, and `vendor/` suggestions are commented out for review. Detected PHP, Ruby, and .NET stacks use active conventional rules for `vendor/`, `/vendor/bundle/`, and `bin/` / `obj/`, respectively. Review these against any maintained source directories. Java/Gradle rules keep `gradle/wrapper/gradle-wrapper.jar` tracked.
- By default no commit is created. Pass `--commit` to commit the generated files (this also serves as the initial commit for a fresh repo, so `git log` works immediately). The commit is limited to the files created by this run; anything already staged stays uncommitted.
- If `git` is unavailable or `git init` fails, the starter documents are still created; the failure is reported on the `git:` line and the exit code is non-zero.

## Generated Files

- `PROJECT_CONTEXT.md`: Stable project memory: purpose, stack, structure, run commands, data notes, and long-term cautions.
- `PLANS.md`: Dynamic plan record: current plan, history, status meanings, verification, and todo pool.
- `README.md`: Human-facing project entry and the session entry point: what the project is, how to run it, and the read order for `PROJECT_CONTEXT.md` / `PLANS.md`.
- `.gitignore`: Stack-aware ignores — common OS/editor/logs/secrets plus entries for whatever language markers were detected.

- `docs/reports/<date>-<slug>.html` (`--report` only): a complete self-contained, system-theme-aware offline report page for humans; the Markdown docs remain the source AI reads. Report values are HTML-escaped and the generator verifies that replacement tokens do not remain.

In `--lite` mode only `README.md` and `.gitignore` are generated; project context is maintained directly in `README.md`.

## Script

Replace `<skill-dir>` with the absolute directory containing this `SKILL.md`, and replace `<target-directory>` with the project path. Keep both paths quoted, including on Windows/PowerShell; use `python3` or `py` if that is the available Python launcher:

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>"
```

For the detailed template:

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>" --full
```

For small projects (README + .gitignore only):

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>" --lite
```

To health-check existing project docs (creates nothing):

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>" --check
```

Choose a check depth with `--check-level basic|standard|strict` (default: `standard`). Add `--json` when a caller needs one machine-readable object on stdout; add `--dry-run` to preview any operation without filesystem or Git side effects.

To scaffold a human-facing report page (creates nothing else):

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>" --report deploy-handover
```

For a custom slug in the current directory, use `--report=deploy-handover` rather than the ambiguous `--report deploy-handover`.

To create and immediately commit the generated templates (before any later editing):

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>" --commit
```

The script prints a concise summary with `mode`, `created`, `skipped`, `conflicts`, `git`, and `commit` results. Existing files are preserved by design. Add `--json` for a machine-readable result or `--dry-run` to inspect the planned operation without side effects. Expected operational failures and conflicts return 1; invalid argument combinations return 2.
