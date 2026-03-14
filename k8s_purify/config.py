"""Configuration and shared options."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta


def parse_duration(s: str) -> timedelta:
    """Parse a human-friendly duration string like '24h', '30m', '7d', '1h30m'."""
    if not s:
        raise ValueError("empty duration string")
    pattern = re.compile(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")
    m = pattern.fullmatch(s.strip())
    if not m or not any(m.groups()):
        raise ValueError(f"invalid duration format: {s!r} (use e.g. '24h', '7d', '1h30m')")
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    seconds = int(m.group(4) or 0)
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


@dataclass
class ScanOptions:
    """Options controlling scan behavior."""

    kubeconfig: str | None = None
    context: str | None = None
    namespaces: list[str] = field(default_factory=list)
    exclude_namespaces: list[str] = field(default_factory=list)
    exclude_labels: list[str] = field(default_factory=list)
    include_labels: str | None = None
    older_than: timedelta | None = None
    newer_than: timedelta | None = None
    output_format: str = "table"
    show_reason: bool = False
    delete: bool = False
    yes: bool = False
    verbose: bool = False
    group_by: str = "namespace"

    # Label used to explicitly mark a resource as unused
    PURIFY_LABEL: str = "k8s-purify/used"
