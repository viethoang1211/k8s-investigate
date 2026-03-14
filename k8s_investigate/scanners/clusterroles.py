"""ClusterRole scanner - finds ClusterRoles not referenced by any binding."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner

# System ClusterRoles to always skip
_SYSTEM_PREFIXES = ("system:", "kubeadm:", "cluster-admin")


@register_scanner
class ClusterRoleScanner(BaseScanner):
    resource_type = "clusterroles"
    namespaced = False

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        cluster_roles = self.k8s.rbac_v1.list_cluster_role().items
        cluster_bindings = self.k8s.rbac_v1.list_cluster_role_binding().items
        # Also check RoleBindings across all namespaces that reference ClusterRoles
        all_role_bindings = self.k8s.rbac_v1.list_role_binding_for_all_namespaces().items

        bound_roles: set[str] = set()
        for crb in cluster_bindings:
            if crb.role_ref.kind == "ClusterRole":
                bound_roles.add(crb.role_ref.name)
        for rb in all_role_bindings:
            if rb.role_ref.kind == "ClusterRole":
                bound_roles.add(rb.role_ref.name)

        # ClusterRoles used in aggregation
        aggregation_labels: set[str] = set()
        for cr in cluster_roles:
            if cr.aggregation_rule and cr.aggregation_rule.cluster_role_selectors:
                for selector in cr.aggregation_rule.cluster_role_selectors:
                    for k, v in (selector.match_labels or {}).items():
                        aggregation_labels.add(f"{k}={v}")

        for cr in cluster_roles:
            if self.should_skip(cr.metadata):
                continue
            # Skip system ClusterRoles
            if any(cr.metadata.name.startswith(p) for p in _SYSTEM_PREFIXES):
                continue
            if self.is_marked_unused(cr.metadata):
                results.append(UnusedResource(
                    namespace="", resource_type="ClusterRole",
                    name=cr.metadata.name, reason="Marked as unused via label",
                ))
                continue
            # Check if used by aggregation
            cr_labels = cr.metadata.labels or {}
            is_aggregated = any(
                f"{k}={v}" in aggregation_labels
                for k, v in cr_labels.items()
            )
            if cr.metadata.name not in bound_roles and not is_aggregated:
                results.append(UnusedResource(
                    namespace="", resource_type="ClusterRole",
                    name=cr.metadata.name,
                    reason="Not referenced by any binding or aggregation rule",
                ))
        return results
