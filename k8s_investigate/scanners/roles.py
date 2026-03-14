"""Role scanner - finds Roles not referenced by any RoleBinding."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class RoleScanner(BaseScanner):
    resource_type = "roles"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        roles = self.k8s.rbac_v1.list_namespaced_role(namespace).items
        bindings = self.k8s.rbac_v1.list_namespaced_role_binding(namespace).items

        # Roles referenced by bindings
        bound_roles: set[str] = set()
        for rb in bindings:
            if rb.role_ref.kind == "Role":
                bound_roles.add(rb.role_ref.name)

        for role in roles:
            if self.should_skip(role.metadata):
                continue
            if self.is_marked_unused(role.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Role",
                    name=role.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if role.metadata.name not in bound_roles:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Role",
                    name=role.metadata.name, reason="Not referenced by any RoleBinding",
                ))
        return results
