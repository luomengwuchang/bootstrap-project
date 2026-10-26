# Project reports

Read this workflow when a dated handover, audit, or investigation report is requested.

## Create the report

Run the bundled script using its actual installed path:

```bash
python "<skill-dir>/scripts/bootstrap_project.py" "<target-directory>" --report deploy-handover
```

The script creates `docs/reports/<YYYY-MM-DD>-<slug>.html` and any missing parent directories.
It does not initialize Git or create the collaboration Markdown files. A report with the same
date and slug is skipped. If the task needs a new report, choose a distinct, descriptive slug
and rerun; preserve the earlier snapshot.

For a custom slug in the current directory, use `--report=SLUG`. The form `--report SLUG`
without a preceding target is rejected because the positional argument is ambiguous.
`--dry-run` previews the path; `--json` returns the structured result.

## Fill and verify

1. Use the user's requested language, replace the content placeholders, and set a concise,
   specific `<title>` and heading. Keep the date in the filename and page header.
2. Delete sections that do not apply. The template includes stat tiles, findings, tables,
   notes, a checklist, and an optional SVG diagram.
3. Prefer measured values; label estimates. Explain findings and their consequences.
4. Record what was verified, what remains unverified, and who can complete that verification.
5. Use a diagram when it explains the mechanism more clearly than prose, and label its arrows.
6. Review the finished HTML for remaining placeholders and open it in a browser when available.
   The project's `--check` command audits the collaboration Markdown files, not report contents.

Keep credentials, tokens, cookies, private URLs, and sensitive datasets out of the report.
Describe credential storage and retrieval without copying the secret value.

## Template and document roles

The report is a historical snapshot. `PROJECT_CONTEXT.md` and `PLANS.md` remain the living
project documents; keep ongoing edits there and create fresh reports for later milestones.
Archive older `PLANS.md` history per the retention rule in that file instead of letting it grow.

Reuse `assets/report-template.html` unless the user requests design changes. The page is
self-contained and uses system fonts, a light theme, and a dark theme selected automatically
by the system preference. It has no manual theme switch and requires no network resources.
Keep colors in the existing CSS variables when adapting components so both themes remain readable.
