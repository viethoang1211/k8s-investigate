"""Deployment scanner - finds Deployments with zero replicas."""

from __future__ import annotations

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class DeploymentScanner(BaseScanner):
    resource_type = "deployments"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        deployments = self.k8s.apps_v1.list_namespaced_deployment(namespace).items

        for deploy in deployments:
            if self.should_skip(deploy.metadata):
                continue
            if self.is_marked_unused(deploy.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Deployment",
                    name=deploy.metadata.name, reason="Marked as unused via label",
                ))
                continue
            replicas = deploy.spec.replicas if deploy.spec.replicas is not None else 1
            if replicas == 0:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Deployment",
                    name=deploy.metadata.name, reason="Zero replicas configured",
                ))
        return results
