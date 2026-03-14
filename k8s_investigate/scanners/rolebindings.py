"""RoleBinding scanner - finds RoleBindings referencing non-existent roles/subjects."""

from __future__ import annotations

from kubernetes.client.exceptions import ApiException

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class RoleBindingScanner(BaseScanner):
    resource_type = "rolebindings"
    namespaced = True

    def _role_exists(self, namespace: str, name: str) -> bool:
        try:
            self.k8s.rbac_v1.read_namespaced_role(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

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
        bindings = self.k8s.rbac_v1.list_namespaced_role_binding(namespace).items

        for rb in bindings:
            if self.should_skip(rb.metadata):
                continue
            if self.is_marked_unused(rb.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="RoleBinding",
                    name=rb.metadata.name, reason="Marked as unused via label",
                ))
                continue

            # Check if referenced role exists
            role_ref = rb.role_ref
            if role_ref.kind == "Role" and not self._role_exists(namespace, role_ref.name):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="RoleBinding",
                    name=rb.metadata.name,
                    reason=f"References non-existent Role: {role_ref.name}",
                ))
                continue
            if role_ref.kind == "ClusterRole" and not self._cluster_role_exists(role_ref.name):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="RoleBinding",
                    name=rb.metadata.name,
                    reason=f"References non-existent ClusterRole: {role_ref.name}",
                ))
                continue

            # Check if all ServiceAccount subjects exist
            sa_subjects = [s for s in (rb.subjects or []) if s.kind == "ServiceAccount"]
            if sa_subjects and all(
                not self._sa_exists(s.namespace or namespace, s.name) for s in sa_subjects
            ):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="RoleBinding",
                    name=rb.metadata.name,
                    reason="All ServiceAccount subjects do not exist",
                ))
        return results
