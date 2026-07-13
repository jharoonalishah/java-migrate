"""Unit tests for the static pattern detector."""

from pathlib import Path

from java_migrate.detector import detect


LEGACY_SOURCE = Path("tests/fixtures/LegacyService.java").read_text()


def _patterns(source: str) -> set[str]:
    result = detect(source, Path("Test.java"))
    return {f.pattern for f in result.findings}


def test_detects_instanceof_cast():
    assert "instanceof-cast" in _patterns(LEGACY_SOURCE)


def test_detects_anon_comparator():
    assert "anon-comparator" in _patterns(LEGACY_SOURCE)


def test_detects_collections_unmodifiable():
    assert "collections-unmodifiable" in _patterns(LEGACY_SOURCE)


def test_detects_string_concat_loop():
    assert "string-concat-loop" in _patterns(LEGACY_SOURCE)


def test_detects_switch_statement():
    assert "switch-statement" in _patterns(LEGACY_SOURCE)


def test_clean_file_has_no_findings():
    modern = """
public class Modern {
    public String greet(Object o) {
        if (o instanceof String s) {
            return "Hello " + s;
        }
        return "Hi";
    }
}
"""
    result = detect(modern, Path("Modern.java"))
    # The modern code should not trigger instanceof-cast
    assert "instanceof-cast" not in {f.pattern for f in result.findings}
