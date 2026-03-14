"""Resource scanners package."""

from k8s_purify.scanners.configmaps import ConfigMapScanner
from k8s_purify.scanners.secrets import SecretScanner
from k8s_purify.scanners.services import ServiceScanner
from k8s_purify.scanners.deployments import DeploymentScanner
from k8s_purify.scanners.statefulsets import StatefulSetScanner
from k8s_purify.scanners.daemonsets import DaemonSetScanner
from k8s_purify.scanners.replicasets import ReplicaSetScanner
from k8s_purify.scanners.pods import PodScanner
from k8s_purify.scanners.ingresses import IngressScanner
from k8s_purify.scanners.pvcs import PVCScanner
from k8s_purify.scanners.pvs import PVScanner
from k8s_purify.scanners.roles import RoleScanner
from k8s_purify.scanners.clusterroles import ClusterRoleScanner
from k8s_purify.scanners.rolebindings import RoleBindingScanner
from k8s_purify.scanners.clusterrolebindings import ClusterRoleBindingScanner
from k8s_purify.scanners.serviceaccounts import ServiceAccountScanner
from k8s_purify.scanners.hpas import HPAScanner
from k8s_purify.scanners.jobs import JobScanner
from k8s_purify.scanners.pdbs import PDBScanner
from k8s_purify.scanners.networkpolicies import NetworkPolicyScanner
from k8s_purify.scanners.storageclasses import StorageClassScanner
from k8s_purify.scanners.priorityclasses import PriorityClassScanner

__all__ = [
    "ConfigMapScanner",
    "SecretScanner",
    "ServiceScanner",
    "DeploymentScanner",
    "StatefulSetScanner",
    "DaemonSetScanner",
    "ReplicaSetScanner",
    "PodScanner",
    "IngressScanner",
    "PVCScanner",
    "PVScanner",
    "RoleScanner",
    "ClusterRoleScanner",
    "RoleBindingScanner",
    "ClusterRoleBindingScanner",
    "ServiceAccountScanner",
    "HPAScanner",
    "JobScanner",
    "PDBScanner",
    "NetworkPolicyScanner",
    "StorageClassScanner",
    "PriorityClassScanner",
]
