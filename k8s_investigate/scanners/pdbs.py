"""PDB scanner - finds PodDisruptionBudgets not matching any workload."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


def _labels_match_selector(labels: dict, selector: dict) -> bool:
    """Check if labels satisfy a matchLabels selector."""
    if not selector:
        return True
    for k, v in selector.items():
        if labels.get(k) != v:
            return False
    return True


@register_scanner
class PDBScanner(BaseScanner):
    resource_type = "pdbs"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        pdbs = self.k8s.policy_v1.list_namespaced_pod_disruption_budget(namespace).items
        deployments = self.k8s.apps_v1.list_namespaced_deployment(namespace).items
        statefulsets = self.k8s.apps_v1.list_namespaced_stateful_set(namespace).items
        pods = self.k8s.list_pods_cached(namespace)

        for pdb in pdbs:
            if self.should_skip(pdb.metadata):
                continue
            if self.is_marked_unused(pdb.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="PDB",
                    name=pdb.metadata.name, reason="Marked as unused via label",
                ))
                continue

            selector = pdb.spec.selector
            if not selector or not selector.match_labels:
                # Empty selector - check if any pods exist in namespace
                if not pods:
                    results.append(UnusedResource(
                        namespace=namespace, resource_type="PDB",
                        name=pdb.metadata.name,
                        reason="Empty selector with no pods in namespace",
                    ))
                continue

            match_labels = selector.match_labels
            matched = False

            # Check against deployment pod templates
            for deploy in deployments:
                tmpl_labels = deploy.spec.template.metadata.labels or {}
                if _labels_match_selector(tmpl_labels, match_labels):
                    matched = True
                    break

            # Check against statefulset pod templates
            if not matched:
                for sts in statefulsets:
                    tmpl_labels = sts.spec.template.metadata.labels or {}
                    if _labels_match_selector(tmpl_labels, match_labels):
                        matched = True
                        break

            # Check against running pods
            if not matched:
                for pod in pods:
                    pod_labels = pod.metadata.labels or {}
                    if _labels_match_selector(pod_labels, match_labels):
                        matched = True
                        break

            if not matched:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="PDB",
                    name=pdb.metadata.name,
                    reason="Selector does not match any deployment, statefulset, or pod",
                ))
        return results
