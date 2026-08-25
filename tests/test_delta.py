import pytest
"""Tests for delta computation."""

from anthropic_tracker.delta import compute_delta


class TestComputeDelta:
    def test_first_run_all_added(self, db, sample_jobs):
        result = compute_delta(db, sample_jobs, snapshot_date="2026-04-15")
        assert len(result.added) == 5
        assert len(result.removed) == 0
        assert result.total == 5

    def test_no_changes(self, db, sample_jobs):
        compute_delta(db, sample_jobs, snapshot_date="2026-04-15")
        result = compute_delta(db, sample_jobs, snapshot_date="2026-04-16")
        assert len(result.added) == 0
        assert len(result.removed) == 0
        assert result.unchanged == 5

    def test_job_removed(self, db, sample_jobs):
        compute_delta(db, sample_jobs, snapshot_date="2026-04-15")

        # Remove the last job
        reduced = sample_jobs[:4]
        result = compute_delta(db, reduced, snapshot_date="2026-04-16")
        assert len(result.added) == 0
        assert len(result.removed) == 1
        assert result.removed[0]["id"] == 1005

    def test_job_added(self, db, sample_jobs):
        compute_delta(db, sample_jobs[:3], snapshot_date="2026-04-15")
        result = compute_delta(db, sample_jobs, snapshot_date="2026-04-16")
        assert len(result.added) == 2
        assert result.total == 5

    def test_department_breakdown(self, db, sample_jobs):
        result = compute_delta(db, sample_jobs, snapshot_date="2026-04-15")
        assert result.departments["Software Engineering (Infrastructure)"] == 2
        assert result.departments["Sales"] == 2
        assert result.departments["AI Research & Engineering"] == 1

    def test_location_breakdown(self, db, sample_jobs):
        result = compute_delta(db, sample_jobs, snapshot_date="2026-04-15")
        assert result.locations["San Francisco, CA"] >= 3
        assert "London, UK" in result.locations

    def test_daily_snapshot_written(self, db, sample_jobs):
        compute_delta(db, sample_jobs, snapshot_date="2026-04-15")
        row = db.execute(
            "SELECT * FROM daily_snapshots WHERE date = '2026-04-15'"
        ).fetchone()
        assert row is not None
        assert row["total_active_jobs"] == 5
        assert row["jobs_added"] == 5

    def test_removed_job_marked_inactive(self, db, sample_jobs):
        compute_delta(db, sample_jobs, snapshot_date="2026-04-15")
        compute_delta(db, sample_jobs[:4], snapshot_date="2026-04-16")

        row = db.execute("SELECT * FROM jobs WHERE id = 1005").fetchone()
        assert row["is_active"] == 0
        assert row["removed_date"] == "2026-04-16"

    def test_last_seen_updated(self, db, sample_jobs):
        compute_delta(db, sample_jobs, snapshot_date="2026-04-15")
        compute_delta(db, sample_jobs, snapshot_date="2026-04-16")

        row = db.execute("SELECT * FROM jobs WHERE id = 1001").fetchone()
        assert row["last_seen"] == "2026-04-16"

    def test_empty_jobs_list(self, db):
        result = compute_delta(db, [], snapshot_date="2026-04-15")
        assert result.total == 0
        assert len(result.added) == 0


class TestEmptyFetchDoesNotWipe:
    """One malformed 200 used to mark every job removed, permanently.

    is_active was written in exactly two places: the schema default of 1, and the
    line that set it to 0. Nothing ever set it back, and the re-add path is
    INSERT OR IGNORE, so returning jobs were silently skipped. The board read
    zero forever while reporting the same jobs as "added" every single run.
    """

    def _job(self, jid: int, title: str) -> dict:
        return {
            "id": jid, "title": title, "location": {"name": "SF"},
            "absolute_url": "u", "internal_job_id": jid, "requisition_id": str(jid),
            "first_published": "2026-01-01",
            "departments": [{"id": 1, "name": "Eng"}], "offices": [],
        }

    def test_empty_payload_against_populated_db_raises(self, db) -> None:
        jobs = [self._job(1, "MTS"), self._job(2, "Sec")]
        compute_delta(db, jobs, "2026-08-20")
        with pytest.raises(ValueError, match="Refusing to compute a delta"):
            compute_delta(db, [], "2026-08-21")
        still_active = db.execute(
            "SELECT COUNT(*) FROM jobs WHERE is_active = 1"
        ).fetchone()[0]
        assert still_active == 2, "an empty fetch must not deactivate anything"

    def test_empty_payload_against_empty_db_is_allowed(self, db) -> None:
        """A genuinely empty first run is not an error."""
        result = compute_delta(db, [], "2026-08-20")
        assert result.total == 0

    def test_job_that_disappears_and_returns_is_reactivated(self, db) -> None:
        jobs = [self._job(1, "MTS"), self._job(2, "Sec")]
        compute_delta(db, jobs, "2026-08-20")
        compute_delta(db, [self._job(1, "MTS")], "2026-08-21")
        assert db.execute(
            "SELECT is_active FROM jobs WHERE id = 2"
        ).fetchone()[0] == 0
        compute_delta(db, jobs, "2026-08-22")
        row = db.execute(
            "SELECT is_active, removed_date FROM jobs WHERE id = 2"
        ).fetchone()
        assert row[0] == 1, "a returning job must be reactivated, not ignored"
        assert row[1] is None, "removed_date must be cleared on reactivation"
