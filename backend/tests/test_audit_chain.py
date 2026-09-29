"""Tests for the tamper-evident hash-chained audit service and verification."""

from app.services.audit.service import AuditService, canonical_json


def test_canonical_json_determinism():
    data1 = {"b": 2, "a": 1, "c": {"y": "test", "x": 10}}
    data2 = {"a": 1, "c": {"x": 10, "y": "test"}, "b": 2}
    assert canonical_json(data1) == canonical_json(data2)
    assert " " not in canonical_json(data1)  # Compact no whitespace


def test_audit_log_append_and_verify(db_session):
    # Empty chain is intact
    is_intact, count, broken = AuditService.verify_chain(db_session)
    assert is_intact is True
    assert count == 0

    # Record 3 events
    e1 = AuditService.record(
        db=db_session,
        actor="alice@bank.local",
        action="DATASET_GENERATE",
        entity_type="dataset",
        entity_id="ds-100",
        payload={"entities": 5, "seed": 42},
    )
    e2 = AuditService.record(
        db=db_session,
        actor="bob@bank.local",
        action="MUTATION_INJECT",
        entity_type="mutation",
        entity_id="mut-200",
        payload={"class": "duplicate_posting"},
    )
    e3 = AuditService.record(
        db=db_session,
        actor="carol@bank.local",
        action="RUN_EXECUTE",
        entity_type="run",
        entity_id="run-300",
        payload={"controls_count": 15},
    )

    # Chaining pointers
    assert e1.prev_hash == "0" * 64
    assert e2.prev_hash == e1.hash
    assert e3.prev_hash == e2.hash

    # Verify chain
    is_intact, count, broken = AuditService.verify_chain(db_session)
    assert is_intact is True
    assert count == 3
    assert broken is None


def test_audit_chain_tamper_detection(db_session):
    # Create two records
    e1 = AuditService.record(
        db=db_session,
        actor="user1",
        action="ACTION_1",
        entity_type="entity",
        entity_id="1",
        payload={"amount": 100},
    )
    AuditService.record(
        db=db_session,
        actor="user2",
        action="ACTION_2",
        entity_type="entity",
        entity_id="2",
        payload={"amount": 200},
    )

    # Tamper with record 1 payload directly
    e1.payload = {"amount": 999999}
    db_session.commit()

    # Verify must flag broken chain
    is_intact, count, broken = AuditService.verify_chain(db_session)
    assert is_intact is False
    assert broken is not None
    assert broken["entry_id"] == e1.id
    assert "Tampered record" in broken["reason"]
