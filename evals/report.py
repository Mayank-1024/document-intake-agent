"""Render an eval payload as Markdown."""

from __future__ import annotations

from typing import Any


def _pct(a: dict[str, Any]) -> str:
    if not a["fields"]:
        return "n/a (0 fields)"
    return f"{a['accuracy'] * 100:.1f}% ({a['correct']}/{a['fields']})"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(v: Any) -> str:
        return "" if v is None else str(v).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def render_markdown(p: dict[str, Any]) -> str:
    s = p["summary"]
    r, e = s["routing"], s["errors"]
    out = [f"# Eval report: {p['mode']} / {p['model']}", "",
           f"Generated {p['generated_at']} (UTC). Confidence threshold {s['threshold']}.", "",
           f"> {p['disclaimer']}", ""]
    if p.get("injected_faults"):
        out += ["Injected faults:", ""]
        out += [f"- `{k}`: {v}" for k, v in p["injected_faults"].items()]
        out.append("")

    out += ["## Summary", "", _table(["Metric", "Value"], [
        ["Documents", s["documents"]],
        ["Fields scored", s["fields"]],
        ["Field accuracy, all", _pct(s["accuracy_overall"])],
        ["Auto-accepted documents", r["auto_accept"]],
        ["Documents sent to review", r["needs_review"]],
        ["Hard cases sent to review", f"{r['hard_cases_sent_to_review']} of "
                                      f"{r['hard_cases_expected_review']}"],
        ["Hard cases flagged for the expected reason", r["hard_cases_with_expected_reason"]],
        ["Clean documents sent to review",
         f"{r['clean_docs_sent_to_review']} of {r['clean_docs']}"],
        ["...of which had no wrong field (false alarms)", r["false_alarms"]],
        ["Wrong fields", e["wrong_fields"]],
        ["Wrong fields in reviewed documents (caught, document level)", e["caught_doc_level"]],
        ["...wrong values the model produced / fields it never produced",
         f"{e['wrong_produced']} / {e['not_produced']}"],
        ["Wrong produced values individually flagged (caught, field level)",
         f"{e['caught_field_level']} of {e['wrong_produced']}"],
        ["Wrong fields in auto-accepted documents (missed)", e["missed_in_auto_accepted_docs"]],
        ["Documents that needed the schema retry", s["retries"]],
        ["Extraction failures (invalid twice, or API error)", s["extraction_failures"]],
        ["PII strings masked by code", s["pii_strings_masked_by_code"]],
        ["Total cost (USD)", s["cost"]["total_usd"]],
        ["Mean cost per document (USD)", s["cost"]["mean_usd_per_doc"]],
        ["Input / output tokens", f"{s['cost']['input_tokens']:,} / "
                                  f"{s['cost']['output_tokens']:,}"],
        ["Latency per document, mean / p50 / p95 / max (ms)",
         f"{s['latency_ms']['mean']} / {s['latency_ms']['p50']} / {s['latency_ms']['p95']} / "
         f"{s['latency_ms']['max']}"],
    ]), ""]

    out += ["## Field accuracy", "",
            _table(["Slice", "Accuracy"],
                   [[f"type: {k}", _pct(v)] for k, v in s["accuracy_by_doc_type"].items()]
                   + [[f"variant: {k}", _pct(v)] for k, v in s["accuracy_by_variant"].items()]
                   + [["fields in auto-accepted docs", _pct(s["accuracy_by_route"]["auto_accept"])],
                      ["fields in review docs", _pct(s["accuracy_by_route"]["needs_review"])],
                      ["flagged fields", _pct(s["accuracy_by_field_flag"]["flagged"])],
                      ["unflagged fields", _pct(s["accuracy_by_field_flag"]["not_flagged"])]]),
            ""]

    out += ["## Wrong fields", ""]
    produced = [w for w in e["all_wrong"] if w["confidence"] is not None]
    if produced:
        out.append(_table(["Doc", "Field", "Truth", "Predicted", "Conf.", "Citation", "Flags",
                           "Route"],
                          [[w["doc_id"], w["path"], w["truth"], w["predicted"], w["confidence"],
                            w["citation"], ", ".join(w["flags"]), w["doc_route"]]
                           for w in produced]))
    else:
        out.append("No wrong values among the fields the model produced.")
    missing: dict[str, list[str]] = {}
    for w in e["all_wrong"]:
        if w["confidence"] is None:
            missing.setdefault(f"{w['doc_id']} ({w['doc_route']})", []).append(w["path"])
    if missing:
        out += ["", "Fields never produced (dropped rows or failed extraction):", ""]
        out += [f"- {doc}: {len(paths)} fields, e.g. {', '.join(paths[:4])}"
                for doc, paths in missing.items()]
    out.append("")

    out += ["## Confidence calibration", "",
            "Each field's self-reported confidence against whether it was right. Row fields "
            "share their row's confidence, so bins are not independent samples.", "",
            _table(["Confidence bin", "Fields", "Mean confidence", "Observed accuracy"],
                   [[c["bin"], c["fields"], c["mean_confidence"], c["observed_accuracy"]]
                    for c in s["calibration"]]), ""]

    out += ["## Threshold sweep (same run, other checks unchanged)", "",
            _table(["Threshold", "Auto-accepted docs", "Auto-accepted fields",
                    "Wrong fields auto-accepted"],
                   [[t["threshold"], t["auto_accepted_docs"], t["auto_accepted_fields"],
                     t["missed_errors"]] for t in s["threshold_sweep"]]), ""]

    out += ["## Documents", "",
            _table(["Doc", "Variant", "Expected", "Route", "Reasons", "Wrong/fields", "Tries",
                    "Tokens in/out", "Cost", "ms"],
                   [[d["doc_id"], d["variant"],
                     "review" if d["expected_review"] else "accept", d["route"],
                     ", ".join(d["reason_codes"]), f"{d['wrong_fields']}/{d['fields']}",
                     d["attempts"], f"{d['input_tokens']}/{d['output_tokens']}",
                     None if d["cost_usd"] is None else f"{d['cost_usd']:.5f}",
                     d["latency_ms"]] for d in s["documents_detail"]]), ""]

    out += ["## Review reasons per document", ""]
    for d in s["documents_detail"]:
        if d["reasons"]:
            out.append(f"- `{d['doc_id']}`: " + "; ".join(d["reasons"]))
    out.append("")
    return "\n".join(out)
