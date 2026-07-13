"""Unit tests for the reporter."""

from pathlib import Path

from java_migrate.reporter import MigrationResult, generate_report


def _result(changed: bool, skipped: bool = False, error: str = "") -> MigrationResult:
    original = "class A { void old() {} }"
    migrated = "class A { void modern() {} }" if changed else original
    return MigrationResult(
        file=Path("A.java"),
        original=original,
        migrated=migrated,
        notes="- Renamed method" if changed else "",
        skipped=skipped,
        error=error,
    )


def test_report_includes_changed_file():
    report = generate_report([_result(changed=True)])
    assert "A.java" in report
    assert "```diff" in report


def test_report_skipped_shows_no_changes():
    report = generate_report([_result(changed=False, skipped=True)])
    assert "No migration needed" in report


def test_report_error_shows_message():
    report = generate_report([_result(changed=False, error="Permission denied")])
    assert "Permission denied" in report


def test_unified_diff_is_non_empty_when_changed():
    r = _result(changed=True)
    diff = r.unified_diff()
    assert "-" in diff or "+" in diff
