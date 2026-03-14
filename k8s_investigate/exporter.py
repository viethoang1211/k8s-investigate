"""Prometheus metrics exporter for orphaned resources."""

from __future__ import annotations

import logging
import threading
import time

from prometheus_client import Gauge, start_http_server

from k8s_investigate.config import ScanOptions
from k8s_investigate.k8s_client import K8sClient
from k8s_investigate.scanner import UnusedResource, get_all_scanners, get_cluster_scanners, get_namespaced_scanners

logger = logging.getLogger(__name__)

orphaned_gauge = Gauge(
    "k8s_investigate_orphaned_resources",
    "Orphaned Kubernetes resources",
    ["kind", "namespace", "resource_name"],
)


def _collect_metrics(k8s: K8sClient, opts: ScanOptions) -> list[UnusedResource]:
    """Run all scanners and collect results."""
    all_results: list[UnusedResource] = []

    # Cluster-scoped scanners
    for name, scanner_cls in get_cluster_scanners().items():
        try:
            scanner = scanner_cls(k8s, opts)
            all_results.extend(scanner.scan())
        except Exception:
            logger.exception("Error scanning %s", name)

    # Namespaced scanners
    namespaces = k8s.get_namespaces(opts)
    for ns in namespaces:
        for name, scanner_cls in get_namespaced_scanners().items():
            try:
                scanner = scanner_cls(k8s, opts)
                all_results.extend(scanner.scan(ns))
            except Exception:
                logger.exception("Error scanning %s in %s", name, ns)
        k8s.clear_cache()

    return all_results


def _update_metrics(results: list[UnusedResource]) -> None:
    """Update Prometheus metrics with scan results."""
    # Clear all existing metrics
    orphaned_gauge._metrics.clear()

    for r in results:
        orphaned_gauge.labels(
            kind=r.resource_type,
            namespace=r.namespace or "",
            resource_name=r.name,
        ).set(1)


def run_exporter(opts: ScanOptions, port: int = 8080, interval: int = 600) -> None:
    """Start Prometheus metrics server and run periodic collection."""
    # Import scanners to trigger registration
    import k8s_investigate.scanners  # noqa: F401

    k8s = K8sClient(opts)
    start_http_server(port)
    logger.info("Prometheus metrics server started on port %d", port)
    logger.info("Collection interval: %ds", interval)

    while True:
        try:
            logger.info("Starting resource scan...")
            results = _collect_metrics(k8s, opts)
            _update_metrics(results)
            logger.info("Scan complete. Found %d orphaned resources.", len(results))
        except Exception:
            logger.exception("Error during metrics collection")
        time.sleep(interval)
