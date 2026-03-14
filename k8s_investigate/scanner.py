"""Base scanner framework and registry."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from k8s_investigate.config import ScanOptions
from k8s_investigate.k8s_client import K8sClient

logger = logging.getLogger(__name__)


@dataclass
class UnusedResource:
    """Represents a single unused resource."""

    namespace: str
    resource_type: str
    name: str
    reason: str


class BaseScanner(ABC):
    """Base class for all resource scanners."""

    # Subclasses must set these
    resource_type: str = ""
    namespaced: bool = True

    def __init__(self, k8s: K8sClient, opts: ScanOptions) -> None:
        self.k8s = k8s
        self.opts = opts

    @abstractmethod
    def scan(self, namespace: str = "") -> list[UnusedResource]:
        """Scan for unused resources in the given namespace."""
        ...

    def is_label_excluded(self, metadata) -> bool:
        """Check if resource should be excluded based on label filters."""
        labels = metadata.labels or {}
        if self.opts.include_labels:
            key, _, val = self.opts.include_labels.partition("=")
            if labels.get(key) != val:
                return True
        for sel in self.opts.exclude_labels:
            key, _, val = sel.partition("=")
            if labels.get(key) == val:
                return True
        return False

    def is_marked_unused(self, metadata) -> bool:
        """Check if resource is explicitly marked as unused via label."""
        labels = metadata.labels or {}
        return labels.get(self.opts.PURIFY_LABEL) == "false"

    def is_age_filtered(self, metadata) -> bool:
        """Check if resource should be filtered based on age."""
        creation = metadata.creation_timestamp
        if not creation:
            return False
        if creation.tzinfo is None:
            creation = creation.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - creation
        if self.opts.older_than and age < self.opts.older_than:
            return True
        if self.opts.newer_than and age > self.opts.newer_than:
            return True
        return False

    def should_skip(self, metadata) -> bool:
        """Check all common filters. Returns True if resource should be skipped."""
        return self.is_label_excluded(metadata) or self.is_age_filtered(metadata)


# Scanner registry
_registry: dict[str, type[BaseScanner]] = {}


def register_scanner(cls: type[BaseScanner]) -> type[BaseScanner]:
    """Decorator to register a scanner class."""
    _registry[cls.resource_type] = cls
    return cls


def get_scanner(resource_type: str) -> type[BaseScanner] | None:
    """Get a scanner class by resource type name."""
    return _registry.get(resource_type)


def get_all_scanners() -> dict[str, type[BaseScanner]]:
    """Get all registered scanners."""
    return dict(_registry)


def get_namespaced_scanners() -> dict[str, type[BaseScanner]]:
    """Get all namespaced scanners."""
    return {k: v for k, v in _registry.items() if v.namespaced}


def get_cluster_scanners() -> dict[str, type[BaseScanner]]:
    """Get all cluster-scoped scanners."""
    return {k: v for k, v in _registry.items() if not v.namespaced}
