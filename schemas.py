from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Request Models ---

class DeviceCreate(BaseModel):
    """Model for a single device row in the CSV."""
    device_id: str
    hostname: str
    bitlocker_status: str
    last_seen: str

# --- Response Models ---

class DeviceResponse(BaseModel):
    """Model returned when querying a device."""
    device_id: str
    hostname: str
    bitlocker_status: str
    last_seen: str
    is_compliant: bool

    class Config:
        from_attributes = True # Allows converting SQLAlchemy/psycopg2 rows to Pydantic models

class IngestResponse(BaseModel):
    """Summary of the CSV ingestion process."""
    message: str
    processed_count: int
    skipped_count: int

class EvaluateResponse(BaseModel):
    """Summary of the policy evaluation."""
    message: str
    total_devices: int
    compliant_count: int
    non_compliant_count: int
    queued_for_alert: int   # <-- exposed: how many violations landed in the outbox


class AlertResponse(BaseModel):
    """Summary of the alert dispatch."""
    message: str
    alerts_sent: int
    failed_alerts: int