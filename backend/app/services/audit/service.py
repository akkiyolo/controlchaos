"""Tamper-evident, append-only hash-chained audit log service."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import AuditLog

settings = get_settings()

GENESIS_PREV_HASH = "0" * 64


def canonical_json(data: Dict[str, Any]) -> str:
    """Produces deterministic, canonical JSON for hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def format_audit_ts(dt: Any) -> str:
    """Normalizes any datetime or string to consistent UTC ISO 8601 string."""
    if isinstance(dt, str):
        dt_str = dt.replace(" ", "T")
        if not dt_str.endswith("Z") and "+00:00" not in dt_str and "-" not in dt_str[-6:]:
            dt_str += "+00:00"
        return dt_str
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)


def compute_audit_hash(prev_hash: str, record_dict: Dict[str, Any], salt: str = "") -> str:
    """Computes SHA-256(prev_hash || canonical_json(record) || salt)."""
    serialized = canonical_json(record_dict)
    hasher = hashlib.sha256()
    hasher.update(prev_hash.encode("utf-8"))
    hasher.update(serialized.encode("utf-8"))
    if salt:
        hasher.update(salt.encode("utf-8"))
    return hasher.hexdigest()


class AuditService:
    @staticmethod
    def record(
        db: Session,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Appends a new audit record to the tamper-evident hash chain.
        Calculates the cryptographic hash chained to the latest existing entry.
        """
        payload = payload or {}
        latest_entry = db.scalar(
            select(AuditLog).order_by(desc(AuditLog.id)).limit(1)
        )
        prev_hash = latest_entry.hash if latest_entry else GENESIS_PREV_HASH

        now_utc = datetime.now(timezone.utc)
        ts_str = format_audit_ts(now_utc)

        record_content = {
            "actor": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "payload": payload,
            "ts": ts_str,
        }

        entry_hash = compute_audit_hash(prev_hash, record_content, settings.AUDIT_HASH_SALT)

        audit_entry = AuditLog(
            ts=now_utc,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            payload=payload,
            prev_hash=prev_hash,
            hash=entry_hash,
        )

        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry

    @staticmethod
    def verify_chain(db: Session) -> Tuple[bool, int, Optional[Dict[str, Any]]]:
        """
        Verifies the cryptographic integrity of the entire audit chain.
        Returns:
            (is_intact: bool, verified_count: int, broken_link_info: Optional[Dict])
        """
        entries = list(db.scalars(select(AuditLog).order_by(AuditLog.id.asc())).all())
        if not entries:
            return True, 0, None

        expected_prev_hash = GENESIS_PREV_HASH

        for idx, entry in enumerate(entries):
            # Check linkage with previous record
            if entry.prev_hash != expected_prev_hash:
                return False, idx, {
                    "entry_id": entry.id,
                    "expected_prev_hash": expected_prev_hash,
                    "actual_prev_hash": entry.prev_hash,
                    "reason": "Previous hash pointer mismatch",
                }

            # Recompute hash of record content using normalized timestamp
            record_content = {
                "actor": entry.actor,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id),
                "payload": entry.payload,
                "ts": format_audit_ts(entry.ts),
            }
            recomputed_hash = compute_audit_hash(
                expected_prev_hash, record_content, settings.AUDIT_HASH_SALT
            )

            if entry.hash != recomputed_hash:
                return False, idx, {
                    "entry_id": entry.id,
                    "expected_hash": recomputed_hash,
                    "actual_hash": entry.hash,
                    "reason": "Tampered record payload or corrupted hash",
                }

            expected_prev_hash = entry.hash

        return True, len(entries), None

    @staticmethod
    def list_entries(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> Tuple[List[AuditLog], int]:
        """Returns paginated audit log entries and total count."""
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        total_count = len(list(db.scalars(query).all()))
        entries = list(
            db.scalars(
                query.order_by(desc(AuditLog.id)).limit(limit).offset(offset)
            ).all()
        )
        return entries, total_count
