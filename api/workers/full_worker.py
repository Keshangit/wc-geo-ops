from __future__ import annotations

"""RQ worker entrypoint for full GEO audits.

Run: rq worker geo_full_audits --url $REDIS_URL
"""

from api.services.full_audit import run_full_audit_job


def process_full_audit(
    job_id: str,
    url: str,
    domain: str | None = None,
    client_ref: str | None = None,
) -> None:
    run_full_audit_job(job_id, url, domain, client_ref)


if __name__ == "__main__":
    import os
    import sys

    from redis import Redis
    from rq import SimpleWorker, Worker

    from api.config import get_settings

    # macOS: default RQ fork() crashes when requests/urllib3 loaded (objc fork safety)
    if sys.platform == "darwin":
        os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    queues = [settings.rq_queue_name]
    if len(sys.argv) > 1:
        queues = sys.argv[1:]

    worker_cls = SimpleWorker if sys.platform == "darwin" else Worker
    w = worker_cls(queues, connection=conn)
    w.work()
