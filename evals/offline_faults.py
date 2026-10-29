"""Scripted answers for offline evals: perfect answers plus injected faults.

Offline mode tests the harness: does each kind of model mistake get caught by
the check designed for it, and does the scorer count it correctly? The faults
are hand-picked, so the offline numbers say nothing about model quality.

One fault (inv-10, customer_name set to the vendor's name with a real
citation) is designed to slip past every check, so the report must show it
as a missed error. That proves the eval measures misses instead of assuming
the checks are complete.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from evals.dataset import Case
from intake.documents import LoadedDocument
from intake.scripted_model import answer_from_truth

FAULTS = {
    "inv-03": "confident wrong total, true citation (value_not_in_citation + arithmetic rule)",
    "inv-04": "misspelled vendor with an invented citation (not_found)",
    "inv-10": "customer_name set to the vendor name, citing the vendor line (built to be missed)",
    "w2-02": "first answer invalid (confidence 1.4, non-ISO date), second answer valid (retry)",
    "w2-03": "model returns the full SSN; code masks it before storage",
    "w2-04": "correct wages with confidence 0.60 (false alarm, review)",
    "lr-01": "claims[0].paid has swapped digits, row citation is the true row (citation + rule)",
    "lr-02": "one claim row dropped (sum rules fail; missing row fields count as errors)",
    "lr-10": "both answers invalid (extraction_invalid, review)",
}


def _swap_digits(x: float) -> float:
    s = f"{x:.2f}"
    digits = [i for i, ch in enumerate(s) if ch.isdigit()]
    a, b = digits[0], digits[1]
    if s[a] == s[b]:
        return round(x + 9.0, 2)
    lst = list(s)
    lst[a], lst[b] = lst[b], lst[a]
    return float("".join(lst))


def scripted_answers(case: Case, doc: LoadedDocument) -> list[str | dict[str, Any]]:
    good = answer_from_truth(case.truth)
    a = copy.deepcopy(good)
    match case.doc_id:
        case "inv-03":
            a["total"]["value"] = round(a["total"]["value"] + 100, 2)
        case "inv-04":
            v = a["vendor_name"]["value"]
            a["vendor_name"]["value"] = v[:3] + v[4] + v[3] + v[5:]  # transposed letters
            a["vendor_name"]["source_text"] = a["vendor_name"]["value"]
        case "inv-10":
            a["customer_name"] = copy.deepcopy(a["vendor_name"])
            a["customer_name"]["confidence"] = 0.95
        case "w2-02":
            bad = copy.deepcopy(good)
            bad["wages"]["confidence"] = 1.4
            bad["tax_year"]["value"] = "tax year 2025"
            return [bad, good]
        case "w2-03":
            full = re.search(r"\b\d{3}-\d{2}-\d{4}\b", (doc.page_texts or [""])[0]).group(0)
            a["employee_ssn"]["value"] = full
            a["employee_ssn"]["source_text"] = f"a Employee's social security number {full}"
        case "w2-04":
            a["wages"]["confidence"] = 0.60
        case "lr-01":
            a["claims"][0]["paid"] = _swap_digits(a["claims"][0]["paid"])
        case "lr-02":
            del a["claims"][1]
        case "lr-10":
            return ["{not json", json.dumps({"carrier_name": "only one field"})]
    return [a]
