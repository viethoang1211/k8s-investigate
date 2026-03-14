"""Service scanner - finds Services with no endpoints."""

from __future__ import annotations

import logging

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner

logger = logging.getLogger(__name__)


@register_scanner
class ServiceScanner(BaseScanner):
    resource_type = "services"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        services = self.k8s.core_v1.list_namespaced_service(namespace).items

        # Build map of service name -> has endpoints
        # Use Endpoints API as fallback since EndpointSlice can have None endpoints
        svc_with_endpoints: set[str] = set()
        try:
            endpoint_slices = self.k8s.discovery_v1.list_namespaced_endpoint_slice(namespace).items
            for eps in endpoint_slices:
                labels = eps.metadata.labels or {}
                svc_name = labels.get("kubernetes.io/service-name", "")
                if svc_name and eps.endpoints:
                    svc_with_endpoints.add(svc_name)
        except Exception:
            # Fallback to legacy Endpoints API
            logger.debug("EndpointSlice API failed for %s, falling back to Endpoints", namespace)
            endpoints_list = self.k8s.core_v1.list_namespaced_endpoints(namespace).items
            for ep in endpoints_list:
                if ep.subsets:
                    for subset in ep.subsets:
                        if subset.addresses:
                            svc_with_endpoints.add(ep.metadata.name)
                            break

        for svc in services:
            if self.should_skip(svc.metadata):
                continue
            # Skip the kubernetes default service
            if svc.metadata.name == "kubernetes" and namespace == "default":
                continue
            if self.is_marked_unused(svc.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Service",
                    name=svc.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if svc.metadata.name not in svc_with_endpoints:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Service",
                    name=svc.metadata.name, reason="No endpoints found",
                ))
        return results
