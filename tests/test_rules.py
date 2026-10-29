import copy
from datetime import date

from intake.checks import invoice_rules, loss_run_rules, run_rules, w2_rules
from intake.schemas import parse_extraction
from tests.conftest import good_answer, truth


def parsed(doc_id: str, mutate=None):
    a = copy.deepcopy(good_answer(doc_id))
    if mutate:
        mutate(a)
    t = truth(doc_id)
    return parse_extraction(t["doc_type"], a, t["pages"])


def status(results, name):
    return next(r for r in results if r.rule == name).status


def failed(results):
    return {r.rule for r in results if r.status == "fail"}


def test_clean_documents_pass_every_rule(cases):
    for c in cases.values():
        if c.truth["expected_reason"] == "rule_failed":
            continue
        results = run_rules(c.doc_type, parsed(c.doc_id))
        assert not failed(results), (c.doc_id, failed(results))


def test_planted_inconsistencies_fail_the_right_rule():
    assert "subtotal_plus_tax_equals_total" in failed(invoice_rules(parsed("inv-06")))
    assert "social_security_tax_is_6.2_percent" in failed(w2_rules(parsed("w2-06")))
    assert {"claims_incurred_sum_to_total_incurred",
            "total_paid_plus_reserved_equals_incurred"} <= failed(loss_run_rules(parsed("lr-05")))
    assert "losses_inside_policy_period" in failed(loss_run_rules(parsed("lr-06")))


def test_invoice_line_math_and_subtotal():
    def bump(a):
        a["line_items"][0]["amount"] += 1.00

    r = invoice_rules(parsed("inv-01", bump))
    assert "line_items[0]_qty_times_price" in failed(r)
    assert "line_items_sum_to_subtotal" in failed(r)
    bad = next(x for x in r if x.rule == "line_items_sum_to_subtotal")
    assert "subtotal" in bad.fields and "line_items[0].amount" in bad.fields


def test_one_cent_tolerance_on_total():
    def off_by(c):
        def m(a):
            a["total"]["value"] = round(a["total"]["value"] + c, 2)
        return m

    assert status(invoice_rules(parsed("inv-01", off_by(0.01))),
                  "subtotal_plus_tax_equals_total") == "pass"
    assert status(invoice_rules(parsed("inv-01", off_by(0.02))),
                  "subtotal_plus_tax_equals_total") == "fail"


def test_terms_and_dates():
    def late(a):
        a["due_date"]["value"] = "2026-01-01"

    r = invoice_rules(parsed("inv-01", late))
    assert {"due_date_not_before_invoice_date", "net_terms_match_due_date"} <= failed(r)


def test_rules_skip_when_inputs_missing():
    r = invoice_rules(parsed("inv-07"))  # invoice_date not printed
    assert status(r, "due_date_not_before_invoice_date") == "skipped"
    assert status(r, "net_terms_match_due_date") == "skipped"


def test_w2_rates_boundaries():
    def ss(delta):
        def m(a):
            a["social_security_tax_withheld"]["value"] = round(
                a["social_security_wages"]["value"] * 0.062 + delta, 2)
        return m

    assert status(w2_rules(parsed("w2-01", ss(0.99))), "social_security_tax_is_6.2_percent") \
        == "pass"
    assert status(w2_rules(parsed("w2-01", ss(1.02))), "social_security_tax_is_6.2_percent") \
        == "fail"

    def high(a):
        for k in ("medicare_wages", "social_security_wages"):
            a[k]["value"] = 250000.0
        a["medicare_tax_withheld"]["value"] = 4525.0

    r = w2_rules(parsed("w2-01", high))
    assert status(r, "medicare_tax_is_1.45_percent") == "skipped"
    assert "social_security_wages_within_wage_base" in failed(r)


def test_w2_ein_and_withholding():
    def m(a):
        a["employer_ein"]["value"] = "851860076"
        a["federal_income_tax_withheld"]["value"] = a["wages"]["value"] + 1

    assert {"ein_format", "withholding_below_wages"} <= failed(w2_rules(parsed("w2-01", m)))


def test_loss_run_claim_math_closed_reserve_and_period():
    def m(a):
        a["claims"][0]["incurred"] += 5
        closed = next(c for c in a["claims"] if c["status"] == "closed")
        closed["reserved"] = 100.0
        a["policy_period_end"]["value"] = a["policy_period_start"]["value"]

    r = loss_run_rules(parsed("lr-01", m))
    f = failed(r)
    assert "claims[0]_paid_plus_reserve_equals_incurred" in f
    assert any(x.endswith("_closed_has_no_reserve") for x in f)
    assert "policy_period_start_before_end" in f


def test_no_claims_loss_run_passes():
    r = loss_run_rules(parsed("lr-07"))
    assert not failed(r)
    assert status(r, "claims_paid_sum_to_total_paid") == "pass"


def test_date_out_of_period_names_the_claim():
    r = loss_run_rules(parsed("lr-06"))
    bad = next(x for x in r if x.rule == "losses_inside_policy_period")
    assert bad.fields == ["claims[1].date_of_loss"]
    t = truth("lr-06")
    assert date.fromisoformat(t["claims"][1]["date_of_loss"]) > \
        date.fromisoformat(t["fields"]["policy_period_end"]["value"])
