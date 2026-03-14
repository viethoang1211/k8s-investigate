"""PriorityClass scanner - finds PriorityClasses not used by any pod."""

from __future__ import annotations

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class PriorityClassScanner(BaseScanner):
    resource_type = "priorityclasses"
    namespaced = False

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        pcs = self.k8s.scheduling_v1.list_priority_class().items
        all_pods = self.k8s.core_v1.list_pod_for_all_namespaces().items

        used_pcs: set[str] = set()
        for pod in all_pods:
            if pod.spec.priority_class_name:
                used_pcs.add(pod.spec.priority_class_name)

        for pc in pcs:
            if self.should_skip(pc.metadata):
                continue
            # Skip system priority classes and global defaults
            if pc.metadata.name.startswith("system-"):
                continue
            if pc.global_default:
                continue
            if self.is_marked_unused(pc.metadata):
                results.append(UnusedResource(
                    namespace="", resource_type="PriorityClass",
                    name=pc.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if pc.metadata.name not in used_pcs:
                results.append(UnusedResource(
                    namespace="", resource_type="PriorityClass",
                    name=pc.metadata.name, reason="Not used by any pod",
                ))
        return results
