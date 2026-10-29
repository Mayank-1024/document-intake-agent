"""CLI: run the dataset through the pipeline and score it against ground truth.

    uv run python -m evals.run                          # offline, scripted model with faults
    uv run python -m evals.run --mode anthropic         # real model (needs ANTHROPIC_API_KEY)
    uv run python -m evals.run --mode anthropic --split stress  # only the 9 stress documents
    uv run python -m evals.run --mode anthropic --estimate      # token count + cost estimate only
    uv run python -m evals.run --mode anthropic --model claude-sonnet-5-5 --docs inv-01,w2-01

Writes evals/reports/<mode>-<model>-<timestamp>.json and .md.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from evals.dataset import Case, load_cases
from evals.offline_faults import FAULTS, scripted_answers
from evals.report import render_markdown
from evals.scoring import score_document, summarize
from intake.anthropic_model import AnthropicModel
from intake.observability import configure_logging
from intake.pii import SEPARATED_SSN
from intake.pipeline import IntakeResult, process
from intake.prompts import SYSTEM, user_prompt
from intake.schemas import output_json_schema
from intake.scripted_model import ScriptedModel
from settings import cost_usd, get_settings

REPORT_DIR = Path(__file__).resolve().parent / "reports"
DISCLAIMERS = {
    "offline": ("Offline mode: answers come from a scripted model built from ground truth with "
                "hand-injected faults (evals/offline_faults.py). This verifies the checks, routing "
                "and scoring. It is NOT a measure of model quality."),
    "anthropic": "Anthropic mode: answers come from the real Claude API.",
}


def run(cases: list[Case], mode: str, model_name: str, threshold: float,
        workers: int = 1) -> tuple[list[IntakeResult], dict]:
    docs = {c.doc_id: c.load() for c in cases}
    if mode == "offline":
        model = ScriptedModel({docs[c.doc_id].sha256: scripted_answers(c, docs[c.doc_id])
                               for c in cases})
    else:
        s = get_settings()
        model = AnthropicModel(model_name, effort=s.effort, max_tokens=s.max_tokens,
                               timeout_s=s.timeout_s, max_retries=s.sdk_max_retries)

    def one(c: Case) -> IntakeResult:
        return process(docs[c.doc_id], c.doc_type, model, threshold=threshold,
                       document_id=c.doc_id)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(one, cases))
    scores = [s for c, r in zip(cases, results, strict=True) for s in score_document(c, r)]
    return results, summarize(cases, results, scores, threshold)


def estimate(cases: list[Case], model_name: str, output_tokens_per_doc: int) -> None:
    import anthropic

    client = anthropic.Anthropic()
    total_in = 0
    for c in cases:
        doc = c.load()
        n = client.messages.count_tokens(
            model=model_name, system=SYSTEM,
            messages=[{"role": "user", "content": [
                doc.content_block(),
                {"type": "text", "text": user_prompt(c.doc_type, doc.page_count)}]}],
            output_config={"format": {"type": "json_schema",
                                      "schema": output_json_schema(c.doc_type)}}).input_tokens
        total_in += n
    out = output_tokens_per_doc * len(cases)
    est = cost_usd(model_name, total_in, out)
    print(f"{len(cases)} docs, {total_in:,} input tokens (counted), ~{out:,} output tokens "
          f"(assumed {output_tokens_per_doc}/doc, before any retries): "
          f"~${est:.4f} with {model_name}" if est is not None else "unknown price")


def write_reports(mode: str, model_name: str, summary: dict, results: list[IntakeResult],
                  out_dir: Path, split: str = "all") -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    payload = {"mode": mode, "model": model_name, "split": split, "generated_at": stamp,
               "disclaimer": DISCLAIMERS[mode],
               "injected_faults": FAULTS if mode == "offline" else None,
               "summary": summary, "results": [r.to_dict() for r in results]}
    text = json.dumps(payload, indent=2, default=str) + "\n"
    if SEPARATED_SSN.search(text):  # PII guard: a full SSN must never reach a report
        raise RuntimeError("refusing to write a report containing an unmasked SSN")
    base = out_dir / f"{mode}-{model_name}-{split}-{stamp}"
    json_path, md_path = base.with_suffix(".json"), base.with_suffix(".md")
    json_path.write_text(text)
    md_path.write_text(render_markdown(payload))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--mode", choices=["offline", "anthropic"], default="offline")
    p.add_argument("--model", default=None, help="model id (anthropic mode)")
    p.add_argument("--split", choices=["core", "stress", "all"], default="all")
    p.add_argument("--docs", default="", help="comma-separated doc ids (default: all)")
    p.add_argument("--threshold", type=float, default=None)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--estimate", action="store_true", help="count tokens and estimate cost only")
    p.add_argument("--assume-output-tokens", type=int, default=2500)
    p.add_argument("--out", type=Path, default=REPORT_DIR)
    args = p.parse_args(argv)

    s = get_settings()
    model_name = "scripted" if args.mode == "offline" else (args.model or s.model)
    threshold = args.threshold if args.threshold is not None else s.confidence_threshold
    cases = load_cases(ids=[d for d in args.docs.split(",") if d] or None, split=args.split)
    if args.estimate:
        estimate(cases, model_name, args.assume_output_tokens)
        return 0
    configure_logging()
    results, summary = run(cases, args.mode, model_name, threshold, args.workers)
    json_path, md_path = write_reports(args.mode, model_name, summary, results, args.out,
                                       args.split)
    acc, err = summary["accuracy_overall"], summary["errors"]
    print(f"{summary['documents']} docs, field accuracy {acc['correct']}/{acc['fields']}, "
          f"auto-accepted {summary['routing']['auto_accept']}, "
          f"wrong fields {err['wrong_fields']} (missed {err['missed_in_auto_accepted_docs']}), "
          f"cost ${summary['cost']['total_usd']}")
    print(f"wrote {json_path}\nwrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
