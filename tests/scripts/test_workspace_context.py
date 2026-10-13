def test_summarizes_project(write, run_script, tmp_path):
    write(
        "pyproject.toml",
        """
        [project]
        name = "demo"
        requires-python = ">=3.11"
        dependencies = ["pyspark>=3.5", "pandas"]

        [dependency-groups]
        dev = ["pytest>=8"]

        [tool.ruff]
        line-length = 100
        """,
    )
    write("databricks.yml", "bundle:\n  name: demo\n")
    write("src/demo/__init__.py", "")
    write("src/demo/job.py", "from pyspark.sql import SparkSession\n")
    write("notebooks/explore.py", "# Databricks notebook source\nprint(1)\n")
    write("tests/test_job.py", "def test_x():\n    pass\n")
    write(".github/cuypilot.lock.json", '{"items": {"python-design": {"type": "skill"}}}')

    out = run_script("improve-prompt", "workspace_context.py", str(tmp_path))

    assert "python: >=3.11" in out
    assert "dependencies: pandas, pyspark" in out
    assert "dev dependencies: pytest" in out
    assert "tooling: databricks bundle, ruff" in out
    assert "layout: src/; packages: demo" in out
    assert "1 Databricks .py" in out
    assert "tests: 1 test file(s)" in out
    assert "uses: pyspark" in out
    assert "cuypilot pieces: python-design (skill)" in out


def test_empty_project(run_script, tmp_path):
    out = run_script("improve-prompt", "workspace_context.py", str(tmp_path))
    assert "python: not declared" in out and "dependencies: none declared" in out


def test_summarizes_all_assistant_locks(write, run_script, tmp_path):
    write(".opencode/cuypilot.lock.json", '{"items": {"python-design": {"type": "skill"}}}')
    write(".assistant/cuypilot.lock.json", '{"items": {"docs-writer": {"type": "agent"}}}')
    write("AGENTS.md", "# Project conventions")
    out = run_script("improve-prompt", "workspace_context.py", str(tmp_path))
    assert "python-design (skill) [opencode]" in out
    assert "docs-writer (agent) [genie]" in out
    assert "instructions: AGENTS.md present" in out
