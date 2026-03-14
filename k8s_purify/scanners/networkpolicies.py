"""NetworkPolicy scanner - finds NetworkPolicies not matching any pods."""

from __future__ import annotations

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner


def _labels_match(pod_labels: dict, match_labels: dict) -> bool:
    for k, v in match_labels.items():
        if pod_labels.get(k) != v:
            return False
    return True


@register_scanner
class NetworkPolicyScanner(BaseScanner):
    resource_type = "networkpolicies"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        policies = self.k8s.networking_v1.list_namespaced_network_policy(namespace).items
        pods = self.k8s.list_pods_cached(namespace)

        for policy in policies:
            if self.should_skip(policy.metadata):
                continue
            if self.is_marked_unused(policy.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="NetworkPolicy",
                    name=policy.metadata.name, reason="Marked as unused via label",
                ))
                continue

            selector = policy.spec.pod_selector
            match_labels = (selector.match_labels or {}) if selector else {}

            # Empty selector matches all pods - only unused if no pods
            if not match_labels:
                if not pods:
                    results.append(UnusedResource(
                        namespace=namespace, resource_type="NetworkPolicy",
                        name=policy.metadata.name,
                        reason="Empty selector with no pods in namespace",
                    ))
                continue

            # Non-empty selector must match at least one pod
            matched = any(
                _labels_match(pod.metadata.labels or {}, match_labels)
                for pod in pods
            )
            if not matched:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="NetworkPolicy",
                    name=policy.metadata.name,
                    reason="Pod selector does not match any pod",
                ))
        return results
