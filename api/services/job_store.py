from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis

from api.config import get_settings

JOB_KEY_PREFIX = "geo:job:"


def _redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def create_job(url: str, domain: str, client_ref: str | None = None) -> str:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "job_id": job_id,
        "status": "queued",
        "url": url,
        "domain": domain,
        "client_ref": client_ref or "",
        "created_at": now,
        "completed_at": "",
        "duration_ms": "",
        "report": "",
        "error": "",
    }
    r = _redis()
    key = f"{JOB_KEY_PREFIX}{job_id}"
    r.hset(key, mapping=payload)
    r.expire(key, get_settings().job_ttl_seconds)
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    r = _redis()
    data = r.hgetall(f"{JOB_KEY_PREFIX}{job_id}")
    if not data:
        return None
    out: dict[str, Any] = dict(data)
    if out.get("report"):
        try:
            out["report"] = json.loads(out["report"])
        except json.JSONDecodeError:
            pass
    else:
        out["report"] = None
    if not out.get("error"):
        out["error"] = None
    for field in ("duration_ms",):
        if out.get(field) == "":
            out[field] = None
        elif out.get(field) is not None:
            try:
                out[field] = int(out[field])
            except (TypeError, ValueError):
                pass
    return out


def update_job(job_id: str, **fields: Any) -> None:
    r = _redis()
    key = f"{JOB_KEY_PREFIX}{job_id}"
    mapping: dict[str, str] = {}
    for k, v in fields.items():
        if v is None:
            mapping[k] = ""
        elif k == "report" and isinstance(v, (dict, list)):
            mapping[k] = json.dumps(v)
        else:
            mapping[k] = str(v)
    if mapping:
        r.hset(key, mapping=mapping)


def redis_available() -> bool:
    try:
        _redis().ping()
        return True
    except redis.RedisError:
        return False
