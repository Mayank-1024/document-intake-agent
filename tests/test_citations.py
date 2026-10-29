import pytest

from intake.checks import check_citation, value_renderings
from intake.documents import squash
from intake.fields import FieldView
from intake.pipeline import process
from intake.schemas import ITEM_KEY
from intake.scripted_model import ScriptedModel
from tests.conftest import doc, good_answer


def fv(value, source, kind="text", page=1):
    return FieldView("x", kind, value, 0.95, page, source)


def test_every_ground_truth_citation_verifies_on_text_documents(cases):
    """Generator and checker agree: the printed text recorded as truth is found where it says."""
    checked = 0
    for c in cases.values():
        d = c.load()
        r = process(d, c.doc_type, ScriptedModel({d.sha256: [good_answer(c.doc_id)]}),
                    threshold=0.9)
        for f in r.fields:
            expected = "absent" if f.value is None else (
                "verified" if d.has_text_layer else "unverifiable")
            assert f.citation == expected, (c.doc_id, f.path, f.citation)
            checked += 1
    assert checked > 1000


def test_squash_ignores_whitespace_and_case():
    assert squash("Invoice  No.:\nINV-1") == squash("invoice no.: inv-1")


@pytest.mark.parametrize("kind,value,printed", [
    ("money", 1962.4, "$1,962.40"), ("money", 0.0, "0.00"), ("money", 500.0, "500"),
    ("date", "2026-09-04", "September 4, 2026"), ("date", "2026-02-26", "02/26/2026"),
    ("date", "2024-07-01", "2024-07-01"), ("int", 2025, "2025"), ("number", 24.0, "24"),
])
def test_value_renderings_cover_common_print_formats(kind, value, printed):
    assert any(squash(r) in squash(printed) for r in value_renderings(kind, value))


def test_statuses():
    d = doc("inv-01")
    assert check_citation(fv("INV-24287", "Invoice No.: INV-24287"), d) == "verified"
    assert check_citation(fv(None, None), d) == "absent"
    assert check_citation(fv("INV-24287", None), d) == "missing_citation"
    assert check_citation(fv("INV-99999", "Invoice No.: INV-99999"), d) == "not_found"
    assert check_citation(fv("INV-99999", "Invoice No.: INV-24287"), d) == \
        "value_not_in_citation"
    assert check_citation(fv(2085.05, "Total Due $2,085.05", "money"), d) == "verified"
    assert check_citation(fv(2085.50, "Total Due $2,085.05", "money"), d) == \
        "value_not_in_citation"


def test_wrong_page_detected():
    d = doc("inv-05")  # two pages
    a = good_answer("inv-05")
    a["total"]["page"] = 1  # totals are printed on page 2
    r = process(d, "invoice", ScriptedModel({d.sha256: [a]}), threshold=0.9)
    total = next(f for f in r.fields if f.path == "total")
    assert total.citation == "wrong_page"
    assert r.route == "needs_review"


def test_scanned_document_is_unverifiable_but_still_checks_value_in_citation():
    d = doc("inv-08")
    assert not d.has_text_layer
    assert check_citation(fv("B1", "Bill Number: B1"), d) == "unverifiable"
    assert check_citation(fv("B2", "Bill Number: B1"), d) == "value_not_in_citation"


def test_row_citation_must_contain_each_cell():
    d = doc("lr-01")
    a = good_answer("lr-01")
    key = ITEM_KEY["loss_run"]
    a[key][0]["reserved"] = a[key][0]["reserved"] + 1000
    r = process(d, "loss_run", ScriptedModel({d.sha256: [a]}), threshold=0.9)
    by = {f.path: f for f in r.fields}
    assert by["claims[0].reserved"].citation == "value_not_in_citation"
    assert by["claims[0].paid"].citation == "verified"
