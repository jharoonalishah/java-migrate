# java-migrate

AI-powered CLI tool that upgrades legacy Java code to modern Java using Claude.

Point it at a file or directory and it rewrites outdated patterns to idiomatic Java 11, 17, 21, or 25 — showing you a diff before touching anything on disk.

---

## Table of Contents

- [What it does](#what-it-does)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Step-by-step usage](#step-by-step-usage)
- [All options](#all-options)
- [Java version targets](#java-version-targets)
- [How it works](#how-it-works)
- [Contributing](#contributing)

---

## What it does

Scans `.java` files for outdated patterns and rewrites them using Claude:

| Legacy pattern | Modern replacement | Min Java |
|---|---|---|
| `instanceof` + cast | Pattern matching (`instanceof Foo f`) | 16 |
| Switch statement | Switch expression (`->` syntax) | 14 |
| Anonymous `Comparator` | Lambda | 8 |
| `Collections.unmodifiableList/Map/Set` | `List.of` / `Map.of` / `Set.of` | 9 |
| String concatenation in loops | `StringBuilder` | 8 |
| Simple POJO with getters/setters | `record` | 16 |
| Multiline string building | Text block (triple-quote) | 15 |
| `var` for obvious local types | `var` | 11 |
| Pattern matching in switch | `case String s ->` | 21 |
| Sequenced collections | `getFirst()` / `getLast()` | 21 |
| Primitive patterns in switch | `case int i ->` | 25 |
| Closed type hierarchies | `sealed` + `permits` | 25 |

Only files that contain at least one detectable legacy pattern are sent to Claude — clean files are skipped at no cost.

---

## Requirements

- Python 3.11 or later
- [`pipx`](https://pipx.pypa.io) (recommended) or a Python virtual environment
- Access to the Claude API via an AWS Bedrock proxy

---

## Installation

### Option A — pipx (recommended for CLI tools)

`pipx` installs the tool in an isolated environment and adds it to your PATH permanently.

```bash
# Install pipx if you don't have it
brew install pipx
pipx ensurepath          # adds ~/.local/bin to PATH
# restart your terminal after this step

# Install java-migrate
pipx install /path/to/java-migrate
```

Verify the installation:

```bash
java-migrate --help
```

### Option B — virtual environment

```bash
cd /path/to/java-migrate
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

You will need to `source .venv/bin/activate` each time you open a new terminal.

---

## Configuration

The tool authenticates via environment variables. Set them in your shell profile (`~/.zshrc` or `~/.bash_profile`) so they are available in every session.

| Variable | Required | Description |
|---|---|---|
| `AWS_BEARER_TOKEN_BEDROCK` | **Yes** | Bearer token for the Claude API proxy |
| `ANTHROPIC_BEDROCK_BASE_URL` | **Yes** | Bedrock proxy base URL (e.g. `https://your-proxy/v1`) |
| `JAVA_MIGRATE_MODEL` | No | Override the Claude model ID (default: `us.anthropic.claude-sonnet-4-6`) |

### Setting the token

```bash
# Temporarily (current session only)
export AWS_BEARER_TOKEN_BEDROCK="your-token-here"

# Permanently (add to ~/.zshrc or ~/.bash_profile)
echo 'export AWS_BEARER_TOKEN_BEDROCK="your-token-here"' >> ~/.zshrc
source ~/.zshrc
```

---

## Step-by-step usage

### Step 1 — Set your API token

```bash
export AWS_BEARER_TOKEN_BEDROCK="your-token-here"
```

### Step 2 — Preview changes with a dry run

Always do a dry run first. No files are written; you just see what would change.

```bash
java-migrate MyClass.java --dry-run --verbose
```

For a whole source tree:

```bash
java-migrate ./src/main/java --dry-run --verbose
```

### Step 3 — Review the diff

The `--verbose` flag prints colour-coded additions (green) and removals (red) for every changed file. Check that the output looks correct before committing.

### Step 4 — Apply the migration

Once satisfied with the preview, run without `--dry-run`:

```bash
java-migrate MyClass.java --verbose
```

### Step 5 — Save a report (optional but recommended)

For large codebases, save a markdown report so you have a full record of every change:

```bash
java-migrate ./src/main/java --report migration-report.md
```

The report contains unified diffs and bullet-point migration notes for every file.

### Step 6 — Commit the result

```bash
git diff          # review one more time
git add -p        # stage interactively if you want to cherry-pick
git commit -m "chore: migrate to Java 17 via java-migrate"
```

### Full example

```bash
export AWS_BEARER_TOKEN_BEDROCK="your-bearer-token-here"

# Preview targeting Java 21
java-migrate ./src/main/java \
  --target-version 21 \
  --dry-run \
  --verbose \
  --report preview-report.md

# Apply when happy
java-migrate ./src/main/java \
  --target-version 21 \
  --report final-report.md
```

---

## All options

```
Usage: java-migrate [OPTIONS] TARGET

  Migrate legacy Java files to modern Java using Claude AI.

  TARGET can be a single .java file or a directory (searched recursively).

Options:
  --dry-run                       Show diff without writing changes.
  --report PATH                   Write a markdown report to this path.
  -v, --verbose                   Show per-file diffs in the terminal.
  --target-version [11|17|21|25]  Java version to target.  [default: 17]
  --help                          Show this message and exit.
```

---

## Java version targets

| `--target-version` | Transformations applied |
|---|---|
| `11` | Lambdas, `StringBuilder`, `List.of`, `var` |
| `17` | Everything in 11 + switch expressions, text blocks, `instanceof` patterns, `record` |
| `21` | Everything in 17 + switch pattern matching, sequenced collections |
| `25` | Everything in 21 + primitive patterns, `sealed` classes, value classes, structured concurrency |

Default is `17` — the most widely used LTS version in production.

---

## How it works

1. **Detect** — a fast regex scan checks each file for known legacy patterns. No API call is made for clean files.
2. **Skip** — files with no detectable patterns are marked skipped and left unchanged.
3. **Migrate** — detected files are sent to Claude with a system prompt tailored to the chosen target version.
4. **Apply** — migrated code replaces the original on disk (skipped in `--dry-run` mode).
5. **Report** — if `--report` is given, a markdown file is written with unified diffs and per-file migration notes.

---

## Contributing

Contributions are welcome. The codebase is intentionally small — four modules, no framework magic.

### Project layout

```
java-migrate/
├── src/java_migrate/
│   ├── cli.py        # click CLI — options, progress bar, summary
│   ├── detector.py   # regex-based legacy pattern scanner
│   ├── migrator.py   # Claude API call, prompt construction, response parsing
│   └── reporter.py   # unified diff and markdown report generation
├── tests/
│   ├── fixtures/     # sample .java files used by this library for testing
│   ├── test_detector.py
│   └── test_reporter.py
├── pyproject.toml
└── README.md
```

### Setting up a development environment

```bash
git clone <repo-url>
cd java-migrate

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"   # installs the package + pytest
```

### Running the tests

```bash
pytest tests/ -v
```

All tests run offline — no API token needed.

### Adding a new legacy pattern

1. **Add a regex** to the `PATTERNS` list in `detector.py`:
   ```python
   (
       "my-pattern-name",
       re.compile(r"<your regex here>"),
   ),
   ```

2. **Add a transformation description** to `_TRANSFORMATIONS` in `migrator.py`:
   ```python
   (17, "Description of what this transformation does"),
   ```
   The first value is the minimum Java version that supports it.

3. **Add a test** in `tests/test_detector.py`:
   ```python
   def test_detects_my_pattern():
       source = "... legacy code snippet ..."
       assert "my-pattern-name" in _patterns(source)
   ```

4. **Add a fixture** to `tests/fixtures/` if you need a realistic multi-pattern example.

### Changing the Claude model

Set `JAVA_MIGRATE_MODEL` to any model ID supported by your proxy:

```bash
export JAVA_MIGRATE_MODEL="us.anthropic.claude-opus-4-8"
java-migrate ./src --target-version 21
```

### Submitting a pull request

1. Fork the repository and create a branch: `git checkout -b feat/my-improvement`
2. Make your changes and add or update tests.
3. Run `pytest tests/ -v` and confirm all tests pass.
4. Open a pull request with a clear description of what changed and why.

Please keep pull requests focused — one feature or fix per PR makes review faster.

### Reporting bugs

Open an issue and include:
- The command you ran
- The Java file (or a minimal reproduction)
- The error output (run with `ANTHROPIC_LOG=debug` for full detail)
