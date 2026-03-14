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
