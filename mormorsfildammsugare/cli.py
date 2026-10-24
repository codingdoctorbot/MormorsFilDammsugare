"""CLI Interface for MormorsFilDammsugare."""

import argparse
from pathlib import Path
import sys

from .modules.document_devourer import DocumentDevourer, DocumentDevourerOptions, DocumentDevourerStats
from .modules.photo_sorter import PhotoSorter, PhotoSorterOptions, PhotoSorterStats
from .modules.privacy_scanner import PrivacyScanner, PrivacyScannerOptions, PrivacyScanStats
from .modules.sampler import FileSampler, SurveyStats, format_bytes
from .privacy.vault import VaultService

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False


def print_rich_report(stats: SurveyStats, console: Console):
    """Render a beautiful terminal report using Rich."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold magenta]👵 MormorsFilDammsugare[/bold magenta] — [cyan]Filedump Sampler & Survey[/cyan]\n"
            f"[dim]Survey of:[/dim] [yellow]{stats.target_path}[/yellow]\n"
            f"[dim]Scanned in:[/dim] [green]{stats.scan_time_seconds:.2f}s[/green]  |  "
            f"[dim]Total Files:[/dim] [bold]{stats.total_files:,}[/bold]  |  "
            f"[dim]Total Size:[/dim] [bold green]{format_bytes(stats.total_bytes)}[/bold green]",
            border_style="magenta",
        )
    )

    # 1. Categories Table
    cat_table = Table(title="📁 Content Category Breakdown", border_style="cyan")
    cat_table.add_column("Category", style="bold")
    cat_table.add_column("Files", justify="right")
    cat_table.add_column("% Files", justify="right")
    cat_table.add_column("Size", justify="right", style="green")
    cat_table.add_column("% Size", justify="right")

    sorted_cats = sorted(stats.category_bytes.items(), key=lambda x: x[1], reverse=True)
    for cat_name, b in sorted_cats:
        cnt = stats.category_counts[cat_name]
        pct_files = (cnt / stats.total_files * 100) if stats.total_files else 0
        pct_bytes = (b / stats.total_bytes * 100) if stats.total_bytes else 0
        cat_table.add_row(
            cat_name,
            f"{cnt:,}",
            f"{pct_files:.1f}%",
            format_bytes(b),
            f"{pct_bytes:.1f}%",
        )
    console.print(cat_table)
    console.print()

    # 2. Top Formats Table
    fmt_table = Table(title="🔍 Detected File Formats (by content header)", border_style="blue")
    fmt_table.add_column("Format", style="bold")
    fmt_table.add_column("Files", justify="right")
    fmt_table.add_column("Total Size", justify="right", style="green")

    sorted_fmts = sorted(stats.format_bytes.items(), key=lambda x: x[1], reverse=True)[:10]
    for fmt_name, b in sorted_fmts:
        cnt = stats.format_counts[fmt_name]
        fmt_table.add_row(fmt_name, f"{cnt:,}", format_bytes(b))
    console.print(fmt_table)
    console.print()

    # 3. Size Histogram
    hist_table = Table(title="📊 File Size Distribution", border_style="yellow")
    hist_table.add_column("Size Range", style="bold")
    hist_table.add_column("Count", justify="right")
    hist_table.add_column("Total Space", justify="right", style="green")

    for bucket, cnt in stats.size_buckets.items():
        hist_table.add_row(bucket, f"{cnt:,}", format_bytes(stats.size_bucket_bytes[bucket]))
    console.print(hist_table)
    console.print()

    # 4. Critical Findings & Duplicates Panel
    findings = []
    if stats.estimated_duplicate_files > 0:
        findings.append(
            f"⚡ [bold red]Duplicate Clutter:[/bold red] Found approx. [bold]{stats.estimated_duplicate_files:,}[/bold] "
            f"duplicate copies wasting [bold red]{format_bytes(stats.estimated_wasted_bytes)}[/bold red]!"
        )
    else:
        findings.append("✨ [green]Duplicates:[/green] No obvious duplicate file waste detected.")

    if stats.mismatches:
        findings.append(
            f"🎭 [bold yellow]Disguised / Misnamed Files:[/bold yellow] [bold]{len(stats.mismatches)}[/bold] files have "
            f"extensions that disagree with their binary content:"
        )
        for m in stats.mismatches[:5]:
            findings.append(f"   • [dim]{m.path.name}[/dim] (has [red]{m.actual_ext}[/red], but is actually [green]{m.detected_format}[/green])")
        if len(stats.mismatches) > 5:
            findings.append(f"   [dim]... and {len(stats.mismatches) - 5} more.[/dim]")

    if stats.zero_byte_files > 0:
        findings.append(f"⚠️ [dim]Zero-byte empty files:[/dim] {stats.zero_byte_files:,}")

    console.print(
        Panel(
            "\n".join(findings),
            title="[bold yellow]Triage Insights[/bold yellow]",
            border_style="yellow",
        )
    )
    console.print()


def print_plain_report(stats: SurveyStats):
    """Fallback plain-text terminal report."""
    print("=" * 60)
    print("MormorsFilDammsugare — Filedump Sampler & Survey")
    print(f"Target: {stats.target_path}")
    print(f"Scanned {stats.total_files:,} files ({format_bytes(stats.total_bytes)}) in {stats.scan_time_seconds:.2f}s")
    print("=" * 60)
    print("\n[Categories]")
    for cat, b in sorted(stats.category_bytes.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat:22}: {stats.category_counts[cat]:>6,} files ({format_bytes(b)})")
    print("\n[Top Formats]")
    for fmt, b in sorted(stats.format_bytes.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"  {fmt:22}: {stats.format_counts[fmt]:>6,} files ({format_bytes(b)})")
    if stats.estimated_duplicate_files > 0:
        print(f"\n[Duplicates] ~{stats.estimated_duplicate_files:,} duplicate copies wasting {format_bytes(stats.estimated_wasted_bytes)}")
    if stats.mismatches:
        print(f"\n[Disguised Files] {len(stats.mismatches)} files with mismatched extensions")


def handle_survey(args):
    target = Path(args.path).resolve()
    if not target.exists() or not target.is_dir():
        print(f"Error: Target directory does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    sampler = FileSampler(check_duplicates=not args.no_dupes)

    if HAVE_RICH:
        console = Console()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]Surveying {target.name}...[/cyan]", total=None)
            def update(count):
                progress.update(task, description=f"[cyan]Surveying {target.name}... ({count:,} files)[/cyan]")
            stats = sampler.survey(target, progress_callback=update)
        print_rich_report(stats, console)
    else:
        print(f"Surveying {target}...")
        stats = sampler.survey(target)
        print_plain_report(stats)

    if args.export_json:
        out_path = Path(args.export_json)
        data = {
            "target": str(stats.target_path),
            "scan_time_seconds": stats.scan_time_seconds,
            "total_files": stats.total_files,
            "total_bytes": stats.total_bytes,
            "categories": {cat: {"count": stats.category_counts[cat], "bytes": stats.category_bytes[cat]} for cat in stats.category_counts},
            "formats": {fmt: {"count": stats.format_counts[fmt], "bytes": stats.format_bytes[fmt]} for fmt in stats.format_counts},
            "estimated_duplicate_files": stats.estimated_duplicate_files,
            "estimated_wasted_bytes": stats.estimated_wasted_bytes,
            "mismatches_count": len(stats.mismatches),
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Saved survey report to: {out_path}")


def handle_photos(args):
    dest = Path(args.dest).resolve()
    sources = [Path(s).resolve() for s in args.sources]

    for s in sources:
        if not s.exists():
            print(f"Error: Source path does not exist: {s}", file=sys.stderr)
            sys.exit(1)

    options = PhotoSorterOptions(
        source_dirs=sources,
        dest_dir=dest,
        layout=args.layout,
        is_move=args.move,
        dry_run=args.dry_run,
    )

    sorter = PhotoSorter(options)

    if HAVE_RICH:
        console = Console()
        console.print(
            Panel.fit(
                f"[bold magenta]👵 MormorsFilDammsugare[/bold magenta] — [cyan]Photo & Video Sorter[/cyan]\n"
                f"[dim]Sources:[/dim] [yellow]{', '.join(str(s) for s in sources)}[/yellow]\n"
                f"[dim]Destination:[/dim] [green]{dest}[/green]\n"
                f"[dim]Layout:[/dim] [blue]{args.layout}[/blue]  |  "
                f"[dim]Mode:[/dim] [bold red]{'MOVE' if args.move else 'COPY'}[/bold red]"
                f"{'  (DRY RUN)' if args.dry_run else ''}",
                border_style="magenta",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Scanning & organizing media...[/cyan]", total=None)
            def update(current_file, count):
                progress.update(task, description=f"[cyan]Processed {count:,} items ({current_file[:25]}...)[/cyan]")
            stats = sorter.organize(progress_callback=update)

        console.print()
        table = Table(title="🎉 Organization Complete", border_style="green")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right", style="cyan")

        table.add_row("Total Files Scanned", f"{stats.total_scanned:,}")
        table.add_row("Photos Organized", f"{stats.photos_processed:,}")
        table.add_row("Videos Organized", f"{stats.videos_processed:,}")
        table.add_row("Duplicates Skipped", f"{stats.duplicates_skipped:,}")
        table.add_row("Data Transferred", format_bytes(stats.bytes_transferred))
        if args.move:
            table.add_row("Originals Removed", f"{stats.originals_removed:,}")
        console.print(table)

        if stats.errors:
            console.print(f"[bold yellow]Warnings / Errors ({len(stats.errors)}):[/bold yellow]")
            for err in stats.errors[:5]:
                console.print(f"  • [dim]{err}[/dim]")
    else:
        print(f"Organizing photos to {dest}...")
        stats = sorter.organize()
        print(f"Done! Photos: {stats.photos_processed:,}, Videos: {stats.videos_processed:,}, Duplicates: {stats.duplicates_skipped:,}")


def handle_restore_photos(args):
    dest = Path(args.dest).resolve()
    if not dest.exists():
        print(f"Error: Destination folder does not exist: {dest}", file=sys.stderr)
        sys.exit(1)

    if HAVE_RICH:
        console = Console()
        with console.status("[bold cyan]Restoring originals from catalog...[/bold cyan]"):
            restored = PhotoSorter.restore_originals(dest)
        console.print(f"[bold green]✓ Restored {restored:,} original files back to their source paths.[/bold green]")
    else:
        print("Restoring originals...")
        restored = PhotoSorter.restore_originals(dest)
        print(f"Restored {restored:,} original files.")


def handle_docs(args):
    dest = Path(args.dest).resolve()
    sources = [Path(s).resolve() for s in args.sources]

    for s in sources:
        if not s.exists():
            print(f"Error: Source path does not exist: {s}", file=sys.stderr)
            sys.exit(1)

    options = DocumentDevourerOptions(
        source_dirs=sources,
        dest_dir=dest,
        extract_all_formats=args.all_formats,
        trust_file_times=args.trust_file_dates,
        is_move=args.move,
        dry_run=args.dry_run,
    )

    devourer = DocumentDevourer(options)

    if HAVE_RICH:
        console = Console()
        console.print(
            Panel.fit(
                f"[bold magenta]👵 MormorsFilDammsugare[/bold magenta] — [cyan]Document Devourer[/cyan]\n"
                f"[dim]Sources:[/dim] [yellow]{', '.join(str(s) for s in sources)}[/yellow]\n"
                f"[dim]Destination:[/dim] [green]{dest}[/green]\n"
                f"[dim]Mode:[/dim] [bold red]{'MOVE' if args.move else 'COPY'}[/bold red]"
                f"{'  (DRY RUN)' if args.dry_run else ''}",
                border_style="magenta",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Devouring documents...[/cyan]", total=None)
            def update(current_file, count):
                progress.update(task, description=f"[cyan]Devoured {count:,} items ({current_file[:25]}...)[/cyan]")
            stats = devourer.devour(progress_callback=update)

        console.print()
        table = Table(title="📄 Document Extraction Complete", border_style="green")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right", style="cyan")

        table.add_row("Total Files Scanned", f"{stats.total_scanned:,}")
        table.add_row("Documents Organized", f"{stats.documents_processed:,}")
        table.add_row("Duplicates Skipped", f"{stats.duplicates_skipped:,}")
        table.add_row("Data Transferred", format_bytes(stats.bytes_transferred))
        if args.move:
            table.add_row("Originals Removed", f"{stats.originals_removed:,}")
        console.print(table)

        if stats.category_counts:
            console.print()
            cat_table = Table(title="📂 Categories", border_style="blue")
            cat_table.add_column("Category", style="bold")
            cat_table.add_column("Documents", justify="right")
            for cat, cnt in sorted(stats.category_counts.items(), key=lambda x: x[1], reverse=True):
                cat_table.add_row(cat, f"{cnt:,}")
            console.print(cat_table)
    else:
        print(f"Extracting documents to {dest}...")
        stats = devourer.devour()
        print(f"Done! Documents: {stats.documents_processed:,}, Duplicates: {stats.duplicates_skipped:,}")


def handle_restore_docs(args):
    dest = Path(args.dest).resolve()
    if not dest.exists():
        print(f"Error: Destination folder does not exist: {dest}", file=sys.stderr)
        sys.exit(1)

    if HAVE_RICH:
        console = Console()
        with console.status("[bold cyan]Restoring original documents from catalog...[/bold cyan]"):
            restored = PhotoSorter.restore_originals(dest)
        console.print(f"[bold green]✓ Restored {restored:,} original documents back to their source paths.[/bold green]")
    else:
        print("Restoring original documents...")
        restored = PhotoSorter.restore_originals(dest)
        print(f"Restored {restored:,} original documents.")


def handle_audit(args):
    sources = [Path(s).resolve() for s in args.sources]
    for s in sources:
        if not s.exists():
            print(f"Error: Source path does not exist: {s}", file=sys.stderr)
            sys.exit(1)

    options = PrivacyScannerOptions(
        source_dirs=sources,
        min_confidence=args.min_conf,
        strict_only=args.strict,
        include_suggestive=args.suggestive,
        quarantine_flagged=args.quarantine,
        model_name=args.model,
    )

    scanner = PrivacyScanner(options)

    if HAVE_RICH:
        console = Console()
        console.print(
            Panel.fit(
                f"[bold magenta]👵 MormorsFilDammsugare[/bold magenta] — [cyan]Privacy & Loaner Audit[/cyan]\n"
                f"[dim]Sources:[/dim] [yellow]{', '.join(str(s) for s in sources)}[/yellow]\n"
                f"[dim]Model:[/dim] [blue]{args.model}[/blue]  |  "
                f"[dim]Min Confidence:[/dim] [blue]{args.min_conf:.2f}[/blue]  |  "
                f"[dim]Action:[/dim] [bold red]{'QUARANTINE TO VAULT' if args.quarantine else 'AUDIT REPORT ONLY'}[/bold red]",
                border_style="magenta",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running AI privacy scan...[/cyan]", total=None)
            def update(current_file, count):
                progress.update(task, description=f"[cyan]Audited {count:,} images ({current_file[:25]}...)[/cyan]")
            stats = scanner.scan(progress_callback=update)

        console.print()
        if not stats.flagged_files:
            console.print("[bold green]✓ Clean! Zero explicit or sensitive items detected.[/bold green]")
        else:
            table = Table(title=f"⚠️ Flagged Items ({len(stats.flagged_files)} detected)", border_style="red")
            table.add_column("File", style="bold")
            table.add_column("Detected Classes", style="yellow")
            table.add_column("Max Conf", justify="right", style="cyan")
            table.add_column("Status", justify="center", style="bold red")

            for res in stats.flagged_files:
                classes_str = ", ".join(f"{d.friendly_name} ({d.confidence:.2f})" for d in res.detections[:3])
                status = "Quarantined" if args.quarantine else "Flagged"
                table.add_row(res.filepath.name, classes_str, f"{res.max_confidence:.2f}", status)
            console.print(table)

            if args.quarantine:
                console.print(f"\n[bold green]✓ Successfully moved {len(stats.quarantined_records)} items to the Vault.[/bold green]")
                console.print(f"[dim]Vault location: {scanner.vault.vault_dir}[/dim]")
    else:
        print(f"Auditing {sources}...")
        stats = scanner.scan()
        print(f"Done! Scanned {stats.total_scanned:,} images. Flagged: {len(stats.flagged_files):,}")


def handle_vault(args):
    vault = VaultService()
    if HAVE_RICH:
        console = Console()
        if args.vault_action == "list":
            entries = vault.list_entries()
            if not entries:
                console.print("[dim]Vault is empty. No quarantined items.[/dim]")
                return
            table = Table(title=f"🔒 Quarantined Vault Items ({len(entries)})", border_style="yellow")
            table.add_column("ID", style="dim")
            table.add_column("Original Filename", style="bold")
            table.add_column("Size", justify="right", style="green")
            table.add_column("Quarantined At", style="cyan")
            for e in entries:
                table.add_row(e.id[:8], e.filename, format_bytes(e.size), e.quarantined_at[:19])
            console.print(table)
        elif args.vault_action == "restore":
            target = vault.restore(args.id)
            if target:
                console.print(f"[bold green]✓ Restored to: {target}[/bold green]")
            else:
                console.print(f"[bold red]Item not found: {args.id}[/bold red]")
        elif args.vault_action == "purge":
            if vault.purge(args.id):
                console.print(f"[bold red]Permanently deleted item: {args.id}[/bold red]")
            else:
                console.print(f"[bold red]Item not found: {args.id}[/bold red]")
    else:
        print(f"Vault action: {args.vault_action}")


def main():
    parser = argparse.ArgumentParser(
        prog="mormor",
        description="👵 MormorsFilDammsugare: The Ultimate Backup Triage & File Vacuum Suite",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: gui
    p_gui = subparsers.add_parser("gui", help="Launch the Desktop GUI window")
    def handle_gui(args):
        from .gui.app import run_gui
        run_gui()
    p_gui.set_defaults(func=handle_gui)

    # Command: survey / sample
    p_survey = subparsers.add_parser("survey", aliases=["sample"], help="Survey a folder or drive dump (The Sampler)")
    p_survey.add_argument("path", help="Path to folder or drive to survey")
    p_survey.add_argument("--no-dupes", action="store_true", help="Skip duplicate calculation for fastest scan")
    p_survey.add_argument("--export-json", help="Export survey results to JSON file")
    p_survey.set_defaults(func=handle_survey)

    # Command: photos
    p_photos = subparsers.add_parser("photos", help="Extract, deduplicate and organize photos & videos")
    p_photos.add_argument("sources", nargs="+", help="One or more source folders")
    p_photos.add_argument("--dest", required=True, help="Destination directory for organized media")
    p_photos.add_argument("--layout", choices=["continent_year", "country_year", "region_year"], default="continent_year", help="Folder tree layout")
    p_photos.add_argument("--move", action="store_true", help="Move mode: safely remove originals after copy verification")
    p_photos.add_argument("--dry-run", action="store_true", help="Simulate run without copying any files")
    p_photos.set_defaults(func=handle_photos)

    # Command: restore-photos
    p_restore = subparsers.add_parser("restore-photos", help="Restore removed originals back to their sources")
    p_restore.add_argument("--dest", required=True, help="Destination directory containing catalog.db")
    p_restore.set_defaults(func=handle_restore_photos)

    # Command: docs
    p_docs = subparsers.add_parser("docs", help="Extract, deduplicate and categorize documents (PDF, Office, etc.)")
    p_docs.add_argument("sources", nargs="+", help="One or more source folders")
    p_docs.add_argument("--dest", required=True, help="Destination directory for organized documents")
    p_docs.add_argument("--all-formats", action="store_true", help="Extract all non-media formats, not just standard docs")
    p_docs.add_argument("--trust-file-dates", action="store_true", help="Trust filesystem timestamps as a fallback year")
    p_docs.add_argument("--move", action="store_true", help="Move mode: safely remove originals after copy verification")
    p_docs.add_argument("--dry-run", action="store_true", help="Simulate run without copying any files")
    p_docs.set_defaults(func=handle_docs)

    # Command: restore-docs
    p_restore_docs = subparsers.add_parser("restore-docs", help="Restore removed original documents back to their sources")
    p_restore_docs.add_argument("--dest", required=True, help="Destination directory containing catalog.db")
    p_restore_docs.set_defaults(func=handle_restore_docs)

    # Command: audit (privacy / nsfw scan)
    p_audit = subparsers.add_parser("audit", aliases=["privacy"], help="Audit photos for explicit content before lending a PC")
    p_audit.add_argument("sources", nargs="+", help="Folders to audit")
    p_audit.add_argument("--quarantine", action="store_true", help="Move flagged files into the secure Vault")
    p_audit.add_argument("--strict", action="store_true", help="Only flag high-severity nudity/genitalia")
    p_audit.add_argument("--suggestive", action="store_true", help="Include covered / suggestive photos")
    p_audit.add_argument("--model", choices=["320n", "640m"], default="320n", help="Model size: 320n (fast) or 640m (high precision)")
    p_audit.add_argument("--min-conf", type=float, default=0.50, help="Minimum confidence threshold (0.0 to 1.0, default 0.50)")
    p_audit.set_defaults(func=handle_audit)

    # Command: vault
    p_vault = subparsers.add_parser("vault", help="Inspect and manage quarantined files in the Vault")
    vault_sub = p_vault.add_subparsers(dest="vault_action", required=True)

    v_list = vault_sub.add_parser("list", help="List all quarantined items")
    v_restore = vault_sub.add_parser("restore", help="Restore an item back to its original path")
    v_restore.add_argument("id", help="Vault Item ID")
    v_purge = vault_sub.add_parser("purge", help="Permanently delete an item")
    v_purge.add_argument("id", help="Vault Item ID")
    p_vault.set_defaults(func=handle_vault)

    args = parser.parse_args()
    if not args.command:
        import os
        # If running in a graphical desktop session (SteamOS Desktop / KDE Plasma), launch GUI
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            from .gui.app import run_gui
            run_gui()
            return
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
