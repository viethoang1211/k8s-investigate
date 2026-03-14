"""StorageClass scanner - finds StorageClasses not used by any PV or PVC."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class StorageClassScanner(BaseScanner):
    resource_type = "storageclasses"
    namespaced = False

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        storage_classes = self.k8s.storage_v1.list_storage_class().items
        pvs = self.k8s.core_v1.list_persistent_volume().items
        pvcs = self.k8s.core_v1.list_persistent_volume_claim_for_all_namespaces().items

        used_scs: set[str] = set()
        for pv in pvs:
            if pv.spec.storage_class_name:
                used_scs.add(pv.spec.storage_class_name)
        for pvc in pvcs:
            if pvc.spec.storage_class_name:
                used_scs.add(pvc.spec.storage_class_name)

        for sc in storage_classes:
            if self.should_skip(sc.metadata):
                continue
            if self.is_marked_unused(sc.metadata):
                results.append(UnusedResource(
                    namespace="", resource_type="StorageClass",
                    name=sc.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if sc.metadata.name not in used_scs:
                results.append(UnusedResource(
                    namespace="", resource_type="StorageClass",
                    name=sc.metadata.name, reason="Not used by any PV or PVC",
                ))
        return results
