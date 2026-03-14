"""ReplicaSet scanner - finds ReplicaSets with zero replicas and no active pods."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class ReplicaSetScanner(BaseScanner):
    resource_type = "replicasets"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        replicasets = self.k8s.apps_v1.list_namespaced_replica_set(namespace).items

        for rs in replicasets:
            if self.should_skip(rs.metadata):
                continue
            if self.is_marked_unused(rs.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="ReplicaSet",
                    name=rs.metadata.name, reason="Marked as unused via label",
                ))
                continue
            replicas = rs.spec.replicas if rs.spec.replicas is not None else 1
            available = rs.status.available_replicas or 0
            ready = rs.status.ready_replicas or 0
            fully_labeled = rs.status.fully_labeled_replicas or 0
            if replicas == 0 and available == 0 and ready == 0 and fully_labeled == 0:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="ReplicaSet",
                    name=rs.metadata.name,
                    reason="Zero replicas with no available/ready pods",
                ))
        return results
