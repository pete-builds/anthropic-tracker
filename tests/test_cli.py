"""Tests for CLI commands."""

import json

import httpx
import respx
from click.testing import CliRunner

from anthropic_tracker.cli import cli
from anthropic_tracker.config import GREENHOUSE_API_URL, GREENHOUSE_DEPARTMENTS_URL
from tests.fixtures import SAMPLE_JOBS

MOCK_DEPARTMENTS = {
    "departments": [
        {
            "id": 100,
            "name": "Software Engineering (Infrastructure)",
            "jobs": [
                {"id": 1001, "title": "Senior Software Engineer, Infrastructure"},
                {"id": 1004, "title": "Forward Deployed Engineer"},
            ],
        },
        {
            "id": 200,
            "name": "Sales",
            "jobs": [
                {"id": 1002, "title": "Account Executive, Higher Education"},
                {"id": 1005, "title": "Solutions Architect, EMEA"},
            ],
        },
        {
            "id": 300,
            "name": "AI Research & Engineering",
            "jobs": [
                {"id": 1003, "title": "Research Scientist, Interpretability"},
            ],
        },
    ]
}


def _mock_api():
    """Set up standard API mocks for jobs + departments."""
    respx.get(GREENHOUSE_API_URL).mock(
        return_value=httpx.Response(200, json={"jobs": SAMPLE_JOBS})
    )
    respx.get(GREENHOUSE_DEPARTMENTS_URL).mock(
        return_value=httpx.Response(200, json=MOCK_DEPARTMENTS)
    )


class TestCLI:
    def test_init_command(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        runner = CliRunner()
        result = runner.invoke(cli, ["--db", db_path, "init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

    @respx.mock
    def test_fetch_command(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _mock_api()

        runner = CliRunner()
        result = runner.invoke(cli, ["--db", db_path, "fetch"])
        assert result.exit_code == 0
        assert "5" in result.output

    @respx.mock
    def test_summary_after_fetch(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _mock_api()

        runner = CliRunner()
        runner.invoke(cli, ["--db", db_path, "fetch"])
        result = runner.invoke(cli, ["--db", db_path, "summary"])
        assert result.exit_code == 0

    @respx.mock
    def test_report_json(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _mock_api()

        runner = CliRunner()
        runner.invoke(cli, ["--db", db_path, "fetch"])
        result = runner.invoke(cli, ["--db", db_path, "report", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_active"] == 5

    @respx.mock
    def test_report_csv(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _mock_api()

        runner = CliRunner()
        runner.invoke(cli, ["--db", db_path, "fetch"])
        result = runner.invoke(cli, ["--db", db_path, "report", "--format", "csv"])
        assert result.exit_code == 0
        assert "id,title,department" in result.output

    def test_alerts_no_data(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        runner = CliRunner()
        runner.invoke(cli, ["--db", db_path, "init"])
        result = runner.invoke(cli, ["--db", db_path, "alerts"])
        assert result.exit_code == 0

    def test_trends_no_data(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        runner = CliRunner()
        runner.invoke(cli, ["--db", db_path, "init"])
        result = runner.invoke(cli, ["--db", db_path, "trends"])
        assert result.exit_code == 0
