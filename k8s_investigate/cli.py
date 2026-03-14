"""CLI interface using Click."""

from __future__ import annotations

import logging

import click
from rich.console import Console

from k8s_investigate import __version__
from k8s_investigate.config import ScanOptions, parse_duration
from k8s_investigate.delete import delete_resources
from k8s_investigate.formatters import format_results, print_summary
from k8s_investigate.k8s_client import K8sClient
from k8s_investigate.scanner import (
    UnusedResource,
    get_all_scanners,
    get_scanner,
)

# Resource type aliases for user convenience
_ALIASES: dict[str, str] = {
    "cm": "configmaps",
    "configmap": "configmaps",
    "secret": "secrets",
    "svc": "services",
    "service": "services",
    "deploy": "deployments",
    "deployment": "deployments",
    "sts": "statefulsets",
    "statefulset": "statefulsets",
    "ds": "daemonsets",
    "daemonset": "daemonsets",
    "rs": "replicasets",
    "replicaset": "replicasets",
    "pod": "pods",
    "ing": "ingresses",
    "ingress": "ingresses",
    "pvc": "pvcs",
    "pv": "pvs",
    "role": "roles",
    "clusterrole": "clusterroles",
    "rb": "rolebindings",
    "rolebinding": "rolebindings",
    "crb": "clusterrolebindings",
    "clusterrolebinding": "clusterrolebindings",
    "sa": "serviceaccounts",
    "serviceaccount": "serviceaccounts",
    "hpa": "hpas",
    "job": "jobs",
    "pdb": "pdbs",
    "netpol": "networkpolicies",
    "networkpolicy": "networkpolicies",
    "sc": "storageclasses",
    "storageclass": "storageclasses",
    "pc": "priorityclasses",
    "priorityclass": "priorityclasses",
}

console = Console()


def _resolve_resource_type(name: str) -> str:
    """Resolve resource type alias to canonical name."""
    return _ALIASES.get(name.lower(), name.lower())


def _build_opts(ctx: click.Context) -> ScanOptions:
    """Build ScanOptions from click context."""
    params = ctx.ensure_object(dict)
    opts = ScanOptions(
        kubeconfig=params.get("kubeconfig"),
        context=params.get("context"),
        output_format=params.get("output", "table"),
        show_reason=params.get("show_reason", False),
        delete=params.get("delete", False),
        yes=params.get("yes", False),
        verbose=params.get("verbose", False),
        group_by=params.get("group_by", "namespace"),
    )
    # Namespaces
    ns = params.get("namespace")
    if ns:
        opts.namespaces = [n.strip() for n in ns.split(",")]
    excl_ns = params.get("exclude_namespace")
    if excl_ns:
        opts.exclude_namespaces = [n.strip() for n in excl_ns.split(",")]
    # Labels
    excl_labels = params.get("exclude_labels")
    if excl_labels:
        opts.exclude_labels = [lbl.strip() for lbl in excl_labels.split(",")]
    incl_labels = params.get("include_labels")
    if incl_labels:
        opts.include_labels = incl_labels
    # Age
    older = params.get("older_than")
    if older:
        opts.older_than = parse_duration(older)
    newer = params.get("newer_than")
    if newer:
        opts.newer_than = parse_duration(newer)
    return opts


def _run_scan(opts: ScanOptions, resource_types: list[str]) -> list[UnusedResource]:
    """Execute scanners for the specified resource types."""
    # Import to trigger registration
    import k8s_investigate.scanners  # noqa: F401

    k8s = K8sClient(opts)
    all_results: list[UnusedResource] = []

    # Separate cluster-scoped and namespaced scanners
    cluster_types = []
    ns_types = []
    for rt in resource_types:
        scanner_cls = get_scanner(rt)
        if scanner_cls is None:
            console.print(f"[red]Unknown resource type: {rt}[/red]")
            continue
        if scanner_cls.namespaced:
            ns_types.append(rt)
        else:
            cluster_types.append(rt)

    # Run cluster-scoped scanners once
    for rt in cluster_types:
        scanner_cls = get_scanner(rt)
        if scanner_cls:
            try:
                scanner = scanner_cls(k8s, opts)
                all_results.extend(scanner.scan())
            except Exception as e:
                console.print(f"[red]Error scanning {rt}: {e}[/red]")

    # Run namespaced scanners per namespace
    if ns_types:
        namespaces = k8s.get_namespaces(opts)
        for ns in namespaces:
            for rt in ns_types:
                scanner_cls = get_scanner(rt)
                if scanner_cls:
                    try:
                        scanner = scanner_cls(k8s, opts)
                        all_results.extend(scanner.scan(ns))
                    except Exception as e:
                        console.print(f"[red]Error scanning {rt} in {ns}: {e}[/red]")
            k8s.clear_cache()

    return all_results


@click.group()
@click.version_option(version=__version__, prog_name="k8s-investigate")
@click.option("--kubeconfig", "-k", envvar="KUBECONFIG", help="Path to kubeconfig file.")
@click.option("--context", help="Kubernetes context to use.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def main(ctx: click.Context, kubeconfig: str, context: str, verbose: bool) -> None:
    """K8s Investigate - Find and clean up unused Kubernetes resources.

    \b
    Examples:
      k8s-investigate scan all
      k8s-investigate scan cm,secrets -n default --show-reason
      k8s-investigate scan all -o json --exclude-namespace kube-system
      k8s-investigate exporter --port 8080 --interval 300
    """
    ctx.ensure_object(dict)
    ctx.obj["kubeconfig"] = kubeconfig
    ctx.obj["context"] = context
    ctx.obj["verbose"] = verbose
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@main.command()
@click.argument("resources", default="all")
@click.option("-n", "--namespace", help="Namespace(s) to scan, comma-separated.")
@click.option("--exclude-namespace", help="Namespace(s) to exclude, comma-separated.")
@click.option("-o", "--output", type=click.Choice(["table", "json", "yaml"]), default="table",
              help="Output format.")
@click.option("-l", "--exclude-labels", help="Label selectors to exclude, comma-separated (key=value).")
@click.option("--include-labels", help="Label selector to include (key=value).")
@click.option("--older-than", help="Only show resources older than duration (e.g. 24h, 7d).")
@click.option("--newer-than", help="Only show resources newer than duration.")
@click.option("--show-reason", is_flag=True, help="Show reason why resource is unused.")
@click.option("--group-by", type=click.Choice(["namespace", "resource"]), default="namespace",
              help="Group output by namespace or resource type.")
@click.option("--delete", is_flag=True, help="Delete unused resources.")
@click.option("--yes", "-y", is_flag=True, help="Skip deletion confirmation.")
@click.pass_context
def scan(ctx: click.Context, resources: str, **kwargs) -> None:
    """Scan for unused Kubernetes resources.

    RESOURCES can be 'all' or a comma-separated list of resource types.

    \b
    Examples:
      k8s-investigate scan all                          # Scan everything
      k8s-investigate scan configmaps                   # Scan only ConfigMaps
      k8s-investigate scan cm,secrets,svc               # Multiple types (short names)
      k8s-investigate scan all -n default               # Only default namespace
      k8s-investigate scan all -n dev,staging            # Multiple namespaces
      k8s-investigate scan all --exclude-namespace kube-system,kube-public
      k8s-investigate scan all --older-than 7d           # Only resources older than 7 days
      k8s-investigate scan all --show-reason             # Show why each resource is unused
      k8s-investigate scan all -o json                   # JSON output
      k8s-investigate scan all -o yaml > report.yaml     # Save YAML report
      k8s-investigate scan all --group-by resource       # Group by resource type
      k8s-investigate scan all --delete                  # Delete with confirmation
      k8s-investigate scan all --delete --yes            # Delete without confirmation

    \b
    Resource type short names:
      cm=ConfigMaps  svc=Services  deploy=Deployments  sts=StatefulSets
      ds=DaemonSets  rs=ReplicaSets  ing=Ingresses  sa=ServiceAccounts
      rb=RoleBindings  crb=ClusterRoleBindings  sc=StorageClasses
      pc=PriorityClasses  netpol=NetworkPolicies  pdb=PDBs
    """
    # Merge params into context
    ctx.obj.update(kwargs)
    opts = _build_opts(ctx)

    # Resolve resource types
    if resources.lower() == "all":
        import k8s_investigate.scanners  # noqa: F401
        resource_types = list(get_all_scanners().keys())
    else:
        resource_types = [_resolve_resource_type(r.strip()) for r in resources.split(",")]

    console.print(f"[bold]Scanning for unused resources: {', '.join(resource_types)}[/bold]\n")

    results = _run_scan(opts, resource_types)

    # Output
    output = format_results(results, opts.output_format, opts.show_reason, opts.group_by)
    click.echo(output)

    print_summary(results)

    # Delete if requested
    if opts.delete and results:
        k8s = K8sClient(opts)
        delete_resources(k8s, results, auto_confirm=opts.yes)


@main.command()
@click.option("--port", default=8080, help="Port for Prometheus metrics server.")
@click.option("--interval", default=600, help="Collection interval in seconds.")
@click.option("-n", "--namespace", help="Namespace(s) to scan, comma-separated.")
@click.option("--exclude-namespace", help="Namespace(s) to exclude, comma-separated.")
@click.pass_context
def exporter(ctx: click.Context, port: int, interval: int, **kwargs) -> None:
    """Run as Prometheus metrics exporter.

    \b
    Examples:
      k8s-investigate exporter                           # Default: port 8080, 10min interval
      k8s-investigate exporter --port 9090 --interval 300
      k8s-investigate exporter --exclude-namespace kube-system
    """
    ctx.obj.update(kwargs)
    opts = _build_opts(ctx)
    console.print(f"[bold]Starting Prometheus exporter on port {port}...[/bold]")
    from k8s_investigate.exporter import run_exporter
    run_exporter(opts, port=port, interval=interval)


if __name__ == "__main__":
    main()
