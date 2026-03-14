"""Pod scanner - finds Evicted and CrashLoopBackOff pods."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class PodScanner(BaseScanner):
    resource_type = "pods"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        pods = self.k8s.list_pods_cached(namespace)

        for pod in pods:
            if self.should_skip(pod.metadata):
                continue
            if self.is_marked_unused(pod.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Pod",
                    name=pod.metadata.name, reason="Marked as unused via label",
                ))
                continue
            status = pod.status
            if not status:
                continue
            # Evicted pods
            if status.phase == "Failed" and status.reason == "Evicted":
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Pod",
                    name=pod.metadata.name, reason="Pod was evicted",
                ))
                continue
            # CrashLoopBackOff - check container statuses
            if status.container_statuses:
                for cs in status.container_statuses:
                    if cs.state and cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                        results.append(UnusedResource(
                            namespace=namespace, resource_type="Pod",
                            name=pod.metadata.name,
                            reason=f"Container {cs.name} in CrashLoopBackOff",
                        ))
                        break
        return results
