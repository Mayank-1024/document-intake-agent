from intake.checks import RuleResult
from intake.fields import FieldView
from intake.pipeline import process
from intake.routing import AUTO_ACCEPT, NEEDS_REVIEW, route
from intake.scripted_model import ScriptedModel
from tests.conftest import doc, good_answer


def f(path, value="v", conf=0.95, citation="verified"):
    x = FieldView(path, "text", value, conf, 1, "v")
    x.citation = citation
    return x


def test_all_clear_is_auto_accept():
    decision, reasons = route([f("a"), f("b")], [RuleResult("r", "pass")], ("a",), 0.9, True)
    assert decision == AUTO_ACCEPT and reasons == []


def test_each_reason_routes_to_review_and_flags_the_field():
    fields = [f("low", conf=0.5), f("cite", citation="not_found"), f("req", value=None,
                                                                       citation="absent"),
              f("ruled")]
    rules = [RuleResult("sum", "fail", "bad sum", ["ruled"]), RuleResult("skip", "skipped")]
    decision, reasons = route(fields, rules, ("req",), 0.9, True)
    assert decision == NEEDS_REVIEW
    assert {r.code for r in reasons} == {"low_confidence", "citation_failed", "missing_required",
                                         "rule_failed"}
    flags = {x.path: x.flags for x in fields}
    assert flags["low"] == ["low_confidence"]
    assert flags["cite"] == ["citation:not_found"]
    assert flags["req"] == ["missing_required"]
    assert flags["ruled"] == ["rule:sum"]


def test_threshold_is_inclusive():
    assert route([f("a", conf=0.9)], [], (), 0.9, True)[0] == AUTO_ACCEPT
    assert route([f("a", conf=0.899)], [], (), 0.9, True)[0] == NEEDS_REVIEW


def test_no_text_layer_always_reviews():
    decision, reasons = route([f("a", citation="unverifiable")], [], (), 0.9, False)
    assert decision == NEEDS_REVIEW and reasons[0].code == "no_text_layer"


def test_pipeline_routes_planted_hard_cases_with_perfect_answers(cases):
    for c in cases.values():
        d = c.load()
        r = process(d, c.doc_type, ScriptedModel({d.sha256: [good_answer(c.doc_id)]}),
                    threshold=0.9)
        assert (r.route == NEEDS_REVIEW) == c.truth["expected_review"], c.doc_id
        if c.truth["expected_reason"]:
            assert c.truth["expected_reason"] in {x.code for x in r.reasons}, c.doc_id


def test_hallucinated_value_for_missing_field_is_caught():
    d = doc("inv-07")  # invoice_date is not printed
    a = good_answer("inv-07")
    a["invoice_date"] = {"value": "2026-03-01", "confidence": 0.95, "page": 1,
                         "source_text": "Invoice Date: 03/01/2026"}
    r = process(d, "invoice", ScriptedModel({d.sha256: [a]}), threshold=0.9)
    inv = next(x for x in r.fields if x.path == "invoice_date")
    assert inv.citation == "not_found"
    assert r.route == NEEDS_REVIEW
