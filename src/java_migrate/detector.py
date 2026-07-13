"""Static pattern detection — identifies legacy Java constructs before sending to Claude."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Finding:
    pattern: str
    line: int
    snippet: str


@dataclass
class DetectionResult:
    file: Path
    findings: list[Finding] = field(default_factory=list)

    @property
    def needs_migration(self) -> bool:
        return len(self.findings) > 0

    @property
    def summary(self) -> str:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.pattern] = counts.get(f.pattern, 0) + 1
        return ", ".join(f"{v}x {k}" for k, v in counts.items())


# Each entry: (pattern_name, compiled_regex)
PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "instanceof-cast",
        re.compile(r"\bif\s*\(\s*\w+\s+instanceof\s+(\w+)\s*\)\s*\{?\s*\n?\s*\w+\s+\w+\s*=\s*\(\1\)"),
    ),
    (
        "anon-comparator",
        re.compile(r"new\s+Comparator\s*<[^>]+>\s*\(\s*\)\s*\{"),
    ),
    (
        "old-for-loop",
        re.compile(r"\bfor\s*\(\s*int\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*\w+\.size\(\)\s*;"),
    ),
    (
        "string-concat-loop",
        re.compile(r"\bString\s+\w+\s*=\s*\"\";\s*\n(?:.*\n)*?.*\w+\s*\+="),
    ),
    (
        "collections-unmodifiable",
        re.compile(r"Collections\.(unmodifiableList|unmodifiableMap|unmodifiableSet)\s*\("),
    ),
    (
        "switch-statement",
        re.compile(r"\bswitch\s*\([^)]+\)\s*\{[^}]*\bcase\b", re.DOTALL),
    ),
    (
        "optional-null-check",
        re.compile(r"if\s*\(\s*\w+\s*==\s*null\s*\)"),
    ),
    (
        "pojo-getters-setters",
        re.compile(r"public\s+(?:void\s+set\w+|[\w<>]+\s+get\w+)\s*\("),
    ),
]


def detect(source: str, file: Path) -> DetectionResult:
    result = DetectionResult(file=file)
    lines = source.splitlines()

    for name, pattern in PATTERNS:
        for match in pattern.finditer(source):
            # Find the 1-indexed line number of this match
            line_num = source[: match.start()].count("\n") + 1
            snippet = lines[line_num - 1].strip()[:120]
            result.findings.append(Finding(pattern=name, line=line_num, snippet=snippet))

    return result


def detect_file(path: Path) -> DetectionResult:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        result = DetectionResult(file=path)
        result.findings.append(
            Finding(pattern="read-error", line=0, snippet=str(e))
        )
        return result
    return detect(source, path)
