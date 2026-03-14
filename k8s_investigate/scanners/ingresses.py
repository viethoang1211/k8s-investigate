"""Ingress scanner - finds Ingresses with non-existent backend services."""

from __future__ import annotations

import logging

from kubernetes.client.exceptions import ApiException

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner

logger = logging.getLogger(__name__)


@register_scanner
class IngressScanner(BaseScanner):
    resource_type = "ingresses"
    namespaced = True

    def _service_exists(self, namespace: str, name: str) -> bool:
        try:
            self.k8s.core_v1.read_namespaced_service(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        ingresses = self.k8s.networking_v1.list_namespaced_ingress(namespace).items

        for ing in ingresses:
            if self.should_skip(ing.metadata):
                continue
            if self.is_marked_unused(ing.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Ingress",
                    name=ing.metadata.name, reason="Marked as unused via label",
                ))
                continue

            has_valid_backend = False

            # Check default backend
            if ing.spec.default_backend and ing.spec.default_backend.service:
                svc_name = ing.spec.default_backend.service.name
                if self._service_exists(namespace, svc_name):
                    has_valid_backend = True

            # Check rules
            for rule in ing.spec.rules or []:
                if not rule.http:
                    continue
                for path in rule.http.paths or []:
                    if path.backend and path.backend.service:
                        svc_name = path.backend.service.name
                        if self._service_exists(namespace, svc_name):
                            has_valid_backend = True
                            break
                if has_valid_backend:
                    break

            if not has_valid_backend:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Ingress",
                    name=ing.metadata.name, reason="No valid backend service found",
                ))
        return results
