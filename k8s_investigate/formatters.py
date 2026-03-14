"""Output formatters for scan results."""

from __future__ import annotations

import io
import json
from collections import defaultdict

import yaml
from rich.console import Console
from rich.table import Table

from k8s_investigate.scanner import UnusedResource


def format_results(
    results: list[UnusedResource],
    output_format: str = "table",
    show_reason: bool = False,
    group_by: str = "namespace",
) -> str:
    """Format scan results based on output format."""
    if output_format == "json":
        return _format_json(results, show_reason)
    elif output_format == "yaml":
        return _format_yaml(results, show_reason)
    else:
        return _format_table(results, show_reason, group_by)


def _results_to_dict(results: list[UnusedResource], show_reason: bool) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        key = r.namespace or "(cluster-scoped)"
        entry: dict = {"resource_type": r.resource_type, "name": r.name}
        if show_reason:
            entry["reason"] = r.reason
        grouped[key].append(entry)
    return dict(grouped)


def _format_json(results: list[UnusedResource], show_reason: bool) -> str:
    data = _results_to_dict(results, show_reason)
    return json.dumps(data, indent=2)


def _format_yaml(results: list[UnusedResource], show_reason: bool) -> str:
    data = _results_to_dict(results, show_reason)
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def _format_table(results: list[UnusedResource], show_reason: bool, group_by: str) -> str:
    if not results:
        return "No unused resources found."

    console = Console(record=True, width=160, file=io.StringIO())

    if group_by == "resource":
        grouped: dict[str, list[UnusedResource]] = defaultdict(list)
        for r in results:
            grouped[r.resource_type].append(r)
        for rtype in sorted(grouped.keys()):
            table = Table(title=f"Unused {rtype}", show_lines=False, pad_edge=True)
            table.add_column("#", justify="right", style="dim", width=4)
            table.add_column("Namespace", style="cyan", min_width=15)
            table.add_column("Name", style="green", min_width=30)
            if show_reason:
                table.add_column("Reason", style="yellow", min_width=40)
            for idx, r in enumerate(grouped[rtype], 1):
                ns = r.namespace or "(cluster)"
                row = [str(idx), ns, r.name]
                if show_reason:
                    row.append(r.reason)
                table.add_row(*row)
            console.print(table)
            console.print()
    else:
        grouped_ns: dict[str, list[UnusedResource]] = defaultdict(list)
        for r in results:
            key = r.namespace or "(cluster-scoped)"
            grouped_ns[key].append(r)
        for ns in sorted(grouped_ns.keys()):
            table = Table(title=f"Unused resources in namespace: {ns}", show_lines=False, pad_edge=True)
            table.add_column("#", justify="right", style="dim", width=4)
            table.add_column("Resource Type", style="cyan", min_width=18)
            table.add_column("Name", style="green", min_width=30)
            if show_reason:
                table.add_column("Reason", style="yellow", min_width=40)
            for idx, r in enumerate(grouped_ns[ns], 1):
                row = [str(idx), r.resource_type, r.name]
                if show_reason:
                    row.append(r.reason)
                table.add_row(*row)
            console.print(table)
            console.print()

    return console.export_text()


def print_summary(results: list[UnusedResource]) -> None:
    """Print a summary of findings."""
    console = Console()
    if not results:
        console.print("[green]No unused resources found.[/green]")
        return

    # Count by type
    by_type: dict[str, int] = defaultdict(int)
    for r in results:
        by_type[r.resource_type] += 1

    console.print(f"\n[bold]Summary: {len(results)} unused resources found[/bold]")
    table = Table(show_header=True)
    table.add_column("Resource Type", style="cyan")
    table.add_column("Count", justify="right", style="bold")
    for rtype in sorted(by_type.keys()):
        table.add_row(rtype, str(by_type[rtype]))
    console.print(table)
