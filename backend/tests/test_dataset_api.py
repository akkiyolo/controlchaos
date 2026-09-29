"""Tests for Dataset API endpoints: generation, trial balance, and drilldowns."""

from app.services.generator.ledger_generator import SyntheticLedgerGenerator
from app.services.generator.models import GeneratorParams
from app.services.generator.writer import BulkDatasetWriter


def test_dataset_generation_and_trial_balance(client, auth_headers, db_session):
    headers = auth_headers["analyst"]

    # 1. Trigger dataset generation
    payload = {
        "name": "Integration Test Ledger",
        "seed": 777,
        "entities_count": 2,
        "months": 3,
        "volume": "low",
        "industry_profile": "bank",
        "include_decoys": True,
    }
    gen_res = client.post("/api/v1/datasets/generate", json=payload, headers=headers)
    assert gen_res.status_code == 200
    job_info = gen_res.json()
    job_id = job_info["id"]

    # 2. Check job status endpoint
    job_res = client.get(f"/api/v1/datasets/jobs/{job_id}", headers=headers)
    assert job_res.status_code == 200
    assert job_res.json()["type"] == "dataset_generation"

    # Wait or generate synchronously via service to test retrieval endpoints directly
    entities_data = [
        {"id": "e-1", "code": "LE-100", "name": "Entity 1", "currency": "USD", "region": "AMER"},
        {"id": "e-2", "code": "LE-200", "name": "Entity 2", "currency": "EUR", "region": "EMEA"},
    ]
    gen_params = GeneratorParams(**payload)
    generator = SyntheticLedgerGenerator(gen_params, entities_data)
    generated = generator.generate_all()

    dataset = BulkDatasetWriter.write_dataset(
        db=db_session,
        generated=generated,
        params_dict=payload,
        creator_email="analyst@test.local",
    )

    # 3. List datasets
    list_res = client.get("/api/v1/datasets", headers=headers)
    assert list_res.status_code == 200
    datasets = list_res.json()["datasets"]
    assert any(d["id"] == dataset.id for d in datasets)

    # 4. Trial Balance inspection
    tb_res = client.get(f"/api/v1/datasets/{dataset.id}/trial-balance", headers=headers)
    assert tb_res.status_code == 200
    tb = tb_res.json()
    assert tb["is_balanced"] is True
    assert tb["net_difference"] < 0.01
    assert tb["sum_debit"] > 0
    assert abs(tb["sum_debit"] - tb["sum_credit"]) < 0.01

    # 5. GL Entries inspection
    gl_res = client.get(f"/api/v1/datasets/{dataset.id}/gl-entries?limit=10", headers=headers)
    assert gl_res.status_code == 200
    entries = gl_res.json()
    assert len(entries) > 0
    assert entries[0]["dataset_id"] == dataset.id

    # 6. Decoys inspection
    decoy_res = client.get(f"/api/v1/datasets/{dataset.id}/decoys", headers=headers)
    assert decoy_res.status_code == 200
    decoys = decoy_res.json()
    assert "decoys" in decoys
