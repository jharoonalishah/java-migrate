---
title: "I Built an AI-Powered CLI That Migrates Legacy Java Code to Java 17/21/25"
published: false
description: "How I combined Claude AI with Python to build java-migrate — a CLI tool that automatically modernises legacy Java 8/11 codebases to idiomatic modern Java."
tags: java, ai, python, opensource
cover_image:
---

# I Built an AI-Powered CLI That Migrates Legacy Java Code to Java 17/21/25

If you've spent any time in enterprise Java, you know the feeling. You open a service that's been running since 2014 and you're greeted by walls of anonymous inner classes, verbose null checks, `Collections.unmodifiableList` wrapping a `new ArrayList`, and switch statements with more `break` keywords than actual logic.

Individually each pattern takes 30 seconds to fix. But across a codebase with 300 files, it's a week of mechanical work — and that's before you factor in the code review.

So I built **java-migrate**: a CLI tool that scans your Java files, detects legacy patterns, and sends them to Claude with a precise system prompt to get them modernised. One command, instant diff, no surprises.

---

## What it looks like in practice

Here's a typical legacy file before migration:

```java
public class LegacyService {

    // POJO with getters/setters
    public static class User {
        private String name;
        private int age;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public int getAge() { return age; }
        public void setAge(int age) { this.age = age; }
    }

    public List<User> sortUsers(List<User> users) {
        // Anonymous Comparator
        users.sort(new Comparator<User>() {
            @Override
            public int compare(User a, User b) {
                return a.getName().compareTo(b.getName());
            }
        });
        return Collections.unmodifiableList(users);
    }

    public String describeObject(Object obj) {
        // instanceof + cast
        if (obj instanceof String) {
            String s = (String) obj;
            return "String of length " + s.length();
        }
        return "Unknown";
    }

    public String classify(int value) {
        // switch statement
        String result;
        switch (value) {
            case 1: result = "one"; break;
            case 2: result = "two"; break;
            default: result = "other";
        }
        return result;
    }
}
```

Run `java-migrate LegacyService.java --dry-run --verbose` and you get this diff:

```diff
-    public static class User {
-        private String name;
-        private int age;
-        public String getName() { return name; }
-        public void setName(String name) { this.name = name; }
-        public int getAge() { return age; }
-        public void setAge(int age) { this.age = age; }
-    }
+    public record User(String name, int age) {}

-        users.sort(new Comparator<User>() {
-            @Override
-            public int compare(User a, User b) {
-                return a.getName().compareTo(b.getName());
-            }
-        });
-        return Collections.unmodifiableList(users);
+        users.sort((a, b) -> a.name().compareTo(b.name()));
+        return List.copyOf(users);

-        if (obj instanceof String) {
-            String s = (String) obj;
+        if (obj instanceof String s) {

-        String result;
-        switch (value) {
-            case 1: result = "one"; break;
-            case 2: result = "two"; break;
-            default: result = "other";
-        }
-        return result;
+        return switch (value) {
+            case 1 -> "one";
+            case 2 -> "two";
+            default -> "other";
+        };
```

And it includes migration notes explaining every change with the line numbers affected. Nothing is written to disk until you remove `--dry-run`.

---

## The architecture

The tool has four modules, each with a single responsibility:

```
src/java_migrate/
├── cli.py        # click CLI — options, progress bar, summary
├── detector.py   # regex-based legacy pattern scanner
├── migrator.py   # Claude API call, prompt construction, response parsing
└── reporter.py   # unified diff and markdown report generation
```

### 1. Fast static detection (no AI cost for clean files)

Before calling Claude, a regex scanner checks each file for known legacy patterns:

```python
PATTERNS = [
    ("instanceof-cast",
     re.compile(r"\bif\s*\(\s*\w+\s+instanceof\s+(\w+)\s*\)\s*\{?\s*\n?\s*\w+\s+\w+\s*=\s*\(\1\)")),
    ("anon-comparator",
     re.compile(r"new\s+Comparator\s*<[^>]+>\s*\(\s*\)\s*\{")),
    ("collections-unmodifiable",
     re.compile(r"Collections\.(unmodifiableList|unmodifiableMap|unmodifiableSet)\s*\(")),
    # ... more patterns
]
```

Files with no matches are skipped entirely — no API call, no cost, no latency. On a typical codebase, 40–60% of files are already clean.

### 2. Version-aware prompt construction

The system prompt changes based on the `--target-version` flag. Each transformation is tagged with the minimum Java version that supports it:

```python
_TRANSFORMATIONS = [
    (8,  "Lambda expressions for anonymous Comparator / Runnable"),
    (9,  "`List.of` / `Map.of` instead of `Collections.unmodifiable*`"),
    (14, "Switch expressions with `->` arrow syntax"),
    (16, "`instanceof` pattern matching (`instanceof Foo f`)"),
    (16, "`record` classes for simple POJOs"),
    (21, "Pattern matching in switch (`case String s ->`)"),
    (25, "`sealed` interfaces with `permits` for closed hierarchies"),
    # ...
]

def build_system_prompt(target: int) -> str:
    applicable = [desc for (min_ver, desc) in _TRANSFORMATIONS if min_ver <= target]
    # build prompt with only the applicable transformations
```

Targeting Java 11? Claude is told not to use records or pattern matching. Targeting Java 25? It gets the full list including sealed classes and structured concurrency.

### 3. Calling Claude

The tool uses the Bedrock InvokeModel API format with a bearer token:

```python
def _invoke(model: str, payload: dict) -> dict:
    url = f"{BEDROCK_BASE_URL}/model/{model}/invoke"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {BEARER_TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())
```

The system prompt is strict: return only the updated file, then a `// === MIGRATION NOTES ===` section with bullet points. The response is split on that marker so the notes are stored separately from the code.

### 4. Diff and report

The reporter uses Python's built-in `difflib` to generate both a coloured terminal diff for `--verbose` mode and a unified diff for the markdown report:

```python
def unified_diff(self) -> str:
    return "".join(difflib.unified_diff(
        self.original.splitlines(keepends=True),
        self.migrated.splitlines(keepends=True),
        fromfile=f"a/{self.file.name}",
        tofile=f"b/{self.file.name}",
    ))
```

---

## What transformations are supported

| Legacy pattern | Modern replacement | Min Java |
|---|---|---|
| `instanceof` + cast | Pattern matching (`instanceof Foo f`) | 16 |
| Switch statement | Switch expression (`->`) | 14 |
| Anonymous `Comparator` | Lambda | 8 |
| `Collections.unmodifiableList` | `List.of` / `List.copyOf` | 9 |
| String concat in loops | `StringBuilder` | 8 |
| POJO with getters/setters | `record` | 16 |
| Multiline string building | Text block | 15 |
| `var` for obvious locals | `var` | 11 |
| Pattern matching in switch | `case String s ->` | 21 |
| Sequenced collections | `getFirst()` / `getLast()` | 21 |
| Primitive patterns | `case int i ->` | 25 |
| Closed type hierarchies | `sealed` + `permits` | 25 |

---

## Why not just use OpenRewrite?

[OpenRewrite](https://docs.openrewrite.org/) is excellent and you should use it for structural refactoring — it has a proper AST, handles edge cases that regex can't, and has a huge library of recipes.

java-migrate is different in two ways:

1. **It's AI-driven** — the transformations are applied by Claude, which means it handles context and nuance that a fixed recipe can't. Converting a POJO to a `record` requires updating every call site from `getName()` to `name()`, something a regex recipe can't reliably do. Claude handles the whole file at once.

2. **It's zero-configuration** — no Gradle/Maven plugin, no YAML config, no build system integration needed. Point it at any directory and it works.

The two tools are complementary. Use OpenRewrite for structural migrations (Spring Boot upgrades, API changes, dependency updates). Use java-migrate for the mechanical Java language modernisation layer on top.

---

## Installation and quick start

```bash
# Install permanently with pipx
brew install pipx && pipx ensurepath
pipx install /path/to/java-migrate

# Set your API token
export ANTHROPIC_BEDROCK_BASE_URL="https://your-bedrock-proxy/v1"
export AWS_BEARER_TOKEN_BEDROCK="your-bearer-token-here"

# Preview what would change (nothing written to disk)
java-migrate ./src/main/java --target-version 17 --dry-run --verbose

# Apply when satisfied
java-migrate ./src/main/java --target-version 17 --report migration-report.md
```

Supported targets: `11`, `17` (default), `21`, `25`.

---

## Lessons learned building this

**Two-stage pipelines save money.** The regex pre-filter was the best decision in the whole project. On a 200-file codebase where 100 files are already clean, you cut your API cost in half before writing a single line of prompt engineering.

**Strict output format is non-negotiable.** The first version just asked Claude to "return the migrated code." The responses were inconsistent — sometimes with explanatory prose, sometimes with fences, sometimes without. Adding `// === MIGRATION NOTES ===` as a required marker and splitting on it made parsing deterministic.

**The proxy URL cost two hours.** My API endpoint was `…/v1` and the Anthropic SDK appends `/v1/messages` automatically, giving `…/v1/v1/messages`. The debug log line `Sending HTTP Request: POST …/v1/v1/messages` made it obvious once I looked, but I spent a long time looking at the wrong thing first. Always print the full request URL when debugging API calls.

**Version-gating the prompt is more important than you'd think.** Without it, Claude would occasionally use a Java 17 feature when the target was Java 11 — it just knew the better way to write the code. Making the target version explicit in the prompt and listing only the applicable transformations solved it.

---

## What's next

A few things I want to add:

- **`--since-commit` flag** — only migrate files changed since a given git commit, useful for incremental adoption
- **Parallel file processing** — currently files are processed sequentially; concurrent API calls would make a big difference on large codebases
- **IntelliJ / VS Code extension** — right-click a file → Migrate to Java 21
- **GitHub Action** — run on PRs to flag legacy patterns as review comments

The codebase is small and intentionally simple. If you want to add a new pattern or a new transformation, it's literally adding two lines in two files.

The project is on GitHub at [link]. PRs welcome.

---

*Have you migrated a large Java codebase recently? What was the most painful part? I'm curious whether the patterns I've targeted match what people actually encounter — drop a comment below.*
