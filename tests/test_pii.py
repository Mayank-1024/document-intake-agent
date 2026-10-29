import io
import json
import logging

from intake.observability import RedactingFormatter, log_event
from intake.pii import mask_response, mask_ssn, redact
from intake.pipeline import process
from intake.scripted_model import ScriptedModel
from tests.conftest import doc, good_answer


def test_mask_ssn_formats():
    assert mask_ssn("000-24-5506") == "XXX-XX-5506"
    assert mask_ssn("000 24 5506") == "XXX-XX-5506"
    assert mask_ssn("000245506") == "XXX-XX-5506"
    assert mask_ssn("XXX-XX-5506") == "XXX-XX-5506"


def test_redact_only_touches_separated_ssns():
    assert redact("ssn 000-24-5506 ok") == "ssn XXX-XX-5506 ok"
    assert redact("invoice 123456789 ein 85-1860076 phone 555-123-4567") == \
        "invoice 123456789 ein 85-1860076 phone 555-123-4567"


def test_mask_response_masks_pii_field_and_free_text():
    data = {"employee_ssn": {"value": "000245506", "source_text": "SSN 000-24-5506"},
            "employer_name": {"value": "Acme", "source_text": "note 000-11-2222"}}
    masked, n = mask_response(data, ("employee_ssn",))
    assert masked["employee_ssn"]["value"] == "XXX-XX-5506"
    assert masked["employee_ssn"]["source_text"] == "SSN XXX-XX-5506"
    assert masked["employer_name"]["source_text"] == "note XXX-XX-2222"
    assert n == 3


def test_full_ssn_from_model_is_masked_before_storage_and_still_verifies():
    d = doc("w2-01")
    full = next(t for t in d.page_texts[0].split() if t.count("-") == 2)
    a = good_answer("w2-01")
    a["employee_ssn"]["value"] = full
    a["employee_ssn"]["source_text"] = full
    r = process(d, "w2", ScriptedModel({d.sha256: [a]}), threshold=0.9)
    dumped = json.dumps(r.to_dict(), default=str)
    assert full not in dumped
    assert r.extraction["employee_ssn"]["value"] == "XXX-XX-" + full[-4:]
    assert r.pii_masked == 2
    ssn = next(f for f in r.fields if f.path == "employee_ssn")
    assert ssn.citation == "verified"  # last four checked against the real page text
    assert r.route == "auto_accept"


def test_wrong_last_four_fails_citation():
    d = doc("w2-01")
    a = good_answer("w2-01")
    a["employee_ssn"]["value"] = a["employee_ssn"]["source_text"] = "XXX-XX-0000"
    r = process(d, "w2", ScriptedModel({d.sha256: [a]}), threshold=0.9)
    ssn = next(f for f in r.fields if f.path == "employee_ssn")
    assert ssn.citation == "not_found"
    assert r.route == "needs_review"


def test_log_formatter_redacts_ssn():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(RedactingFormatter())
    logger = logging.getLogger("test.pii")
    logger.handlers[:] = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_event(logger, "oops 000-24-5506", detail="value 000-11-2222")
    line = stream.getvalue()
    assert "5506" in line and "000-24-5506" not in line and "000-11-2222" not in line


def test_no_ground_truth_file_contains_a_full_ssn(cases):
    from intake.pii import SEPARATED_SSN
    for c in cases.values():
        assert not SEPARATED_SSN.search(json.dumps(c.truth)), c.doc_id
