"""Diff generation and markdown report output."""

import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MigrationResult:
    file: Path
    original: str
    migrated: str
    notes: str
    skipped: bool = False
    error: str = ""

    @property
    def changed(self) -> bool:
        return self.original != self.migrated

    def unified_diff(self) -> str:
        original_lines = self.original.splitlines(keepends=True)
        migrated_lines = self.migrated.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines,
            migrated_lines,
            fromfile=f"a/{self.file.name}",
            tofile=f"b/{self.file.name}",
        )
        return "".join(diff)

    def inline_diff(self) -> str:
        """Side-by-side style for terminal display (additions/removals only)."""
        original_lines = self.original.splitlines()
        migrated_lines = self.migrated.splitlines()
        matcher = difflib.SequenceMatcher(None, original_lines, migrated_lines)
        out: list[str] = []
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                continue
            if op in ("replace", "delete"):
                for line in original_lines[i1:i2]:
                    out.append(f"\033[31m- {line}\033[0m")
            if op in ("replace", "insert"):
                for line in migrated_lines[j1:j2]:
                    out.append(f"\033[32m+ {line}\033[0m")
        return "\n".join(out)


def generate_report(results: list[MigrationResult]) -> str:
    """Return a markdown string summarising all migration results."""
    lines: list[str] = [
        "# Java Migration Report",
        "",
        f"**Files processed:** {len(results)}",
        f"**Files changed:** {sum(1 for r in results if r.changed)}",
        f"**Files skipped:** {sum(1 for r in results if r.skipped)}",
        f"**Errors:** {sum(1 for r in results if r.error)}",
        "",
    ]

    for result in results:
        lines.append(f"## `{result.file}`")
        if result.error:
            lines += ["", f"> **Error:** {result.error}", ""]
            continue
        if result.skipped:
            lines += ["", "> No migration needed.", ""]
            continue
        if not result.changed:
            lines += ["", "> Claude returned identical code — no changes applied.", ""]
            continue

        lines += [
            "",
            "### Changes",
            "",
            "```diff",
            result.unified_diff(),
            "```",
            "",
        ]
        if result.notes:
            lines += [
                "### Migration Notes",
                "",
                result.notes,
                "",
            ]

    return "\n".join(lines)
