"""Tests for the scanner framework."""

from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from k8s_investigate.config import ScanOptions
from k8s_investigate.scanner import (
    BaseScanner, UnusedResource, register_scanner,
    get_scanner, get_all_scanners, _registry,
)


class TestBaseScanner:
    def _make_metadata(self, labels=None, creation_timestamp=None):
        m = MagicMock()
        m.labels = labels
        m.creation_timestamp = creation_timestamp
        return m

    def test_is_marked_unused(self):
        opts = ScanOptions()
        scanner = MagicMock(spec=BaseScanner)
        scanner.opts = opts
        meta = self._make_metadata(labels={"k8s-investigate/used": "false"})
        assert BaseScanner.is_marked_unused(scanner, meta) is True

    def test_is_not_marked_unused(self):
        opts = ScanOptions()
        scanner = MagicMock(spec=BaseScanner)
        scanner.opts = opts
        meta = self._make_metadata(labels={"app": "test"})
        assert BaseScanner.is_marked_unused(scanner, meta) is False

    def test_is_age_filtered_older_than(self):
        opts = ScanOptions(older_than=timedelta(hours=24))
        scanner = MagicMock(spec=BaseScanner)
        scanner.opts = opts
        # Resource created 1 hour ago -> should be filtered (too young)
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        meta = self._make_metadata(creation_timestamp=recent)
        assert BaseScanner.is_age_filtered(scanner, meta) is True

    def test_is_age_not_filtered(self):
        opts = ScanOptions(older_than=timedelta(hours=24))
        scanner = MagicMock(spec=BaseScanner)
        scanner.opts = opts
        # Resource created 48 hours ago -> passes filter
        old = datetime.now(timezone.utc) - timedelta(hours=48)
        meta = self._make_metadata(creation_timestamp=old)
        assert BaseScanner.is_age_filtered(scanner, meta) is False

    def test_label_exclude(self):
        opts = ScanOptions(exclude_labels=["env=test"])
        scanner = MagicMock(spec=BaseScanner)
        scanner.opts = opts
        meta = self._make_metadata(labels={"env": "test"})
        assert BaseScanner.is_label_excluded(scanner, meta) is True

    def test_label_include(self):
        opts = ScanOptions(include_labels="env=prod")
        scanner = MagicMock(spec=BaseScanner)
        scanner.opts = opts
        meta = self._make_metadata(labels={"env": "test"})
        assert BaseScanner.is_label_excluded(scanner, meta) is True


class TestRegistry:
    def test_registered_scanners(self):
        # Import to trigger registration
        import k8s_investigate.scanners  # noqa: F401
        scanners = get_all_scanners()
        assert "configmaps" in scanners
        assert "secrets" in scanners
        assert "services" in scanners
        assert "deployments" in scanners
        assert "pods" in scanners
        assert "pvs" in scanners
        assert "clusterroles" in scanners

    def test_get_scanner(self):
        import k8s_investigate.scanners  # noqa: F401
        cls = get_scanner("configmaps")
        assert cls is not None
        assert cls.resource_type == "configmaps"

    def test_get_unknown_scanner(self):
        assert get_scanner("nonexistent") is None


class TestPVCScanner:
    def _make_owner_ref(self, kind: str):
        ref = MagicMock()
        ref.kind = kind
        return ref

    def _make_pvc(self, name: str, owner_refs=None):
        pvc = MagicMock()
        pvc.metadata.name = name
        pvc.metadata.labels = {}
        pvc.metadata.annotations = {}
        pvc.metadata.owner_references = owner_refs or []
        return pvc

    def _make_pod_with_pvc(self, pvc_name: str):
        vol = MagicMock()
        vol.persistent_volume_claim = MagicMock()
        vol.persistent_volume_claim.claim_name = pvc_name
        vol.ephemeral = None
        pod = MagicMock()
        pod.spec.volumes = [vol]
        return pod

    def test_pvc_owned_by_statefulset_excluded(self):
        """PVCs owned by a StatefulSet must not be reported even when no pods run."""
        from k8s_investigate.scanners.pvcs import PVCScanner
        from k8s_investigate.config import ScanOptions

        sts_ref = self._make_owner_ref("StatefulSet")
        pvc = self._make_pvc("data-db-0", owner_refs=[sts_ref])

        k8s = MagicMock()
        k8s.list_pods_cached.return_value = []  # no running pods
        k8s.core_v1.list_namespaced_persistent_volume_claim.return_value.items = [pvc]

        scanner = PVCScanner(k8s=k8s, opts=ScanOptions())
        results = scanner.scan(namespace="default")

        assert results == [], (
            "PVC owned by a StatefulSet should not be reported as unused"
        )

    def test_pvc_not_owned_by_statefulset_reported(self):
        """Orphan PVCs (no owner, not mounted) must still be reported."""
        from k8s_investigate.scanners.pvcs import PVCScanner
        from k8s_investigate.config import ScanOptions

        pvc = self._make_pvc("orphan-pvc", owner_refs=[])

        k8s = MagicMock()
        k8s.list_pods_cached.return_value = []
        k8s.core_v1.list_namespaced_persistent_volume_claim.return_value.items = [pvc]

        scanner = PVCScanner(k8s=k8s, opts=ScanOptions())
        results = scanner.scan(namespace="default")

        assert len(results) == 1
        assert results[0].name == "orphan-pvc"

    def test_pvc_owned_by_other_kind_still_checked(self):
        """PVCs owned by a non-StatefulSet owner (e.g. Job) are still checked."""
        from k8s_investigate.scanners.pvcs import PVCScanner
        from k8s_investigate.config import ScanOptions

        job_ref = self._make_owner_ref("Job")
        pvc = self._make_pvc("job-pvc", owner_refs=[job_ref])

        k8s = MagicMock()
        k8s.list_pods_cached.return_value = []
        k8s.core_v1.list_namespaced_persistent_volume_claim.return_value.items = [pvc]

        scanner = PVCScanner(k8s=k8s, opts=ScanOptions())
        results = scanner.scan(namespace="default")

        assert len(results) == 1
        assert results[0].name == "job-pvc"

    def test_pvc_owned_by_statefulset_and_mounted(self):
        """PVC owned by a StatefulSet that is also mounted is safely excluded once."""
        from k8s_investigate.scanners.pvcs import PVCScanner
        from k8s_investigate.config import ScanOptions

        sts_ref = self._make_owner_ref("StatefulSet")
        pvc = self._make_pvc("data-db-0", owner_refs=[sts_ref])
        pod = self._make_pod_with_pvc("data-db-0")

        k8s = MagicMock()
        k8s.list_pods_cached.return_value = [pod]
        k8s.core_v1.list_namespaced_persistent_volume_claim.return_value.items = [pvc]

        scanner = PVCScanner(k8s=k8s, opts=ScanOptions())
        results = scanner.scan(namespace="default")

        assert results == []
