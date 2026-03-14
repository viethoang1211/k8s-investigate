"""ClusterRoleBinding scanner - finds bindings with non-existent roles/subjects."""

from __future__ import annotations

from kubernetes.client.exceptions import ApiException

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner

_SYSTEM_PREFIXES = ("system:", "kubeadm:", "cluster-admin")


@register_scanner
class ClusterRoleBindingScanner(BaseScanner):
    resource_type = "clusterrolebindings"
    namespaced = False

    def _cluster_role_exists(self, name: str) -> bool:
        try:
            self.k8s.rbac_v1.read_cluster_role(name)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def _sa_exists(self, namespace: str, name: str) -> bool:
        try:
            self.k8s.core_v1.read_namespaced_service_account(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        bindings = self.k8s.rbac_v1.list_cluster_role_binding().items

        for crb in bindings:
            if self.should_skip(crb.metadata):
                continue
            if any(crb.metadata.name.startswith(p) for p in _SYSTEM_PREFIXES):
                continue
            if self.is_marked_unused(crb.metadata):
                results.append(UnusedResource(
                    namespace="", resource_type="ClusterRoleBinding",
                    name=crb.metadata.name, reason="Marked as unused via label",
                ))
                continue

            # Check if referenced ClusterRole exists
            if not self._cluster_role_exists(crb.role_ref.name):
                results.append(UnusedResource(
                    namespace="", resource_type="ClusterRoleBinding",
                    name=crb.metadata.name,
                    reason=f"References non-existent ClusterRole: {crb.role_ref.name}",
                ))
                continue

            # Check if all SA subjects exist
            sa_subjects = [s for s in (crb.subjects or []) if s.kind == "ServiceAccount"]
            if sa_subjects and all(
                not self._sa_exists(s.namespace or "default", s.name) for s in sa_subjects
            ):
                results.append(UnusedResource(
                    namespace="", resource_type="ClusterRoleBinding",
                    name=crb.metadata.name,
                    reason="All ServiceAccount subjects do not exist",
                ))
        return results
