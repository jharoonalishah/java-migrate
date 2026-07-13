"""Claude API integration — calls the AWS Bedrock proxy directly."""

import json
import os
import urllib.error
import urllib.request

from .detector import DetectionResult

# Proxy base: .../v1/model/{modelId}/invoke  (Bedrock InvokeModel format)
_BEDROCK_BASE_URL = (
    os.environ.get("ANTHROPIC_BEDROCK_BASE_URL", "")
    .rstrip("/")
)
_BEARER_TOKEN = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")

# Working model ID confirmed by probe
MODEL = os.environ.get("JAVA_MIGRATE_MODEL", "us.anthropic.claude-sonnet-4-6")

# Transformations available per Java version.
# Each entry is (minimum_java_version, description).
_TRANSFORMATIONS: list[tuple[int, str]] = [
    (8,  "Lambda expressions for anonymous Comparator / Runnable / single-method interfaces"),
    (8,  "`StringBuilder` instead of string concatenation in loops"),
    (9,  "`List.of` / `Map.of` / `Set.of` instead of `Collections.unmodifiable*`"),
    (11, "`var` for local variables with obvious types"),
    (14, "Switch expressions with `->` arrow syntax (use `yield` where needed)"),
    (15, "Text blocks (triple-quote) for multiline strings (HTML, SQL, JSON)"),
    (16, "`instanceof` pattern matching (`instanceof Foo f`) instead of cast"),
    (16, "`record` classes for simple POJOs with only getters/setters (no inheritance)"),
    (21, "Pattern matching in switch (`case String s ->`)"),
    (21, "Sequenced collections (`SequencedCollection`, `getFirst()`, `getLast()`)"),
    (25, "Primitive types in patterns and switch (`case int i ->`)"),
    (25, "`sealed` interfaces and classes with `permits` for closed type hierarchies"),
    (25, "Value classes (`value class`) for immutable data — only when class is already effectively immutable"),
    (25, "Structured concurrency (`StructuredTaskScope`) for parallel subtasks replacing manual `ExecutorService`"),
]

SUPPORTED_TARGETS = (11, 17, 21, 25)


def build_system_prompt(target: int) -> str:
    applicable = [desc for (min_ver, desc) in _TRANSFORMATIONS if min_ver <= target]
    numbered = "\n".join(f"{i+1}. {desc}" for i, desc in enumerate(applicable))
    return f"""You are an expert Java modernization engineer.
Your job is to upgrade legacy Java code to idiomatic Java {target}.

Rules:
- Apply ONLY the transformations listed below — do not refactor unrelated code.
- Preserve all existing logic, comments, and formatting outside the changed lines.
- Never add features, abstractions, or error handling that were not asked for.
- Do NOT use any Java feature introduced after Java {target}.
- Return the complete updated file content, nothing else.

Transformations to apply (only where safe and applicable):
{numbered}

After the migrated code, add a short section starting with exactly:
// === MIGRATION NOTES ===
Bullet-list every change you made, with the line numbers affected."""


def _invoke(model: str, payload: dict) -> dict:
    """Call the Bedrock InvokeModel endpoint and return the parsed JSON response."""
    if not _BEDROCK_BASE_URL:
        raise RuntimeError(
            "ANTHROPIC_BEDROCK_BASE_URL is not set. "
            "Export it before running java-migrate:\n"
            "  export ANTHROPIC_BEDROCK_BASE_URL=https://your-bedrock-proxy/v1"
        )
    if not _BEARER_TOKEN:
        raise RuntimeError(
            "AWS_BEARER_TOKEN_BEDROCK is not set. "
            "Export it before running java-migrate:\n"
            "  export AWS_BEARER_TOKEN_BEDROCK=your-token-here"
        )
    url = f"{_BEDROCK_BASE_URL}/model/{model}/invoke"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if _BEARER_TOKEN:
        req.add_header("Authorization", f"Bearer {_BEARER_TOKEN}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} from proxy: {body_text}") from e


def migrate(
    source: str,
    detection: DetectionResult,
    target: int = 17,
    client=None,  # unused, kept for CLI compatibility
) -> tuple[str, str]:
    """Send source to Claude via Bedrock proxy and return (migrated_code, notes)."""
    pattern_names = {f.pattern for f in detection.findings}
    patterns_hint = ", ".join(sorted(pattern_names)) if pattern_names else "general review"

    user_message = (
        f"File: {detection.file.name}\n"
        f"Detected patterns: {patterns_hint}\n\n"
        f"```java\n{source}\n```"
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8192,
        "system": build_system_prompt(target),
        "messages": [{"role": "user", "content": user_message}],
    }

    response = _invoke(MODEL, payload)

    full_text = ""
    for block in response.get("content", []):
        if block.get("type") == "text":
            full_text = block["text"]
            break

    marker = "// === MIGRATION NOTES ==="
    if marker in full_text:
        code_part, notes_part = full_text.split(marker, 1)
        code = _strip_fences(code_part.strip())
        notes = notes_part.strip()
    else:
        code = _strip_fences(full_text.strip())
        notes = ""

    return code, notes


def build_client():
    """No-op — kept so CLI import doesn't break."""
    return None


def _strip_fences(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
