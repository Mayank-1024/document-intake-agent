import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app, offline_dataset_model
from evals.dataset import DATA
from intake.store import InvalidAction, Store
from tests.conftest import truth


@pytest.fixture(scope="module")
def model():
    return offline_dataset_model(DATA)


@pytest.fixture
def client(tmp_path, model):
    app = create_app(store=Store(tmp_path / "t.db"), model=model,
                     upload_dir=tmp_path / "uploads", threshold=0.9)
    return TestClient(app)


def upload(client, doc_id):
    t = truth(doc_id)
    path = DATA / t["file"]
    with path.open("rb") as fh:
        return client.post("/documents", data={"doc_type": t["doc_type"]},
                           files={"file": (path.name, fh, t["media_type"])})


def test_clean_document_is_auto_accepted_and_not_queued(client):
    r = upload(client, "inv-01")
    assert r.status_code == 201
    body = r.json()
    assert body["route"] == "auto_accept" and body["status"] == "auto_accepted"
    assert client.get("/review-queue").json() == []
    assert client.get(f"/documents/{body['id']}").json()["result"]["fields"][0]["citation"] \
        == "verified"


def test_review_flow_correct_then_approve_and_export(client):
    doc_id = upload(client, "inv-06").json()["id"]  # printed total does not add up
    queue = client.get("/review-queue").json()
    assert [q["id"] for q in queue] == [doc_id] and queue[0]["reason_codes"] == ["rule_failed"]

    r = client.post(f"/documents/{doc_id}/corrections",
                    json={"field": "total", "value": 2549.65, "reviewer": "mayank",
                          "note": "vendor typo; confirmed by phone"})
    assert r.status_code == 200
    assert r.json()["current_values"]["total"] == 2549.65
    assert r.json()["status"] == "in_review"  # a correction alone does not close the review

    r = client.post(f"/documents/{doc_id}/approve", json={"reviewer": "mayank"})
    assert r.json()["status"] == "corrected"
    assert client.get("/review-queue").json() == []

    exported = client.get("/corrections").json()
    assert exported[0]["field"] == "total" and exported[0]["previous_value"] == 2567.65
    assert exported[0]["corrected_value"] == 2549.65 and len(exported[0]["sha256"]) == 64

    again = client.post(f"/documents/{doc_id}/approve", json={"reviewer": "mayank"})
    assert again.status_code == 409


def test_correction_validation(client):
    doc_id = upload(client, "w2-05").json()["id"]
    assert client.post(f"/documents/{doc_id}/corrections",
                       json={"field": "nope", "value": 1, "reviewer": "m"}).status_code == 409
    assert client.post(f"/documents/{doc_id}/corrections",
                       json={"field": "total", "value": 1}).status_code == 422
    assert client.post("/documents/missing/approve", json={"reviewer": "m"}).status_code == 404


def test_ssn_correction_is_stored_masked(client, tmp_path):
    doc_id = upload(client, "w2-07").json()["id"]  # scan: in review
    client.post(f"/documents/{doc_id}/corrections",
                json={"field": "employee_ssn", "value": "000-12-3456", "reviewer": "m"})
    raw = (tmp_path / "t.db").read_bytes()
    assert b"000-12-3456" not in raw
    assert client.get("/corrections").json()[0]["corrected_value"] == "XXX-XX-3456"


def test_uploaded_file_is_served_back(client):
    doc_id = upload(client, "lr-08").json()["id"]
    r = client.get(f"/documents/{doc_id}/file")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_bad_uploads(client):
    r = client.post("/documents", data={"doc_type": "invoice"},
                    files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415
    r = client.post("/documents", data={"doc_type": "receipt"},
                    files={"file": ("x.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 422
    r = client.post("/documents", data={"doc_type": "invoice"},
                    files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 422


def test_unknown_document_with_offline_model_goes_to_review(client):
    from io import BytesIO

    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "Invoice INV-1 Total $10.00")
    c.save()
    r = client.post("/documents", data={"doc_type": "invoice"},
                    files={"file": ("new.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 201
    assert r.json()["route"] == "needs_review"
    assert r.json()["reason_codes"] == ["model_error"]


def test_store_rejects_actions_on_auto_accepted(tmp_path, model):
    from intake.documents import load_path
    from intake.pipeline import process
    store = Store(tmp_path / "s.db")
    t = truth("w2-01")
    result = process(load_path(DATA / t["file"]), "w2", model, threshold=0.9)
    store.save_result(result)
    with pytest.raises(InvalidAction):
        store.approve(result.document_id, "m")
    assert json.dumps(store.get(result.document_id)).count("XXX-XX-") >= 1
