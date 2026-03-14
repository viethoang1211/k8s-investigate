"""Job scanner - finds completed or failed Jobs."""

from __future__ import annotations

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner

_FAILED_REASONS = {"BackoffLimitExceeded", "DeadlineExceeded", "FailedIndexes"}


@register_scanner
class JobScanner(BaseScanner):
    resource_type = "jobs"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        jobs = self.k8s.batch_v1.list_namespaced_job(namespace).items

        for job in jobs:
            if self.should_skip(job.metadata):
                continue
            if self.is_marked_unused(job.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Job",
                    name=job.metadata.name, reason="Marked as unused via label",
                ))
                continue

            status = job.status
            if not status:
                continue

            # Completed jobs
            if status.completion_time and (status.succeeded or 0) > 0:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Job",
                    name=job.metadata.name, reason="Job completed successfully",
                ))
                continue

            # Failed jobs
            for cond in status.conditions or []:
                if cond.type == "Failed" and cond.status == "True" and cond.reason in _FAILED_REASONS:
                    results.append(UnusedResource(
                        namespace=namespace, resource_type="Job",
                        name=job.metadata.name,
                        reason=f"Job failed: {cond.reason}",
                    ))
                    break

            # Suspended jobs
            if job.spec.suspend:
                for cond in status.conditions or []:
                    if cond.type == "Suspended" and cond.status == "True":
                        results.append(UnusedResource(
                            namespace=namespace, resource_type="Job",
                            name=job.metadata.name, reason="Job is suspended",
                        ))
                        break
        return results
