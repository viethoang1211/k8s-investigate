"""PV scanner - finds PersistentVolumes not bound to any PVC."""

from __future__ import annotations

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class PVScanner(BaseScanner):
    resource_type = "pvs"
    namespaced = False

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        pvs = self.k8s.core_v1.list_persistent_volume().items

        for pv in pvs:
            if self.should_skip(pv.metadata):
                continue
            if self.is_marked_unused(pv.metadata):
                results.append(UnusedResource(
                    namespace="", resource_type="PV",
                    name=pv.metadata.name, reason="Marked as unused via label",
                ))
                continue
            phase = pv.status.phase if pv.status else ""
            if phase != "Bound":
                results.append(UnusedResource(
                    namespace="", resource_type="PV",
                    name=pv.metadata.name, reason=f"Not bound (phase: {phase})",
                ))
        return results
