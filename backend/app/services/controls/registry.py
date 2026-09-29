"""Control Registry and Versioning Service with Maker-Checker Governance."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import assert_maker_checker
from app.models.entities import ControlDefinition, ControlVersion
from app.services.audit.service import AuditService
from app.services.controls.base import BaseControl
from app.services.controls.suite import ALL_CONTROLS


class ControlRegistry:
    """Central registry and life-cycle manager for financial controls."""

    def __init__(self) -> None:
        self._controls: Dict[str, BaseControl[Any]] = {}
        for cls in ALL_CONTROLS:
            instance = cls()
            self._controls[instance.key] = instance

    def get(self, key: str) -> Optional[BaseControl[Any]]:
        return self._controls.get(key)

    def list_all(self) -> List[BaseControl[Any]]:
        return list(self._controls.values())

    def seed_defaults(self, db: Session, audit_actor: str = "system") -> None:
        """Seed default control definitions into DB if they do not already exist."""
        existing = db.execute(select(ControlDefinition)).scalars().all()
        existing_keys = {c.key for c in existing}

        for ctrl in self.list_all():
            if ctrl.key not in existing_keys:
                default_params = ctrl.get_default_params()
                c_def = ControlDefinition(
                    key=ctrl.key,
                    name=ctrl.name,
                    category=ctrl.category,
                    description=ctrl.description,
                    params=default_params,
                    version=1,
                    status="active",
                    owner="control_owner@controlchaos.local",
                )
                db.add(c_def)
                db.flush()

                # Create version 1 record
                c_ver = ControlVersion(
                    control_id=c_def.id,
                    version=1,
                    params=default_params,
                    created_by=audit_actor,
                    approved_by=audit_actor,
                    diff={"initial": True},
                )
                db.add(c_ver)

                AuditService.record(
                    db=db,
                    actor=audit_actor,
                    action="control.seed",
                    entity_type="control_definition",
                    entity_id=c_def.id,
                    payload={"key": ctrl.key, "version": 1, "params": default_params},
                )

        db.commit()

    def propose_edit(
        self,
        db: Session,
        control_key: str,
        new_params: Dict[str, Any],
        maker: str,
        rationale: str,
    ) -> ControlVersion:
        """Propose parameter changes (Maker step). Creates a draft ControlVersion pending review."""
        ctrl = self.get(control_key)
        if not ctrl:
            raise ValueError(f"Control with key '{control_key}' not found in registry")

        # Validate params against typed model
        validated = ctrl.validate_params(new_params).model_dump()

        c_def = db.execute(select(ControlDefinition).where(ControlDefinition.key == control_key)).scalar_one_or_none()
        if not c_def:
            raise ValueError(f"Control definition for '{control_key}' not found in database")

        next_version = c_def.version + 1

        # Calculate diff between current active params and new params
        diff: Dict[str, Any] = {"rationale": rationale}
        for k, v in validated.items():
            old_v = c_def.params.get(k)
            if old_v != v:
                diff[k] = {"old": old_v, "new": v}

        draft_version = ControlVersion(
            control_id=c_def.id,
            version=next_version,
            params=validated,
            created_by=maker,
            approved_by=None,  # Pending checker approval
            diff=diff,
        )
        db.add(draft_version)

        AuditService.record(
            db=db,
            actor=maker,
            action="control.edit_proposed",
            entity_type="control_version",
            entity_id=draft_version.id,
            payload={
                "control_key": control_key,
                "proposed_version": next_version,
                "diff": diff,
            },
        )
        db.commit()
        db.refresh(draft_version)
        return draft_version

    def approve_edit(
        self,
        db: Session,
        control_key: str,
        version_id: str,
        checker: str,
        comment: Optional[str] = None,
    ) -> ControlDefinition:
        """Approve proposed parameter changes (Checker step).

        Enforces maker != checker rule, updates ControlDefinition active params, and logs to audit chain.
        """
        c_def = db.execute(select(ControlDefinition).where(ControlDefinition.key == control_key)).scalar_one_or_none()
        if not c_def:
            raise ValueError(f"Control '{control_key}' not found")

        draft = db.execute(
            select(ControlVersion).where(ControlVersion.id == version_id, ControlVersion.control_id == c_def.id)
        ).scalar_one_or_none()
        if not draft:
            raise ValueError(f"Version '{version_id}' not found for control '{control_key}'")

        if draft.approved_by is not None:
            raise ValueError("This version has already been approved or finalized")

        # Enforce maker-checker policy: maker != checker
        assert_maker_checker(draft.created_by, checker)

        draft.approved_by = checker
        c_def.params = draft.params
        c_def.version = draft.version

        AuditService.record(
            db=db,
            actor=checker,
            action="control.edit_approved",
            entity_type="control_definition",
            entity_id=c_def.id,
            payload={
                "control_key": control_key,
                "activated_version": draft.version,
                "maker": draft.created_by,
                "checker": checker,
                "comment": comment,
            },
        )
        db.commit()
        db.refresh(c_def)
        return c_def

    def reject_edit(
        self,
        db: Session,
        control_key: str,
        version_id: str,
        checker: str,
        comment: Optional[str] = None,
    ) -> None:
        """Reject proposed parameter changes (Checker step)."""
        c_def = db.execute(select(ControlDefinition).where(ControlDefinition.key == control_key)).scalar_one_or_none()
        if not c_def:
            raise ValueError(f"Control '{control_key}' not found")

        draft = db.execute(
            select(ControlVersion).where(ControlVersion.id == version_id, ControlVersion.control_id == c_def.id)
        ).scalar_one_or_none()
        if not draft:
            raise ValueError(f"Version '{version_id}' not found")

        if draft.approved_by is not None:
            raise ValueError("This version has already been decided")

        assert_maker_checker(draft.created_by, checker)

        draft.approved_by = f"REJECTED by {checker}"
        if draft.diff is None:
            draft.diff = {}
        draft.diff["status"] = "rejected"
        draft.diff["rejection_comment"] = comment

        AuditService.record(
            db=db,
            actor=checker,
            action="control.edit_rejected",
            entity_type="control_version",
            entity_id=draft.id,
            payload={
                "control_key": control_key,
                "rejected_version": draft.version,
                "maker": draft.created_by,
                "checker": checker,
                "comment": comment,
            },
        )
        db.commit()


registry = ControlRegistry()
