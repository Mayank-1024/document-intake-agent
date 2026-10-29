# Document Intake Agent

An intake pipeline for business documents. Claude reads a PDF or image natively and extracts structured fields from three document types (supplier invoices, W-2 wage statements, insurance loss runs). Every field comes back with a value, a confidence and a citation (page number plus the exact source text). Deterministic code then checks what the model said: it verifies the citations against the document's own text layer, runs arithmetic and date rules, masks SSNs, and routes each document to `auto_accept` or to a human review queue with explicit reasons. An eval harness scores the whole thing against ground truth, including how many real model errors the review routing caught and how well the model's confidence matches its accuracy.

Built with Python, the Anthropic Python SDK (native PDF and image input, structured outputs), pydantic, FastAPI, SQLite, pytest, and a small React + TypeScript (Vite) review page.

**All data is synthetic.** Every company, person, address, policy number, EIN, SSN and amount was invented by `data/generate.py`. SSNs start with `000`, which the SSA never issues. The W-2 layout imitates the real form for testing only and is labeled as a synthetic sample on the page. This project is not affiliated with any company.

## Architecture

```
  client / review UI
        |
        |  POST /documents (file + doc_type)        GET /review-queue
        v                                           POST /documents/{id}/corrections
+---------------+                                   POST /documents/{id}/approve
|    FastAPI    |
|    (api/)     |
+---------------+
        |
        v
+--------------------------------------------------------------------+
| intake/pipeline.py                                                 |
|                                                                    |
|  1. load        documents.py   bytes + text layer (pypdf), no OCR  |
|  2. extract     extract.py --> ExtractionModel                     |
|                   |              AnthropicModel (Claude)           |
|                   |              ScriptedModel  (offline fake)     |
|                   +-- decode JSON, mask PII, pydantic validate,    |
|                       one retry with the validation problems       |
|  3. flatten     fields.py      one record per field path           |
|  4. verify      checks.py      citation found on that page?        |
|                                value inside the cited text?        |
|  5. rules       checks.py      sums, tax rates, dates, formats     |
|  6. route       routing.py     auto_accept | needs_review + reasons|
+--------------------------------------------------------------------+
        |
        v
+--------------------------------------------------------------------+
| SQLite (intake/store.py): documents, review_actions                |
+--------------------------------------------------------------------+
```

Only step 2 calls a model. Steps 3 to 6 are plain code with unit tests.

## What the model decides vs. what code decides

| Decided by the model (Claude) | Decided by code (deterministic) |
|---|---|
| Reading each field off the rendered page | Whether the response has the right shape and ranges (pydantic) |
| Normalizing dates and amounts | Whether the cited text appears on the cited page |
| Its confidence in each value | Whether the value actually appears inside its own citation |
| Which text it cites | Whether the numbers add up and the dates make sense |
| | Whether a required field is empty |
| | Whether an SSN is masked before anything is stored or logged |
| | Whether the document is accepted or sent to a person |

Why this split: reading a skewed scan or a table is perception and language, which is where a model adds value. Whether $2,382.85 plus $166.80 equals the printed $2,567.65 has a right answer, so it belongs in code that can be tested at the boundaries (one cent of tolerance passes, two cents fails). The model can be confidently wrong. The checks never take its word for anything except the reading itself, and even that has to be backed by a citation that code can find.

The API's built-in citations feature cannot be combined with structured outputs (the API documentation lists them as incompatible), so the model writes its own `source_text` per field and `intake/checks.py` verifies it. That is a deliberate tradeoff: a self-reported citation can be invented, which is exactly why it is checked against the document instead of trusted.

## The checks

Each one has unit tests (see Tests).

1. **Schema validation with one retry.** The request uses structured outputs (`output_config.format` with a JSON Schema generated from the pydantic models in `intake/schemas.py`), so the response always has the right shape. Pydantic then enforces what the API schema cannot express: confidence in [0, 1], ISO dates, page numbers that exist, a masked SSN. A failure sends one fresh request with the problems listed (field paths and messages, never the values). A second failure routes the document to review as `extraction_invalid`.
2. **Citation verification.** For each field, the cited text must appear on the cited page of the PDF's text layer (case-insensitive, whitespace removed, so table rows split into separate text runs still match), and the value must appear inside the cited text in one of its common printed forms (`1962.4` matches `$1,962.40`; `2026-09-04` matches `September 4, 2026`). Statuses: `verified`, `not_found`, `wrong_page`, `value_not_in_citation`, `missing_citation`, `absent`, and `unverifiable` for scans, where only the value-in-citation part can run.
3. **Business rules** (`intake/checks.py`), compared in integer cents:
   - invoice: quantity x unit price = amount per line, line items sum to the subtotal, subtotal + tax = total, due date not before invoice date, `Net N` terms match the due date;
   - W-2: box 4 is 6.2% of box 3 and box 6 is 1.45% of box 5 (within $1; the Medicare rule is skipped above $200,000, where the 0.9% surtax applies), box 3 within the published Social Security wage base, withholding below wages, EIN format, plausible tax year;
   - loss run: paid + reserve = incurred per claim, claim columns sum to the printed totals, total paid + total reserve = total incurred, policy period start before end, every date of loss inside the policy period, valuation date not before the policy start, closed claims carry no reserve.
   Each rule names the fields it implicates, so a failed rule flags those fields for the reviewer. A rule with a missing input is `skipped`, not passed.
4. **PII.** `intake/pii.py` masks any full SSN in the decoded response (value, citation, any other string) before validation, storage, logging or a retry prompt. The model is also told to return only `XXX-XX-####`; the code does not rely on it. The SSN citation is verified by matching the last four digits against an SSN pattern on the page. Logs carry ids, routes, reason codes, tokens and latency, never field values, and the log formatter redacts anything shaped like an SSN as a safety net. Reviewer corrections to the SSN field are masked before they are written. The eval refuses to write a report that contains an unmasked SSN.
5. **Routing.** A document is auto-accepted only if every required field has a value, every field's confidence is at or above the threshold (default 0.90), every citation verified, and every rule passed. Anything else goes to the review queue with reasons such as `low_confidence`, `citation_failed`, `missing_required`, `rule_failed`, `no_text_layer`, `extraction_invalid` or `model_error`. A scan has no text layer, so its citations cannot be checked and it always goes to review.

## Dataset

`uv run python -m data.generate` rebuilds everything byte for byte (fixed seed, fixed PDF metadata).

**Core split (30 documents, 10 per type).** Two layouts per type with different labels and date formats. Hard cases:

| Variant | Documents | What it tests | Expected route |
|---|---|---|---|
| `scanned_png`, `scanned_pdf` | 6 | page rendered to an image, rotated up to 2.2 degrees, speckle noise; no text layer | review (`no_text_layer`) |
| `two_page` | 2 | line items or claims continue on page 2, totals on page 2 | auto-accept |
| `missing_field` | 2 | invoice date or employer EIN not printed; the model must return null | review (`missing_required`) |
| `total_mismatch` | 2 | printed total does not equal subtotal + tax, or the claim columns | review (`rule_failed`) |
| `ss_tax_mismatch` | 1 | W-2 box 4 is not 6.2% of box 3 | review (`rule_failed`) |
| `date_out_of_period` | 1 | a claim's date of loss falls after the policy period | review (`rule_failed`) |
| `no_claims` | 1 | loss run with no claims and zero totals | auto-accept |

The ground truth is what is printed. A faithful extractor returns the wrong printed total; catching it is the rules' job.

**Stress split (9 documents).** Added after the first real run scored every core field correctly, which meant no real model error had ever reached the checks. Distractors printed next to the right value: a Ship To company above the Bill To, a balance due under the invoice total, a per-page subtotal, a negative discount line, split indemnity and expense paid columns, a W-2 whose box 3 is capped at the wage base. Plus three badly degraded scans (80 dpi, up to 3.5 degrees of rotation, heavy noise, JPEG quality 30), one of them a two-page loss run with 34 claims.

## Running it

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/), and `pdftoppm` (poppler) only if you regenerate the scans. Node.js for the UI (built with Node 24.8). No API key is needed for anything except real-model runs.

```bash
uv sync                                   # create .venv and install dependencies
uv run pytest                             # 65 tests, all offline
uv run ruff check .                       # lint
uv run python -m evals.run                # offline eval (scripted model with injected faults)
uv run python -m data.generate            # rebuild data/ (already committed)
```

### Real model

Put `ANTHROPIC_API_KEY=...` in a git-ignored `.env` (see `.env.example`) and pass it with `--env-file`:

```bash
uv run --env-file .env python -m evals.run --mode anthropic --estimate     # count tokens, estimate cost
uv run --env-file .env python -m evals.run --mode anthropic                # all 39 documents, claude-haiku-5-5
uv run --env-file .env python -m evals.run --mode anthropic --model claude-sonnet-5-5 --split stress
```

`INTAKE_MODEL` (default `claude-haiku-5-5`), `INTAKE_EFFORT` (default `medium`) and `CONFIDENCE_THRESHOLD` (default `0.90`) are read from the environment. `--estimate` uses the token counting endpoint, which is free.

### API and review UI

```bash
uv run uvicorn api.main:create_app --factory --port 8000     # terminal 1
cd ui && npm install && npm run dev                          # terminal 2, open http://localhost:5173
```

Without `ANTHROPIC_API_KEY` the API uses an offline model that only knows the 39 dataset documents (it replays their ground truth), so the whole flow works with no key; any other upload goes to review with `model_error`. With the key in the environment (`uv run --env-file .env uvicorn ...`) it calls Claude. Processing runs inside the request.

```bash
curl -s -X POST localhost:8000/documents -F doc_type=invoice -F file=@data/docs/inv-06.pdf
curl -s localhost:8000/review-queue
curl -s -X POST localhost:8000/documents/<id>/corrections -H 'content-type: application/json' \
  -d '{"field": "total", "value": 2549.65, "reviewer": "mayank"}'
curl -s -X POST localhost:8000/documents/<id>/approve -H 'content-type: application/json' \
  -d '{"reviewer": "mayank"}'
curl -s localhost:8000/corrections        # corrections with document hash, field path, old and new value
```

The UI lists the queue, shows the document next to its fields (value, confidence, citation and its status, flags), lets a reviewer correct a field (typed by field kind) and approve. `#<document id>` in the URL opens a document directly.

## Evals

`python -m evals.run` processes every document, compares each field to ground truth and writes `evals/reports/<mode>-<model>-<split>-<timestamp>.json` and `.md`. Fields are compared exactly after light normalization (case, commas and periods in text; amounts to the cent). Line items and claims are aligned by description or claim number before comparing, so one dropped row counts as one row of errors instead of shifting every later row.

The report covers field accuracy by split, document type and variant; accuracy of fields in auto-accepted vs review-routed documents; accuracy of flagged vs unflagged fields; every wrong field with its confidence, citation status and flags; errors caught at document level (the document went to review) and at field level (the wrong field itself was flagged) vs missed (auto-accepted); false alarms (clean documents sent to review with nothing wrong); a confidence calibration table; a threshold sweep over the same run; cost, tokens and latency per document.

Two modes:

- `--mode offline` (default): a scripted model built from ground truth with nine hand-injected faults (`evals/offline_faults.py`): a confident wrong total, an invented citation, a dropped claim row, swapped digits, an invalid first answer that the retry fixes, two invalid answers, an unmasked SSN, a correct value with low confidence, and one fault built to slip past every check (the vendor's name returned as the customer, with a real citation). **This mode tests the checks, routing and scoring. Its numbers say nothing about model quality.** `tests/test_evals.py` pins its accounting: the planted miss is reported as the only missed error, the three flaggable wrong values are flagged, and the dropped row counts as 6 wrong fields. Committed example: `evals/reports/example-offline-scripted-all.md`.
- `--mode anthropic`: the real Claude API.

## Real-model results

All runs were on 2026-10-29 over all 39 documents (1,648 scored fields), threshold 0.90, effort `medium`, with the prompt and schema as committed. Full reports are in `evals/reports/example-anthropic-*.md` (and `.json`).

| | Haiku 5.5, run 1 | Haiku 5.5, run 2 | Sonnet 5.5 |
|---|---|---|---|
| Field accuracy, all | 99.2% (1,634/1,648) | 99.0% (1,631/1,648) | 99.5% (1,639/1,648) |
| Core split (30 docs) | 100% (1,124/1,124) | 100% (1,124/1,124) | 100% (1,124/1,124) |
| Stress split (9 docs) | 97.3% (510/524) | 96.8% (507/524) | 98.3% (515/524) |
| Auto-accepted documents | 23 | 22 | 24 |
| Hard cases sent to review for the expected reason | 15 of 15 | 15 of 15 | 15 of 15 |
| Clean documents sent to review (false alarms) | 1 | 2 | 0 |
| Wrong fields | 14 | 17 | 9 |
| Wrong fields in auto-accepted documents | 0 | 0 | 0 |
| Wrong fields individually flagged | 14 of 14 | 17 of 17 | 9 of 9 |
| Accuracy of flagged fields | 94.3% (232/246) | 92.9% (221/238) | 96.3% (233/242) |
| Schema retries / extraction failures | 0 / 0 | 0 / 0 | 0 / 0 |
| Total cost | $0.0548 | $0.0547 | $0.8501 |
| Mean cost per document | $0.0014 | $0.0014 | $0.0218 |
| Latency per document, p50 / p95 | 6.1 s / 12.9 s | 5.9 s / 12.6 s | 6.1 s / 13.0 s |

An earlier Haiku run the same day over only the 30 core documents, before the stress split existed and before some schema descriptions were clarified, also got 1,124 of 1,124 core fields right for $0.0398; its report was not kept. Total API spend for this project, including three single-document probes and one API smoke test, was about $1.00.

What these runs showed, plainly:

- **The core set is too easy for these models.** Both models read every core field correctly in every run, including the rotated scans, the two-page documents and the missing fields (they returned null rather than inventing a value). On the core set, review routing was driven entirely by the planted hard cases, and every one of them was routed for the expected reason.
- **Every real error happened on a degraded scan, and scans always go to review.** All wrong fields in all three runs were on `inv-s3` (a degraded invoice JPEG) and `lr-s2` (a degraded two-page loss run). Because a scan has no text layer, it goes to review regardless of confidence. So "0 wrong fields auto-accepted" is partly a consequence of that policy, not proof that the confidence threshold or the rules would stop a real error on a text PDF: in these runs no real error occurred on a text PDF at all. The offline mode is what exercises that path, with planted faults.
- **The rules caught misreads on scans.** In all three runs the model read `lr-s2`'s printed total paid of 849,692.92 as 649,692.92 (Haiku gave it confidence 0.60, Sonnet 0.85). The claim-column sum rule failed and flagged it. On `inv-s3`, Haiku run 1 misread the first line consistently (unit price 23.95 for 23.85 and amount 239.50 for 238.50), so the per-line rule passed but the line items no longer summed to the printed subtotal and that rule flagged the amount. Haiku run 2 misread only the unit price, and the quantity x unit price rule flagged it.
- **Value-in-citation works even without a text layer.** On the degraded W-2 (`w2-s2`, Haiku run 1) the model's citation read "Northmere Software Labe LLC" while its value said "Labs". The check flagged the mismatch. The value happened to be right, so this was a false flag, but it shows the check catches the model contradicting itself.
- **Field-level flags were not precise on degraded scans.** On `lr-s2` (213 fields), Haiku run 1 flagged 207 fields to cover 12 wrong ones, because the model lowered its confidence for whole rows and the sum rules implicate every value in a column. A reviewer is pointed at the right document, not at the right cell.
- **Confidence was directionally useful but coarse.** Every field Haiku gave 0.90 or more was right in both runs (1,420 fields in run 1). Below 0.90 accuracy dropped (run 1: 92.1% in the 0.70 to 0.80 bin, 97.0% in 0.80 to 0.90). Sonnet never went below 0.80. Confidence is self-reported and coarse: each run used only 12 to 14 distinct values, with most fields between 0.93 and 0.98, so the calibration table has few populated bins.
- **False alarms came from low confidence, not failed checks.** Haiku run 1 sent `inv-s2` (the deposit and balance-due invoice) to review because it gave the correct subtotal 0.88. Haiku run 2 sent two clean W-2s to review because it gave the correctly masked SSN 0.85. All three runs got every distractor document right (Ship To, balance due, page subtotal, discount line, split paid columns, capped box 3).
- **Sonnet vs Haiku.** Sonnet made 9 errors to Haiku's 14 and 17, had no false alarms, and cost about 15.5 times as much ($0.8501 vs $0.0548 for the same 39 documents), with similar latency. On this data, Haiku plus the deterministic checks sent every error to a person at about $0.0014 per document.

Two runs per model on 39 synthetic documents is a small sample. These are findings to act on, not a benchmark.

## Tests

`uv run pytest` runs 65 tests, all offline (no API key, no network):

| File | Tests | Covers |
|---|---|---|
| `test_citations.py` | 14 | every ground-truth citation verifies on its own document, print-format renderings, each citation status, wrong page, scans, row citations |
| `test_extract.py` | 13 | schema retry (problems sent, values not echoed), two invalid answers, page range, max_tokens cutoff, model errors, strict JSON Schema, `AnthropicModel` request shape for PDF and image, error mapping, refusal |
| `test_rules.py` | 11 | clean documents pass every rule, planted inconsistencies fail the right rule, one-cent tolerance, terms and dates, skipped rules, W-2 rate boundaries and wage base, loss run claim math and period |
| `test_store_api.py` | 8 | upload, auto-accept, correct then approve, corrections export, validation errors, SSN correction stored masked, file serving, bad uploads, unknown document offline |
| `test_pii.py` | 7 | masking formats, free-text redaction without false positives, full SSN from the model masked before storage and still verified, log redaction, no full SSN in any truth file |
| `test_routing.py` | 6 | each reason and its field flag, inclusive threshold, scans always reviewed, every planted hard case routed for the expected reason, a hallucinated value for a missing field caught |
| `test_evals.py` | 6 | offline accounting for every injected fault, sweep and calibration consistency, value comparison, row alignment, invented rows, CLI report without PII |

The UI is type-checked and built with `npm run build`; it has no automated tests.

## Layout

```
intake/      schemas, document loading, model seam + Claude and scripted models, prompts,
             extraction with retry, PII, citation checks and rules, routing, pipeline, SQLite store
api/         FastAPI app
evals/       dataset loader, offline faults, scoring, Markdown report, CLI, reports/
data/        generate.py, docs/ (PDF, PNG, JPEG), truth/ (one JSON per document), manifest.json
ui/          React + TypeScript review page (Vite)
tests/       pytest suite
settings.py  environment configuration and per-model prices
WALKTHROUGH.md  file-by-file guide and interview questions
```

## Limitations and what I would do next

- **The dataset is synthetic and small.** Clean generated PDFs are easier than real vendor invoices, carrier loss runs or phone photos. The next step is a labeled set of real (redacted) documents, with ground truth built from reviewer corrections (`GET /corrections` already exports them in the eval's field-path format, but they are not yet wired into `evals/`).
- **Scans always go to review.** There is no independent text layer to check a scan's citations against. A second, independent reading (a different model, or OCR where available) compared field by field would let clean scans auto-accept and would localize disagreements to cells.
- **Flags are coarse on bad scans.** Sum rules implicate a whole column. Per-row rules localize better; a cross-check of each row against the page image would localize further.
- **Confidence is self-reported.** It was informative here but clustered. With more labeled data I would calibrate it (or replace it with agreement between two readings) and pick the threshold from the sweep on a held-out set, per document type.
- **Document type is supplied by the caller.** A classification step would be needed for a mixed inbox.
- **Processing is synchronous** inside the HTTP request. A queue and worker (as in my commerce-support-agent project) would be the production shape.
- **Uploaded originals are stored as files** in `uploads/` (git-ignored) and still contain the full SSN printed on the page. Production would need encrypted storage and retention rules for originals.
- **Prompt caching** is not used. Most of each request's tokens are the document itself, which changes every time; I have not measured whether caching the shared system prompt and schema would help.

## How this was built

Built by Mayank Bhadrasen with Claude Code.

## License

MIT, see [LICENSE](LICENSE).
