"""CLI entry point for java-migrate."""

import sys
from pathlib import Path

import click

from .detector import detect_file
from .migrator import SUPPORTED_TARGETS, build_client, migrate
from .reporter import MigrationResult, generate_report


def _collect_java_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix == ".java" else []
    return sorted(target.rglob("*.java"))


@click.command()
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Show diff without writing changes.")
@click.option("--report", "report_path", type=click.Path(path_type=Path), default=None,
              help="Write a markdown report to this path.")
@click.option("--verbose", "-v", is_flag=True, help="Show per-file diffs in the terminal.")
@click.option(
    "--target-version",
    "target_version",
    type=click.Choice([str(v) for v in SUPPORTED_TARGETS]),
    default="17",
    show_default=True,
    help="Java version to target.",
)
def main(target: Path, dry_run: bool, report_path: Path | None, verbose: bool, target_version: str) -> None:
    """Migrate legacy Java files to modern Java using Claude AI.

    TARGET can be a single .java file or a directory (searched recursively).
    """
    java_target = int(target_version)
    click.echo(f"Target: Java {java_target}")
    files = _collect_java_files(target)
    if not files:
        click.echo("No .java files found.", err=True)
        sys.exit(1)

    click.echo(f"Found {len(files)} Java file(s). Starting migration…")

    client = build_client()
    results: list[MigrationResult] = []

    with click.progressbar(files, label="Migrating", item_show_func=lambda p: p.name if p else "") as bar:
        for java_file in bar:
            try:
                original = java_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                results.append(MigrationResult(
                    file=java_file, original="", migrated="", notes="",
                    error=str(e),
                ))
                continue

            detection = detect_file(java_file)

            if not detection.needs_migration:
                results.append(MigrationResult(
                    file=java_file, original=original, migrated=original,
                    notes="", skipped=True,
                ))
                continue

            try:
                migrated_code, notes = migrate(original, detection, target=java_target, client=client)
            except Exception as e:  # noqa: BLE001
                results.append(MigrationResult(
                    file=java_file, original=original, migrated=original,
                    notes="", error=str(e),
                ))
                continue

            result = MigrationResult(
                file=java_file, original=original, migrated=migrated_code, notes=notes,
            )
            results.append(result)

            if not dry_run and result.changed:
                java_file.write_text(migrated_code, encoding="utf-8")

    # Summary
    changed = [r for r in results if r.changed]
    errors = [r for r in results if r.error]
    skipped = [r for r in results if r.skipped]

    click.echo()
    click.echo(f"✓ Changed : {len(changed)}")
    click.echo(f"– Skipped : {len(skipped)} (no patterns detected)")
    click.echo(f"✗ Errors  : {len(errors)}")
    if dry_run and changed:
        click.echo("  (dry-run: no files written)")

    if errors:
        click.echo("\nError details:", err=True)
        for r in errors:
            click.echo(f"  {r.file}: {r.error}", err=True)

    if verbose:
        for r in changed:
            click.echo(f"\n{'═'*60}")
            click.echo(f"  {r.file}")
            click.echo('═'*60)
            click.echo(r.inline_diff())
            if r.notes:
                click.echo(f"\n{r.notes}")

    if report_path:
        report_md = generate_report(results)
        report_path.write_text(report_md, encoding="utf-8")
        click.echo(f"\nReport written to: {report_path}")

    if errors:
        sys.exit(1)
