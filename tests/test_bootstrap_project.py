from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "bootstrap_project.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_project", SCRIPT_PATH)
assert SPEC and SPEC.loader
bootstrap_project = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap_project
SPEC.loader.exec_module(bootstrap_project)


class BootstrapProjectTests(unittest.TestCase):
    def temp_path(self) -> contextlib.AbstractContextManager[Path]:
        class TempPath:
            def __init__(self) -> None:
                self._temp = tempfile.TemporaryDirectory()

            def __enter__(self) -> Path:
                return Path(self._temp.__enter__())

            def __exit__(self, *args: object) -> None:
                self._temp.__exit__(*args)

        return TempPath()

    def capture(self, func, *args, **kwargs):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = func(*args, **kwargs)
        return result, stdout.getvalue()

    def create_templates(self, root: Path, mode: str = "minimal") -> tuple[list[str], list[str], list[str]]:
        root.mkdir(parents=True, exist_ok=True)
        return bootstrap_project.write_missing_files(root, mode=mode)

    def create_healthy_docs(self, root: Path) -> None:
        created, _, _ = self.create_templates(root)
        self.assertEqual(
            set(created),
            {"PROJECT_CONTEXT.md", "PLANS.md", "README.md", ".gitignore"},
        )
        for name in ("PROJECT_CONTEXT.md", "PLANS.md", "README.md"):
            path = root / name
            path.write_text(
                path.read_text(encoding="utf-8").replace("待补充", "已填写"),
                encoding="utf-8",
                newline="\n",
            )

    def git(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if not shutil.which("git"):
            self.skipTest("git executable is required")
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True,
            text=True, encoding="utf-8", check=True,
        )

    def create_repository(self, root: Path, *, commit: bool = False) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self.git(root, "init", "--template=")
        for key, value in (
            ("user.name", "Bootstrap Test"),
            ("user.email", "bootstrap@example.invalid"),
            ("commit.gpgsign", "false"),
            ("core.hooksPath", str(root / ".git" / "test-hooks")),
        ):
            self.git(root, "config", key, value)
        if commit:
            self.git(root, "add", "--all")
            self.git(root, "commit", "--allow-empty", "-m", "test fixture")

    def create_worktree(self, root: Path) -> Path:
        repository = root / "repository"
        self.create_healthy_docs(repository)
        self.create_repository(repository, commit=True)
        worktree = root / "linked worktree"
        self.git(repository, "worktree", "add", "--detach", str(worktree), "HEAD")
        return worktree

    def test_skill_metadata_is_valid_yaml(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        metadata = yaml.safe_load(text.split("---", 2)[1])
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata["name"], SKILL_DIR.name)
        self.assertIsInstance(metadata["description"], str)
        self.assertTrue(metadata["description"].strip())

    def make_symlink(self, target: Path, link: Path, *, target_is_directory: bool = False) -> None:
        try:
            os.symlink(target, link, target_is_directory=target_is_directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")

    def test_default_template_file_set_and_key_content(self) -> None:
        with self.temp_path() as root:
            created, skipped, conflicts = self.create_templates(root)
            self.assertEqual(
                set(created),
                {"PROJECT_CONTEXT.md", "PLANS.md", "README.md", ".gitignore"},
            )
            self.assertEqual(skipped, [])
            self.assertEqual(conflicts, [])
            self.assertIn("## 项目定位", (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8"))
            self.assertIn("## 当前计划", (root / "PLANS.md").read_text(encoding="utf-8"))
            self.assertIn("## 文档入口", (root / "README.md").read_text(encoding="utf-8"))

    def test_lite_template_file_set_and_key_content(self) -> None:
        with self.temp_path() as root:
            created, skipped, conflicts = self.create_templates(root, "lite")
            self.assertEqual(set(created), {"README.md", ".gitignore"})
            self.assertEqual(skipped, [])
            self.assertEqual(conflicts, [])
            self.assertIn("小项目模式", (root / "README.md").read_text(encoding="utf-8"))
            self.assertFalse((root / "PROJECT_CONTEXT.md").exists())
            self.assertFalse((root / "PLANS.md").exists())

    def test_full_template_file_set_and_key_content(self) -> None:
        with self.temp_path() as root:
            created, skipped, conflicts = self.create_templates(root, "full")
            self.assertEqual(
                set(created),
                {"PROJECT_CONTEXT.md", "PLANS.md", "README.md", ".gitignore"},
            )
            self.assertEqual(skipped, [])
            self.assertEqual(conflicts, [])
            self.assertIn("本文档用于让新的 AI 会话", (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8"))
            self.assertIn("## 使用规则", (root / "PLANS.md").read_text(encoding="utf-8"))
            self.assertIn("给后续维护者的提示", (root / "README.md").read_text(encoding="utf-8"))

    def test_existing_regular_file_is_skipped_without_overwrite(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            readme = root / "README.md"
            readme.write_text("keep me", encoding="utf-8")
            created, skipped, conflicts = bootstrap_project.write_missing_files(root, mode="minimal")
            self.assertIn("README.md", skipped)
            self.assertNotIn("README.md", created)
            self.assertEqual(conflicts, [])
            self.assertEqual(readme.read_text(encoding="utf-8"), "keep me")

    def test_directory_at_document_path_is_conflict(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            (root / "README.md").mkdir()
            _, skipped, conflicts = bootstrap_project.write_missing_files(root, mode="minimal")
            self.assertNotIn("README.md", skipped)
            self.assertIn("README.md", conflicts)

    def test_regular_file_symlink_is_conflict(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            target = root / "source.txt"
            target.write_text("source", encoding="utf-8")
            self.make_symlink(target, root / "README.md")
            _, skipped, conflicts = bootstrap_project.write_missing_files(root, mode="minimal")
            self.assertNotIn("README.md", skipped)
            self.assertIn("README.md", conflicts)
            self.assertEqual(target.read_text(encoding="utf-8"), "source")

    def test_directory_symlink_is_conflict(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            target = root / "target-dir"
            target.mkdir()
            self.make_symlink(target, root / "README.md", target_is_directory=True)
            _, skipped, conflicts = bootstrap_project.write_missing_files(root, mode="minimal")
            self.assertNotIn("README.md", skipped)
            self.assertIn("README.md", conflicts)

    def test_dangling_symlink_is_conflict(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            self.make_symlink(root / "missing-target", root / "README.md")
            _, skipped, conflicts = bootstrap_project.write_missing_files(root, mode="minimal")
            self.assertNotIn("README.md", skipped)
            self.assertIn("README.md", conflicts)

    def test_english_and_chinese_slugify(self) -> None:
        self.assertEqual(bootstrap_project.slugify("Deploy Handover"), "deploy-handover")
        self.assertEqual(bootstrap_project.slugify("部署 交接"), "部署-交接")
        self.assertEqual(bootstrap_project.slugify("---"), "report")

    def test_report_creation_and_same_slug_are_idempotent(self) -> None:
        with self.temp_path() as root:
            first_code, first_output = self.capture(
                bootstrap_project.write_report, root, slug="部署 交接"
            )
            second_code, second_output = self.capture(
                bootstrap_project.write_report, root, slug="部署 交接"
            )
            report = root / "docs" / "reports" / f"{date.today().isoformat()}-部署-交接.html"
            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            self.assertTrue(report.is_file())
            self.assertIn("created: docs/reports/", first_output)
            self.assertIn("skipped: docs/reports/", second_output)
            html = report.read_text(encoding="utf-8")
            self.assertNotIn("{{TITLE}}", html)
            self.assertIn("部署 交接", html)

    def test_report_escapes_html_tokens(self) -> None:
        with self.temp_path() as root:
            result = bootstrap_project.write_report_result(root, slug="audit", kind='<b>&"')
            self.assertEqual(result.exit_code, 0)
            report = root / "docs" / "reports" / f"{date.today().isoformat()}-audit.html"
            html = report.read_text(encoding="utf-8")
            self.assertIn("&lt;b&gt;&amp;&quot;", html)
            self.assertNotIn("{{TITLE}}", html)

    def test_report_requires_complete_html_shell_and_offline_fonts(self) -> None:
        template = bootstrap_project.REPORT_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", template.lower())
        self.assertIn('<html lang="zh-CN">', template)
        self.assertIn('<meta charset="utf-8">', template)
        self.assertIn('<meta name="viewport"', template)
        self.assertIn("</style>", template)
        self.assertIn("</head>", template)
        self.assertIn("<body>", template)
        self.assertIn("</body>", template)
        self.assertIn("</html>", template)
        self.assertNotIn("fonts.googleapis.com", template)
        self.assertNotIn("fonts.gstatic.com", template)

        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            (root / "docs").write_text("conflict", encoding="utf-8")
            code, output = self.capture(bootstrap_project.write_report, root, slug="audit")
            self.assertEqual(code, 1)
            self.assertIn("error: report directory conflicts with a non-directory path", output)

    def test_manifest_combines_multiple_stacks_without_duplicate_blocks(self) -> None:
        with self.temp_path() as root:
            for marker in ("package.json", "pyproject.toml", "build.gradle", "Cargo.toml"):
                (root / marker).write_text("", encoding="utf-8")
            text = bootstrap_project.build_gitignore(root)
            self.assertIn("# Node", text)
            self.assertIn("# Python", text)
            self.assertIn("# Java (Maven/Gradle)", text)
            self.assertIn("# Rust", text)
            self.assertEqual(text.count("# Node"), 1)
            self.assertIn("!gradle/wrapper/gradle-wrapper.jar", text)
            self.assertIn("Review before ignoring", text)

    def test_stack_detection_and_combined_gitignore(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            (root / "package.json").write_text("{}", encoding="utf-8")
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            self.assertEqual(bootstrap_project.detect_stacks(root), ["node", "python"])
            text = bootstrap_project.build_gitignore(root)
            self.assertIn("node_modules/", text)
            self.assertIn("__pycache__/", text)
            self.assertNotIn("No language stack detected", text)

    def test_empty_project_gitignore_has_common_fallback(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            text = bootstrap_project.build_gitignore(root)
            self.assertIn(".env", text)
            self.assertIn("No language stack detected", text)

    def test_check_healthy_documents(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            self.create_repository(root, commit=True)
            code, output = self.capture(bootstrap_project.check, root)
            self.assertEqual(code, 0)
            self.assertIn("check[info] fresh_context PROJECT_CONTEXT.md:", output)
            self.assertIn("check[info] structure_match PROJECT_CONTEXT.md:", output)
            self.assertIn("check[info] git_ok .git:", output)
            self.assertIn("result: healthy", output)

    def test_check_reports_placeholders(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root)
            self.create_repository(root, commit=True)
            code, output = self.capture(bootstrap_project.check, root)
            self.assertEqual(code, 1)
            self.assertIn("check[issue] placeholder README.md:", output)

    def test_check_rejects_empty_markdown_documents(self) -> None:
        for content in (b"", b" \r\n\t", b"\xef\xbb\xbf"):
            with self.subTest(content=content), self.temp_path() as root:
                self.create_healthy_docs(root)
                names = {"README.md", "PROJECT_CONTEXT.md", "PLANS.md"}
                for name in names:
                    (root / name).write_bytes(content)
                self.create_repository(root, commit=True)
                for level in ("standard", "strict"):
                    with self.subTest(level=level):
                        completed = self.run_cli(str(root), "--check", "--check-level", level, "--json")
                        payload = json.loads(completed.stdout)
                        self.assertEqual(completed.returncode, 1, payload)
                        empty = {item["path"] for item in payload["checks"] if item["code"] == "empty_document"}
                        self.assertEqual(empty, names)
                        for name in names:
                            self.assertEqual((root / name).read_bytes(), content)

    def test_check_rejects_invalid_utf8_at_every_level(self) -> None:
        for name in bootstrap_project.DOC_FILES:
            with self.subTest(name=name), self.temp_path() as root:
                self.create_healthy_docs(root)
                content = b"\xff\xfeinvalid UTF-8"
                (root / name).write_bytes(content)
                self.create_repository(root, commit=True)
                for level in ("basic", "standard", "strict"):
                    with self.subTest(level=level):
                        completed = self.run_cli(str(root), "--check", "--check-level", level, "--json")
                        payload = json.loads(completed.stdout)
                        self.assertEqual(completed.returncode, 1, payload)
                        invalid = [item for item in payload["checks"] if item["code"] == "invalid_encoding"]
                        self.assertEqual([item["path"] for item in invalid], [name])
                        self.assertEqual((root / name).read_bytes(), content)

    def test_check_accepts_utf8_bom_and_empty_gitignore(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            for name in ("README.md", "PROJECT_CONTEXT.md", "PLANS.md"):
                path = root / name
                path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
            (root / ".gitignore").write_bytes(b"")
            self.create_repository(root, commit=True)
            completed = self.run_cli(str(root), "--check", "--check-level", "strict", "--json")
            self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_check_reports_stale_date(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            context = root / "PROJECT_CONTEXT.md"
            stale = (date.today() - timedelta(days=31)).isoformat()
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    f"最后整理：{date.today().isoformat()}", f"最后整理：{stale}"
                ),
                encoding="utf-8",
                newline="\n",
            )
            self.create_repository(root, commit=True)
            code, output = self.capture(bootstrap_project.check, root)
            self.assertEqual(code, 1)
            self.assertIn("check[issue] stale_context PROJECT_CONTEXT.md:", output)

    def test_cli_check_supports_custom_and_disabled_age_limits(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            context = root / "PROJECT_CONTEXT.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    f"最后整理：{date.today().isoformat()}",
                    f"最后整理：{(date.today() - timedelta(days=31)).isoformat()}",
                ), encoding="utf-8",
            )
            self.create_repository(root, commit=True)
            for days, code in ((30, 1), (60, 0), (0, 0)):
                with self.subTest(days=days):
                    completed = self.run_cli(
                        str(root), "--check", "--check-level", "strict", "--stale-days", str(days), "--json",
                    )
                    self.assertEqual(completed.returncode, code, completed.stdout)
                    payload = json.loads(completed.stdout)
                    self.assertEqual(payload["stale_days"], days)
                    self.assertEqual(any(item["code"] == "stale_context" for item in payload["checks"]), days == 30)

    def test_cli_check_additional_placeholders_preserve_default(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            (root / "README.md").write_text("# Demo\n\n[TBD]\n", encoding="utf-8")
            (root / "PLANS.md").write_text("# 计划\n\n待补充\n", encoding="utf-8")
            self.create_repository(root, commit=True)
            completed = self.run_cli(
                str(root), "--check", "--placeholder", "[TBD]", "--placeholder", "[TBD]", "--json",
            )
            self.assertEqual(completed.returncode, 1, completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["placeholders"], ["待补充", "[TBD]"])
            unfilled = {item["path"] for item in payload["checks"] if item["code"] == "placeholder"}
            self.assertEqual(unfilled, {"README.md", "PLANS.md"})

    def test_check_accepts_an_english_review_date(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            context = root / "PROJECT_CONTEXT.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace("最后整理：", "Last reviewed: "),
                encoding="utf-8",
            )
            self.create_repository(root, commit=True)
            completed = self.run_cli(str(root), "--check", "--check-level", "strict", "--json")
            self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_cli_rejects_invalid_check_settings(self) -> None:
        for arguments in (
            ("--stale-days", "60"), ("--placeholder", "TBD"),
            ("--check", "--stale-days", "-1"), ("--check", "--stale-days", "many"),
            ("--check", "--placeholder", " "),
        ):
            with self.subTest(arguments=arguments):
                completed = self.run_cli(*arguments, "--json")
                self.assertEqual(completed.returncode, 2, completed.stdout)
                self.assertEqual(json.loads(completed.stdout)["exit_code"], 2)
                self.assertEqual(completed.stderr, "")

    def test_check_reports_structure_drift(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            (root / "extra.txt").write_text("extra", encoding="utf-8")
            self.create_repository(root, commit=True)
            code, output = self.capture(bootstrap_project.check, root)
            self.assertEqual(code, 1)
            self.assertIn("check[issue] structure_drift PROJECT_CONTEXT.md:", output)

    def test_check_reports_no_git_repository(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            code, output = self.capture(bootstrap_project.check, root)
            self.assertEqual(code, 1)
            self.assertIn("check[issue] no_git .git:", output)

    def test_check_accepts_worktree_gitfile(self) -> None:
        with self.temp_path() as root:
            worktree = self.create_worktree(root)
            self.assertTrue((worktree / ".git").is_file())
            for level in ("basic", "standard", "strict"):
                with self.subTest(level=level):
                    result = bootstrap_project.check_result(worktree, level=level)
                    self.assertEqual(result.exit_code, 0, result.as_dict())
                    self.assertIn("git_ok", {item.code for item in result.checks})

    def test_bootstrap_accepts_worktree_without_replacing_gitfile(self) -> None:
        with self.temp_path() as root:
            worktree = self.create_worktree(root)
            gitfile = (worktree / ".git").read_bytes()
            readme = (worktree / "README.md").read_bytes()
            (worktree / "PLANS.md").unlink()
            for dry_run in (True, False):
                with self.subTest(dry_run=dry_run):
                    result = bootstrap_project.bootstrap_result(worktree, dry_run=dry_run)
                    self.assertEqual(result.exit_code, 0, result.as_dict())
                    self.assertTrue(result.git.startswith("skipped:"))
                    self.assertEqual(result.created, ["PLANS.md"])
                    self.assertEqual((worktree / "PLANS.md").exists(), not dry_run)
                    self.assertEqual((worktree / ".git").read_bytes(), gitfile)
                    self.assertEqual((worktree / "README.md").read_bytes(), readme)

    def test_check_rejects_invalid_repositories_at_every_level(self) -> None:
        for kind in ("empty-directory", "invalid-file", "missing-gitdir"):
            with self.subTest(kind=kind), self.temp_path() as root:
                self.create_healthy_docs(root)
                if kind == "empty-directory":
                    (root / ".git").mkdir()
                else:
                    content = "not a repository" if kind == "invalid-file" else "gitdir: missing\n"
                    (root / ".git").write_text(content, encoding="utf-8")
                for level in ("basic", "standard", "strict"):
                    with self.subTest(level=level):
                        completed = self.run_cli(str(root), "--check", "--check-level", level, "--json")
                        self.assertEqual(completed.returncode, 1)
                        codes = {item["code"] for item in json.loads(completed.stdout)["checks"]}
                        self.assertIn("git_error", codes)
                        self.assertNotIn("git_ok", codes)
                        self.assertNotIn("no_head", codes)

    def test_bootstrap_rejects_empty_git_directory_without_repairing_it(self) -> None:
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run), self.temp_path() as root:
                (root / ".git").mkdir()
                result = bootstrap_project.bootstrap_result(root, dry_run=dry_run)
                self.assertEqual(result.exit_code, 1)
                self.assertTrue(result.git.startswith("failed:"))
                self.assertEqual(list((root / ".git").iterdir()), [])
                self.assertEqual((root / "README.md").exists(), not dry_run)

    def test_valid_unborn_repository_is_distinct_from_invalid_repository(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            self.create_repository(root)
            for level in ("basic", "standard", "strict"):
                with self.subTest(level=level):
                    result = bootstrap_project.check_result(root, level=level)
                    self.assertNotIn("git_error", {item.code for item in result.checks})
                    self.assertEqual(result.exit_code, 1 if level == "strict" else 0)
                    no_head = [item for item in result.checks if item.code == "no_head"]
                    if level == "basic":
                        self.assertEqual(no_head, [])
                    else:
                        self.assertEqual(len(no_head), 1)
                        self.assertEqual(no_head[0].level, "issue" if level == "strict" else "warning")

    def test_parent_repository_does_not_count_as_target_repository(self) -> None:
        with self.temp_path() as root:
            self.create_repository(root, commit=True)
            child = root / "child"
            self.create_healthy_docs(child)
            missing = bootstrap_project.check_result(child, level="basic")
            self.assertIn("no_git", {item.code for item in missing.checks})
            self.assertEqual(bootstrap_project.bootstrap_plan(child, dry_run=True).git, "would-init: git repository")
            (child / ".git").mkdir()
            invalid = bootstrap_project.check_result(child, level="basic")
            self.assertIn("git_error", {item.code for item in invalid.checks})
            self.assertEqual(bootstrap_project.bootstrap_plan(child, dry_run=True).exit_code, 1)

    def test_strict_checks_preserve_index_bytes_and_mtime(self) -> None:
        for linked in (False, True):
            for dry_run in (False, True):
                with self.subTest(linked=linked, dry_run=dry_run), self.temp_path() as root:
                    if linked:
                        project = self.create_worktree(root)
                    else:
                        project = root
                        self.create_healthy_docs(project)
                        self.create_repository(project, commit=True)
                    index = Path(self.git(project, "rev-parse", "--git-path", "index").stdout.strip())
                    if not index.is_absolute():
                        index = project / index
                    original = (index.read_bytes(), index.stat().st_mtime_ns)
                    tracked = project / "README.md"
                    stat = tracked.stat()
                    # Change cached stat data without changing file contents;
                    # an ordinary git status would refresh the index here.
                    os.utime(tracked, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000_000))
                    args = [str(project), "--check", "--check-level", "strict", "--json"]
                    if dry_run:
                        args.append("--dry-run")
                    with mock.patch.dict(os.environ, {"GIT_OPTIONAL_LOCKS": "1"}):
                        completed = self.run_cli(*args)
                    self.assertEqual(completed.returncode, 0, completed.stdout)
                    self.assertEqual(json.loads(completed.stdout)["dry_run"], dry_run)
                    self.assertEqual((index.read_bytes(), index.stat().st_mtime_ns), original)

    def test_documented_noise_directories_are_checked_against_disk(self) -> None:
        for present in (True, False):
            with self.subTest(present=present), self.temp_path() as root:
                self.create_healthy_docs(root)
                self.create_repository(root)
                names = ("bin", "build", "vendor")
                context = root / "PROJECT_CONTEXT.md"
                context.write_text(
                    context.read_text(encoding="utf-8").replace(
                        "|-- PLANS.md", "|-- PLANS.md\n" + "\n".join(f"|-- {name}/" for name in names)
                    ), encoding="utf-8",
                )
                if present:
                    for name in names:
                        (root / name).mkdir()
                result = bootstrap_project.check_result(root)
                drift = [item for item in result.checks if item.code == "structure_drift"]
                if present:
                    self.assertEqual(drift, [])
                    self.assertEqual(result.exit_code, 0)
                else:
                    self.assertEqual(len(drift), 1)
                    self.assertIn("in tree but not on disk:", drift[0].message)
                    for name in names:
                        self.assertIn(name, drift[0].message)

    def test_undocumented_noise_directories_can_be_omitted(self) -> None:
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            self.create_repository(root)
            for name in ("bin", "build", "vendor"):
                (root / name).mkdir()
            result = bootstrap_project.check_result(root)
            self.assertEqual(result.exit_code, 0, result.as_dict())
            self.assertIn("structure_match", {item.code for item in result.checks})

    def test_check_lite_layout_is_recognized(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root, "lite")
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace("待补充", "已填写"),
                encoding="utf-8",
                newline="\n",
            )
            self.create_repository(root, commit=True)
            code, output = self.capture(bootstrap_project.check, root)
            self.assertEqual(code, 0)
            self.assertIn("lite layout", output)

    def test_check_non_directory_target(self) -> None:
        with self.temp_path() as root:
            target = root / "target.txt"
            target.write_text("not a directory", encoding="utf-8")
            code, output = self.capture(bootstrap_project.check, target)
            self.assertEqual(code, 1)
            self.assertIn("target is not a regular directory", output)

    def test_git_init_failure_raises_clear_runtime_error(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            completed = SimpleNamespace(returncode=1, stdout="", stderr="permission denied")
            with mock.patch.object(bootstrap_project.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(RuntimeError, "permission denied"):
                    bootstrap_project.init_git(root)

    def test_git_init_success_requires_a_local_repository(self) -> None:
        with self.temp_path() as root:
            completed = SimpleNamespace(returncode=0, stdout="initialized", stderr="")
            with mock.patch.object(bootstrap_project, "run_git", return_value=completed):
                with self.assertRaisesRegex(RuntimeError, "did not create a repository"):
                    bootstrap_project.init_git(root)

    @unittest.skipUnless(shutil.which("git"), "git executable is required")
    def test_initial_commit_success(self) -> None:
        with self.temp_path() as root:
            self.create_repository(root)
            (root / "README.md").write_text("test", encoding="utf-8")
            result = bootstrap_project.make_initial_commit(root, ["README.md"])
            self.assertEqual(result, (True, "created: committed generated files"))
            head = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=root,
                check=False,
                capture_output=True,
            )
            self.assertEqual(head.returncode, 0)

    def test_initial_commit_identity_failure_is_reported(self) -> None:
        add = SimpleNamespace(returncode=0, stdout="", stderr="")
        commit = SimpleNamespace(
            returncode=128,
            stdout="",
            stderr="Author identity unknown\nPlease tell me who you are.",
        )
        with mock.patch.object(bootstrap_project.subprocess, "run", side_effect=[add, commit]):
            result = bootstrap_project.make_initial_commit(Path.cwd(), ["README.md"])
        self.assertFalse(result[0])
        self.assertIn("failed: Author identity unknown", result[1])

    def test_initial_commit_preserves_unrelated_staged_changes(self) -> None:
        with self.temp_path() as root:
            self.create_repository(root)
            (root / "unrelated.txt").write_text("already staged", encoding="utf-8")
            self.git(root, "add", "--", "unrelated.txt")
            (root / "README.md").write_text("completed docs", encoding="utf-8")
            ok, message = bootstrap_project.make_initial_commit(root, ["README.md"])
            self.assertTrue(ok, message)
            self.assertEqual(self.git(root, "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines(), ["README.md"])
            self.assertEqual(self.git(root, "diff", "--cached", "--name-only").stdout.splitlines(), ["unrelated.txt"])

    def test_bootstrap_commit_ignores_foreign_git_environment(self) -> None:
        for layout in ("new", "existing", "worktree"):
            with self.subTest(layout=layout), self.temp_path() as root:
                foreign = root / "foreign repository"
                self.create_healthy_docs(foreign)
                self.create_repository(foreign, commit=True)
                (foreign / "staged.txt").write_text("keep staged\n", encoding="utf-8")
                self.git(foreign, "add", "--", "staged.txt")
                before = {p.relative_to(foreign): p.read_bytes() for p in foreign.rglob("*") if p.is_file()}

                if layout == "worktree":
                    target = self.create_worktree(root)
                    self.git(target, "rm", "--", "README.md")
                    self.git(target, "commit", "-m", "remove README for bootstrap fixture")
                    gitfile = (target / ".git").read_bytes()
                    expected = {"README.md"}
                else:
                    target = root / "目标项目 with spaces"
                    if layout == "existing":
                        self.create_repository(target)
                    expected = set(bootstrap_project.DOC_FILES)

                config = root / "test.gitconfig"
                self.git(root, "config", "--file", str(config), "commit.gpgsign", "false")
                self.git(root, "config", "--file", str(config), "core.hooksPath", str(root / "no-hooks"))
                template = root / "empty-template"
                template.mkdir()
                environment = {
                    "GIT_DIR": str(foreign / ".git"),
                    "GIT_WORK_TREE": str(foreign),
                    "GIT_COMMON_DIR": str(foreign / ".git"),
                    "GIT_INDEX_FILE": str(foreign / ".git" / "index"),
                    "GIT_OBJECT_DIRECTORY": str(foreign / ".git" / "objects"),
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "core.worktree",
                    "GIT_CONFIG_VALUE_0": str(foreign),
                    "GIT_CONFIG_GLOBAL": str(config),
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_TEMPLATE_DIR": str(template),
                    "GIT_AUTHOR_NAME": "Bootstrap Override",
                    "GIT_AUTHOR_EMAIL": "override@example.invalid",
                    "GIT_COMMITTER_NAME": "Bootstrap Override",
                    "GIT_COMMITTER_EMAIL": "override@example.invalid",
                }
                with mock.patch.dict(os.environ, environment):
                    completed = self.run_cli(str(target), "--commit", "--json")
                self.assertEqual(completed.returncode, 0, completed.stdout)
                self.assertEqual(set(json.loads(completed.stdout)["created"]), expected)
                self.assertTrue((target / ".git").exists())
                self.assertEqual(
                    set(self.git(target, "show", "--pretty=format:", "--name-only", "HEAD").stdout.splitlines()),
                    expected,
                )
                self.assertEqual(self.git(target, "log", "-1", "--format=%an <%ae>").stdout.strip(),
                                 "Bootstrap Override <override@example.invalid>")
                after = {p.relative_to(foreign): p.read_bytes() for p in foreign.rglob("*") if p.is_file()}
                self.assertEqual(after, before)
                if layout == "worktree":
                    self.assertEqual((target / ".git").read_bytes(), gitfile)

    def test_strict_check_ignores_foreign_git_index_and_worktree(self) -> None:
        with self.temp_path() as root:
            target = root / "target"
            foreign = root / "foreign"
            self.create_healthy_docs(target)
            self.create_repository(target, commit=True)
            self.create_repository(foreign, commit=True)
            (foreign / "staged.txt").write_text("keep staged\n", encoding="utf-8")
            self.git(foreign, "add", "--", "staged.txt")
            before = (foreign / ".git" / "index").read_bytes()
            environment = {
                "GIT_DIR": str(foreign / ".git"),
                "GIT_WORK_TREE": str(foreign),
                "GIT_INDEX_FILE": str(foreign / ".git" / "index"),
                "GIT_COMMON_DIR": str(foreign / ".git"),
            }
            with mock.patch.dict(os.environ, environment):
                completed = self.run_cli(str(target), "--check", "--check-level", "strict", "--json")
            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertEqual((foreign / ".git" / "index").read_bytes(), before)

    def test_initial_commit_hook_failure_is_reported(self) -> None:
        add = SimpleNamespace(returncode=0, stdout="", stderr="")
        commit = SimpleNamespace(returncode=1, stdout="", stderr="pre-commit hook failed")
        with mock.patch.object(bootstrap_project.subprocess, "run", side_effect=[add, commit]):
            result = bootstrap_project.make_initial_commit(Path.cwd(), ["README.md"])
        self.assertEqual(result, (False, "failed: pre-commit hook failed"))

    def test_check_result_exposes_stable_fields(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root)
            result = bootstrap_project.check_result(root)
            placeholder = next(item for item in result.checks if item.code == "placeholder")
            self.assertEqual(placeholder.level, "issue")
            self.assertIn(placeholder.path, {"README.md", "PROJECT_CONTEXT.md", "PLANS.md"})
            self.assertTrue(placeholder.message)
            self.assertEqual(result.exit_code, 1)

    def test_check_basic_skips_standard_content_checks(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root)
            self.create_repository(root)
            result = bootstrap_project.check_result(root, level="basic")
            codes = {item.code for item in result.checks}
            self.assertNotIn("structure_missing", codes)
            self.assertNotIn("placeholder", codes)
            self.assertEqual(result.exit_code, 0)

    def test_check_basic_does_not_probe_head(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root)
            self.create_repository(root)
            with mock.patch.object(
                bootstrap_project, "read_git", wraps=bootstrap_project.read_git
            ) as read:
                result = bootstrap_project.check_result(root, level="basic")
            self.assertTrue(read.called)
            self.assertFalse(any("HEAD" in call.args or "status" in call.args for call in read.call_args_list))
            self.assertEqual(next(item.message for item in result.checks if item.code == "git_ok"), "Git repository is present")

    def test_check_strict_without_git_does_not_run_status(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root)
            with mock.patch.object(bootstrap_project.subprocess, "run") as run:
                result = bootstrap_project.check_result(root, level="strict")
            run.assert_not_called()
            self.assertIn("no_git", {item.code for item in result.checks})

    def test_check_strict_treats_lite_docs_and_no_head_as_issues(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root, "lite")
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace("待补充", "已填写"),
                encoding="utf-8",
            )
            self.create_repository(root)
            result = bootstrap_project.check_result(root, level="strict")
            codes = [item.code for item in result.checks if item.level == "issue"]
            self.assertIn("missing_file", codes)
            self.assertIn("no_head", codes)
            self.assertEqual(result.exit_code, 1)

    def test_check_strict_detects_untracked_files_hidden_by_git_config(self) -> None:
        for relative_path in (".untracked.txt", ".untracked/notes.txt"):
            with self.subTest(path=relative_path), self.temp_path() as root:
                self.create_healthy_docs(root)
                self.create_repository(root, commit=True)
                self.git(root, "config", "status.showUntrackedFiles", "no")
                arguments = (str(root), "--check", "--check-level", "strict", "--json")
                clean = self.run_cli(*arguments)
                self.assertEqual(clean.returncode, 0, clean.stdout)

                untracked = root / relative_path
                untracked.parent.mkdir(parents=True, exist_ok=True)
                untracked.write_text("uncommitted notes\n", encoding="utf-8")
                self.assertEqual(self.git(root, "status", "--porcelain").stdout, "")
                completed = self.run_cli(*arguments)
                payload = json.loads(completed.stdout)
                self.assertEqual(completed.returncode, 1, payload)
                self.assertEqual(payload["exit_code"], 1)
                issues = {item["code"] for item in payload["checks"] if item["level"] == "issue"}
                self.assertEqual(issues, {"dirty_worktree"})
                self.assertEqual(self.git(root, "config", "status.showUntrackedFiles").stdout.strip(), "no")
                self.assertEqual(untracked.read_text(encoding="utf-8"), "uncommitted notes\n")

    def test_check_strict_summary_counts_blocking_warnings(self) -> None:
        # A warning-only project (structure tree removed) blocks in strict
        # mode; the text summary must not claim "0 issue(s) found" while
        # exiting non-zero.
        with self.temp_path() as root:
            self.create_healthy_docs(root)
            context = root / "PROJECT_CONTEXT.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace("```text", "```"),
                encoding="utf-8",
                newline="\n",
            )
            self.create_repository(root, commit=True)
            result = bootstrap_project.check_result(root, level="strict")
            self.assertEqual(result.exit_code, 1)
            self.assertFalse(any(item.level == "issue" for item in result.checks))
            rendered = bootstrap_project.render_check(result)
            self.assertIn("result: 1 blocking item(s) found", rendered)
            self.assertNotIn("0 issue", rendered)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT_PATH), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_json_results_have_common_contract_fields(self) -> None:
        common = {
            "operation", "target", "mode", "created", "skipped", "conflicts",
            "git", "commit", "report", "checks", "errors", "exit_code", "dry_run",
        }
        with self.temp_path() as root:
            bootstrap = bootstrap_project.bootstrap_plan(root / "bootstrap", dry_run=True).as_dict()
            report = bootstrap_project.report_plan(root / "report", slug="audit", dry_run=True).as_dict()
            check = bootstrap_project.check_result(root / "missing").as_dict()
        self.assertTrue(common <= bootstrap.keys())
        self.assertTrue(common <= report.keys())
        self.assertTrue(common <= check.keys())

    def test_json_argument_error_is_one_parseable_object(self) -> None:
        completed = self.run_cli("--check", "--commit", "--json")
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["operation"], "arguments")
        self.assertEqual(payload["exit_code"], 2)
        self.assertEqual(completed.stderr, "")

    def test_dry_run_rejects_file_parent_without_side_effects(self) -> None:
        with self.temp_path() as root:
            parent = root / "file"
            parent.write_text("x", encoding="utf-8")
            target = parent / "child"
            completed = self.run_cli(str(target), "--dry-run", "--json")
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertIn("target parent is not a regular directory", payload["errors"][0])
            self.assertFalse(target.exists())

    def test_json_check_is_one_parseable_object(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root, "lite")
            self.create_repository(root)
            completed = self.run_cli(str(root), "--check", "--json")
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["operation"], "check")
            self.assertEqual(payload["mode"], "check")
            self.assertEqual(payload["level"], "standard")
            self.assertEqual(completed.stdout.count("\n"), 1)

    def test_dry_run_bootstrap_has_no_side_effects(self) -> None:
        with self.temp_path() as root:
            target = root / "new-project"
            completed = self.run_cli(str(target), "--dry-run", "--commit", "--json")
            self.assertEqual(completed.returncode, 0)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["dry_run"], True)
            self.assertEqual(payload["created"], ["PROJECT_CONTEXT.md", "PLANS.md", "README.md", ".gitignore"])
            self.assertEqual(payload["git"], "would-init: git repository")
            self.assertEqual(payload["commit"], "would-commit: generated files")
            self.assertFalse(target.exists())

    def test_dry_run_report_detects_report_directory_conflict(self) -> None:
        with self.temp_path() as root:
            (root / "docs").write_text("conflict", encoding="utf-8")
            completed = self.run_cli(str(root), "--report=audit", "--dry-run", "--json")
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["conflicts"], ["docs"])
            self.assertEqual((root / "docs").read_text(encoding="utf-8"), "conflict")

    def test_dry_run_report_has_no_side_effects(self) -> None:
        with self.temp_path() as root:
            target = root / "new-project"
            completed = self.run_cli(str(target), "--report=audit", "--dry-run", "--json")
            self.assertEqual(completed.returncode, 0)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["dry_run"], True)
            self.assertEqual(payload["created"], ["docs/reports/" + date.today().isoformat() + "-audit.html"])
            self.assertFalse(target.exists())

    def test_check_rejects_symlink_target(self) -> None:
        with self.temp_path() as root:
            target = root / "target"
            target.mkdir()
            link = root / "link"
            self.make_symlink(target, link, target_is_directory=True)
            result = bootstrap_project.check_result(link)
            self.assertEqual(result.exit_code, 1)
            self.assertIn("symbolic link", result.errors[0])

    def test_cli_rejects_check_level_without_check(self) -> None:
        for arguments in (("--check-level", "strict"), ("--check-level=strict",)):
            with self.subTest(arguments=arguments), self.temp_path() as root:
                target = root / "new-project"
                completed = self.run_cli(str(target), *arguments, "--json")
                self.assertEqual(completed.returncode, 2)
                payload = json.loads(completed.stdout)
                self.assertIn("only valid with --check", payload["errors"][0])
                self.assertFalse(target.exists())

    def test_cli_rejects_abbreviated_options_without_side_effects(self) -> None:
        for arguments in (
            ("--check-lev", "strict"), ("--check-lev=strict",),
            ("--check", "--check-lev", "strict"), ("--check", "--check-lev=strict"),
            ("--repor=audit",),
        ):
            with self.subTest(arguments=arguments), self.temp_path() as root:
                target = root / "new-project"
                completed = self.run_cli(str(target), *arguments, "--json")
                self.assertEqual(completed.returncode, 2, completed.stdout)
                payload = json.loads(completed.stdout)
                self.assertEqual(payload["operation"], "arguments")
                self.assertEqual(payload["exit_code"], 2)
                self.assertEqual(payload["created"], [])
                self.assertTrue(payload["errors"])
                self.assertEqual(completed.stderr, "")
                self.assertFalse(target.exists())

    def test_cli_rejects_conflicting_operations(self) -> None:
        completed = self.run_cli("--check", "--report", "audit", "--json")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("mutually exclusive operations", json.loads(completed.stdout)["errors"][0])

    def test_cli_rejects_report_with_initialization_flags(self) -> None:
        for flag in ("--full", "--lite", "--commit"):
            with self.subTest(flag=flag):
                completed = self.run_cli("--report", "audit", flag, "--json")
                self.assertEqual(completed.returncode, 2)
                self.assertIn("only valid for initialization", json.loads(completed.stdout)["errors"][0])

    def test_cli_requires_explicit_current_directory_report_slug(self) -> None:
        completed = self.run_cli("--report", "audit", "--json")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("ambiguous report syntax", json.loads(completed.stdout)["errors"][0])

    def test_cli_accepts_report_slug_with_explicit_target(self) -> None:
        with self.temp_path() as root:
            completed = self.run_cli(str(root), "--report", "audit", "--json")
            self.assertEqual(completed.returncode, 0, completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["operation"], "report")
            self.assertTrue((root / payload["report"]).is_file())

    def test_cli_lite_upgrade_preserves_existing_docs_and_source(self) -> None:
        with self.temp_path() as root:
            source = root / "main.py"
            source.write_text("print('hello')\n", encoding="utf-8")
            first = self.run_cli(str(root), "--lite", "--json")
            self.assertEqual(first.returncode, 0, first.stdout)
            readme = root / "README.md"
            readme.write_text("# Hello\n\nRun with `python main.py`.\n", encoding="utf-8")
            before = {name: (root / name).read_bytes() for name in ("README.md", ".gitignore", "main.py")}
            second = self.run_cli(str(root), "--json")
            self.assertEqual(second.returncode, 0, second.stdout)
            self.assertEqual(set(json.loads(second.stdout)["created"]), {"PROJECT_CONTEXT.md", "PLANS.md"})
            for name, content in before.items():
                self.assertEqual((root / name).read_bytes(), content)
            third = self.run_cli(str(root), "--json")
            self.assertEqual(third.returncode, 0, third.stdout)
            self.assertEqual(json.loads(third.stdout)["created"], [])

    def test_bootstrap_conflict_returns_one(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            (root / "README.md").mkdir()
            with mock.patch.object(
                bootstrap_project, "init_git", return_value="skipped: test"
            ):
                code, output = self.capture(bootstrap_project.bootstrap, root)
            self.assertEqual(code, 1)
            self.assertIn("conflicts: README.md", output)
            # Conflict on one file must not block creating the others.
            self.assertTrue((root / "PROJECT_CONTEXT.md").is_file())
            self.assertTrue((root / "PLANS.md").is_file())
            self.assertTrue((root / ".gitignore").is_file())
            self.assertFalse((root / "README.md").is_file())

    def test_bootstrap_bad_git_path_still_creates_docs(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            (root / ".git").write_text("not a repository", encoding="utf-8")
            code, output = self.capture(bootstrap_project.bootstrap, root)
            self.assertEqual(code, 1)
            self.assertIn("git: failed:", output)
            self.assertTrue((root / "README.md").is_file())
            self.assertTrue((root / "PROJECT_CONTEXT.md").is_file())
            self.assertTrue((root / "PLANS.md").is_file())
            self.assertTrue((root / ".gitignore").is_file())

    def test_dry_run_bad_git_path_reports_failure_without_touching(self) -> None:
        with self.temp_path() as root:
            root.mkdir(parents=True, exist_ok=True)
            (root / ".git").write_text("not a repository", encoding="utf-8")
            result = bootstrap_project.bootstrap_plan(root, dry_run=True)
            self.assertEqual(result.exit_code, 1)
            self.assertIn("failed", result.git)
            self.assertEqual((root / ".git").read_text(encoding="utf-8"), "not a repository")

    def test_check_dry_run_flag_is_reported(self) -> None:
        with self.temp_path() as root:
            self.create_templates(root, "lite")
            self.create_repository(root)
            completed = self.run_cli(str(root), "--check", "--dry-run", "--json")
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["dry_run"], True)

    def test_target_creation_failure_returns_one(self) -> None:
        with self.temp_path() as root:
            parent_file = root / "not-a-directory"
            parent_file.write_text("x", encoding="utf-8")
            code, output = self.capture(bootstrap_project.bootstrap, parent_file / "child")
            self.assertEqual(code, 1)
            self.assertIn("error: target parent is not a regular directory", output)

    def test_json_target_creation_failure_does_not_report_planned_files(self) -> None:
        with self.temp_path() as root:
            target = root / "new-project"
            with (
                mock.patch.object(Path, "mkdir", side_effect=PermissionError("permission denied")),
                mock.patch.object(sys, "argv", [str(SCRIPT_PATH), str(target), "--json"]),
            ):
                code, output = self.capture(bootstrap_project.main)
            payload = json.loads(output)
            self.assertEqual(code, 1)
            self.assertEqual(payload["exit_code"], 1)
            self.assertEqual(payload["created"], [])
            self.assertIn("unable to prepare target directory", payload["errors"][0])
            self.assertFalse(target.exists())

    def test_json_file_inspection_failure_does_not_report_planned_files(self) -> None:
        with self.temp_path() as root:
            self.create_repository(root)
            with (
                mock.patch.object(bootstrap_project, "write_missing_files", side_effect=PermissionError("permission denied")),
                mock.patch.object(sys, "argv", [str(SCRIPT_PATH), str(root), "--json"]),
            ):
                code, output = self.capture(bootstrap_project.main)
            payload = json.loads(output)
            self.assertEqual(code, 1)
            self.assertEqual(payload["exit_code"], 1)
            self.assertEqual(payload["created"], [])
            self.assertIn("unable to inspect or create project files", payload["errors"][0])
            self.assertFalse(any((root / name).exists() for name in bootstrap_project.DOC_FILES))

    def test_json_partial_write_failure_reports_only_created_files(self) -> None:
        with self.temp_path() as root:
            root = root.resolve()
            self.create_repository(root)
            original_open = Path.open

            def fail_plans(path, *args, **kwargs):
                if path == root / "PLANS.md":
                    raise PermissionError("permission denied")
                return original_open(path, *args, **kwargs)

            with (
                mock.patch.object(Path, "open", fail_plans),
                mock.patch.object(sys, "argv", [str(SCRIPT_PATH), str(root), "--json"]),
            ):
                code, output = self.capture(bootstrap_project.main)
            payload = json.loads(output)
            self.assertEqual(code, 1)
            self.assertEqual(payload["exit_code"], 1)
            self.assertEqual(set(payload["created"]), {"PROJECT_CONTEXT.md", "README.md", ".gitignore"})
            self.assertTrue(all((root / name).is_file() for name in payload["created"]))
            self.assertFalse((root / "PLANS.md").exists())
            self.assertTrue(any("PLANS.md" in conflict for conflict in payload["conflicts"]))


if __name__ == "__main__":
    unittest.main()
