"""K8s Investigate - Kubernetes Orphaned Resources Finder."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("k8s-investigate")
except PackageNotFoundError:
    __version__ = "unknown"
