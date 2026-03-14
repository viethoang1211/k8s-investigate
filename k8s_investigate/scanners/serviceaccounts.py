"""ServiceAccount scanner - finds ServiceAccounts not used by any pod or binding."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class ServiceAccountScanner(BaseScanner):
    resource_type = "serviceaccounts"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        service_accounts = self.k8s.core_v1.list_namespaced_service_account(namespace).items
        pods = self.k8s.list_pods_cached(namespace)
        role_bindings = self.k8s.rbac_v1.list_namespaced_role_binding(namespace).items
        cluster_role_bindings = self.k8s.rbac_v1.list_cluster_role_binding().items

        # SAs used by pods
        used_sas: set[str] = set()
        for pod in pods:
            sa = pod.spec.service_account_name or "default"
            used_sas.add(sa)

        # SAs referenced in role bindings (namespace-scoped)
        for rb in role_bindings:
            for subject in rb.subjects or []:
                if subject.kind == "ServiceAccount" and (subject.namespace or namespace) == namespace:
                    used_sas.add(subject.name)

        # SAs referenced in cluster role bindings
        for crb in cluster_role_bindings:
            for subject in crb.subjects or []:
                if subject.kind == "ServiceAccount" and subject.namespace == namespace:
                    used_sas.add(subject.name)

        for sa in service_accounts:
            if self.should_skip(sa.metadata):
                continue
            # Skip the default service account
            if sa.metadata.name == "default":
                continue
            if self.is_marked_unused(sa.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="ServiceAccount",
                    name=sa.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if sa.metadata.name not in used_sas:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="ServiceAccount",
                    name=sa.metadata.name, reason="Not used by any pod or binding",
                ))
        return results
