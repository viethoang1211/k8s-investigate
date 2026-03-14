"""DaemonSet scanner - finds DaemonSets not scheduled on any node."""

from __future__ import annotations

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class DaemonSetScanner(BaseScanner):
    resource_type = "daemonsets"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        daemonsets = self.k8s.apps_v1.list_namespaced_daemon_set(namespace).items

        for ds in daemonsets:
            if self.should_skip(ds.metadata):
                continue
            if self.is_marked_unused(ds.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="DaemonSet",
                    name=ds.metadata.name, reason="Marked as unused via label",
                ))
                continue
            scheduled = ds.status.current_number_scheduled or 0
            if scheduled == 0:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="DaemonSet",
                    name=ds.metadata.name, reason="Not scheduled on any node",
                ))
        return results
