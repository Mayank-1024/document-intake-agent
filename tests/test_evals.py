import json

import pytest

from evals.dataset import load_cases
from evals.run import main, run
from evals.scoring import align_rows, score_document, values_equal
from intake.pipeline import process
from intake.scripted_model import ScriptedModel
from tests.conftest import good_answer


@pytest.fixture(scope="module")
def offline():
    return run(load_cases(), "offline", "scripted", threshold=0.9)


def test_offline_run_accounts_for_every_injected_fault(offline):
    results, s = offline
    e, r = s["errors"], s["routing"]
    assert s["documents"] == 30
    assert r["hard_cases_sent_to_review"] == r["hard_cases_expected_review"] == 12
    assert r["hard_cases_with_expected_reason"] == 12
    # the one fault built to slip through every check is reported as missed
    assert e["missed_in_auto_accepted_docs"] == 1
    assert [(m["doc_id"], m["path"]) for m in e["missed"]] == [("inv-10", "customer_name")]
    # inv-03 total, inv-04 vendor, lr-01 paid are wrong values that get flagged
    flagged = {(w["doc_id"], w["path"]) for w in e["all_wrong"] if w["flags"]}
    assert flagged == {("inv-03", "total"), ("inv-04", "vendor_name"), ("lr-01", "claims[0].paid")}
    assert r["false_alarms"] == 1  # w2-04: correct value, low confidence
    assert s["retries"] == 2 and s["extraction_failures"] == 1
    assert s["pii_strings_masked_by_code"] == 2
    by = {d["doc_id"]: d for d in s["documents_detail"]}
    assert by["lr-02"]["wrong_fields"] == 6  # one dropped row, not a cascade of shifted rows
    assert by["w2-02"]["attempts"] == 2 and by["w2-02"]["route"] == "auto_accept"


def test_threshold_sweep_and_calibration_are_consistent(offline):
    results, s = offline
    at_09 = next(t for t in s["threshold_sweep"] if t["threshold"] == 0.9)
    assert at_09["auto_accepted_docs"] == s["routing"]["auto_accept"]
    # every field the model produced lands in exactly one calibration bin
    assert sum(b["fields"] for b in s["calibration"]) == sum(len(r.fields) for r in results)


def test_values_equal():
    assert values_equal("money", 10.0, 10.004)
    assert not values_equal("money", 10.0, 10.01)
    assert values_equal("text", "Halvorsen Tool & Die Inc.", "halvorsen tool & die inc")
    assert values_equal("text", None, None)
    assert not values_equal("text", None, "x")


def test_align_rows_handles_dropped_and_extra_rows():
    assert align_rows(["a", "b", "c"], ["a", "c"]) == [(0, 0), (1, None), (2, 1)]
    pairs = align_rows(["a", "b"], ["a", "x", "b"])
    assert (None, 1) in pairs and (1, 2) in pairs


def test_invented_row_counts_as_wrong(cases):
    c = cases["inv-01"]
    d = c.load()
    a = good_answer("inv-01")
    a["line_items"].append(dict(a["line_items"][0], description="Phantom widget"))
    r = process(d, "invoice", ScriptedModel({d.sha256: [a]}), threshold=0.9)
    wrong = [s for s in score_document(c, r) if not s.correct]
    assert wrong and all(w.path.startswith("extra:") for w in wrong)


def test_cli_writes_reports_without_pii(tmp_path):
    assert main(["--out", str(tmp_path), "--docs", "w2-01,w2-03,inv-06"]) == 0
    md = next(tmp_path.glob("offline-*.md")).read_text()
    js = json.loads(next(tmp_path.glob("offline-*.json")).read_text())
    assert "NOT a measure of model quality" in md
    assert js["summary"]["documents"] == 3
    text = json.dumps(js)
    assert "XXX-XX-" in text
    import re
    assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", text)
