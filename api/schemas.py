from typing import Optional

from pydantic import BaseModel, Field


class QuickAuditRequest(BaseModel):
    url: str = Field(..., min_length=1)


class FullAuditRequest(BaseModel):
    url: str = Field(..., min_length=1)
    domain: Optional[str] = None
    client_ref: Optional[str] = None


class JobEnqueueResponse(BaseModel):
    job_id: str
    status: str
    url: str
    domain: str
