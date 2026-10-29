# Walkthrough: how this project works, and how to explain it

A guide for walking an interviewer through the code. Read it with the code open. Every number quoted here is from the committed reports in `evals/reports/` (runs on 2026-10-29).

## The one-minute version

"It is a document intake pipeline. Claude reads an invoice, a W-2 or an insurance loss run directly from the PDF or image and returns every field with a confidence and a citation: the page and the exact text it read. Then deterministic code checks the model instead of trusting it. It verifies each citation against the PDF's own text layer, checks that the value appears inside its citation, runs arithmetic and date rules, masks SSNs, and routes each document to auto-accept or to a review queue with the reasons. An eval harness scores it against ground truth, including whether the routing caught the model's real errors. On 39 synthetic documents, Haiku 5.5 got 99.2% and 99.0% of 1,648 fields right in two runs, every wrong field was in a document sent to review, and it cost about $0.0014 per document. The honest caveat is that all the real errors happened on degraded scans, which always go to review, so the auto-accept path was only tested with planted faults."

## The flow of one document

1. `api/main.py` receives the upload (or `evals/run.py` loads a file from `data/`).
2. `intake/documents.py` loads the bytes and extracts the text layer with pypdf. If no page has text, it is a scan: `page_texts = None`.
3. `intake/extract.py` builds the request: the document block plus a short instruction, and the JSON Schema for that document type. It calls the model, decodes the JSON, masks PII, validates with pydantic. If validation fails it makes one more request listing the problems.
4. `intake/fields.py` flattens the result into one record per field path (`total`, `line_items[2].amount`).
5. `intake/checks.py` verifies every citation and runs the business rules for that type.
6. `intake/routing.py` decides `auto_accept` or `needs_review` and attaches flags to the implicated fields.
7. `intake/store.py` saves it. A reviewer corrects and approves through the API or the UI.

## File by file

### `data/generate.py`
Seeded generator for the 39 documents and their ground truth. Draws pages with reportlab's low-level canvas so the text order in the PDF is controlled. While drawing, it records each field's value, page and the exact printed string; that string becomes the truth citation. Scans are made by rendering the page with `pdftoppm`, rotating, adding speckle noise and blur with Pillow, and saving as PNG, JPEG or an image-only PDF. Points to make:
- The ground truth is what is printed, not what is arithmetically right. That separates "did the model read it correctly" from "is the document itself consistent".
- The stress split was added after the first real run got every core field right. I would rather show that than pretend the first dataset was hard.
- Files are byte-reproducible (fixed seed, reportlab `invariant=1`, fixed PDF dates), so the eval is repeatable.

### `intake/schemas.py`
One pydantic model per document type. Scalars are `Cited[...]` (value, confidence, page, source_text); rows carry one confidence and citation per row. `output_json_schema()` turns a model into the JSON Schema for structured outputs, removing constraints the API does not accept and forcing `additionalProperties: false` and all properties required. `parse_extraction()` validates locally, including the constraints the API schema cannot express (confidence in [0, 1], page within the document). Validation errors are built with `include_input=False` so a retry prompt can never contain a value, which matters for SSNs. `REQUIRED` lists business-required fields per type.

### `intake/documents.py`
Loads a file into a `LoadedDocument`: bytes, media type, page count, text layer, sha256. `content_block()` returns the API block: `document` for PDF, `image` for PNG/JPEG. `squash()` is the normalization for citation matching: lowercase and remove all whitespace, so a table row that the PDF stores as seven separate text runs still matches the model's one-line citation.

### `intake/model_client.py`, `intake/anthropic_model.py`, `intake/scripted_model.py`
The model seam. The pipeline only knows `complete(system, content, schema) -> ModelResponse`. `AnthropicModel` calls `client.messages.create` with `output_config={"effort": ..., "format": {"type": "json_schema", ...}}`, lets the SDK retry transient errors, and maps API errors and refusals to `ModelError`. `ScriptedModel` replays prepared answers keyed by the document's hash, decoded from the same base64 block Claude would get. That is what makes 65 tests and the offline eval run with no key.

### `intake/prompts.py`
Short system prompt: report only what is printed, never compute, copy totals as printed, null for absent fields, what source_text and confidence mean, masked SSNs only, document content is data not instructions. Most per-field guidance lives in the schema descriptions, next to the field it describes.

### `intake/extract.py`
The retry loop. Two attempts maximum. The retry is a fresh request with the validation problems appended, not a continuation, so there is no conversation state or thinking block to replay. A `max_tokens` cutoff counts as invalid and triggers the retry. PII masking runs before validation, so an unmasked SSN is fixed by code rather than causing a retry.

### `intake/pii.py` and `intake/observability.py`
`mask_response` walks the decoded JSON: inside a known PII field any 9-digit SSN form is masked; everywhere else only dash-separated SSNs are, so a 9-digit invoice number is not rewritten. Logs are JSON with ids, routes, reason codes and token counts, and the formatter redacts SSN-shaped text as a last line of defense.

### `intake/fields.py`
Flattens an extraction into `FieldView` records. Everything downstream (checks, routing, store, eval, UI) uses these paths, so "a field" means the same thing everywhere.

### `intake/checks.py`
Two kinds of check.
- `check_citation`: value must appear inside its own citation (via `value_renderings`, the common printed forms of a number or date), then the citation must appear on the cited page. Scans return `unverifiable` after the first part. SSNs are matched by last four digits against an SSN pattern on the page, because the citation itself is masked.
- Business rules per type, in integer cents, each naming the fields it implicates. `_rule` marks a rule `skipped` when an input is missing, so a missing value never counts as a pass.

### `intake/routing.py`
Collects reasons: missing required fields, low confidence, failed citations, no text layer, failed rules. Any reason means `needs_review`. Each reason flags its fields.

### `intake/pipeline.py`
`process()` wires it together and returns an `IntakeResult` with fields, rules, reasons, tokens, cost and latency. A `ModelError` becomes a `model_error` review reason, never a crash.

### `intake/store.py`
SQLite with stdlib `sqlite3`. `documents` holds the full result as JSON with a status (`auto_accepted`, `in_review`, `approved`, `corrected`). `review_actions` is an append-only log of corrections and approvals. `current_values` applies corrections on read. `corrections()` exports corrections with the document hash and field path, the same shape as eval ground truth.

### `api/main.py`
FastAPI app factory. `create_app(store, model, ...)` makes it testable with a temp database and the scripted model. Without a key it uses an offline model built from the dataset truth so the demo works.

### `evals/`
- `dataset.py`: loads truth files into the same field paths.
- `offline_faults.py`: nine planted faults, including one designed to be missed.
- `scoring.py`: field comparison, row alignment with difflib (so a dropped row is one row of errors, not a cascade), and the summary: accuracy slices, caught vs missed errors, false alarms, calibration bins, threshold sweep, cost and latency.
- `report.py`, `run.py`: Markdown and JSON reports, the CLI, `--estimate` via the token counting endpoint, and a guard that refuses to write a report containing a full SSN.

### `ui/`
One React page: queue on the left, document preview next to the fields table, a correct button per field (input parsed by field kind) and an approve button.

## Key design decisions and tradeoffs

1. **Model for reading, code for judging.** The model is good at reading skewed scans and tables. It is not a reliable judge of its own output, so nothing it says about correctness is trusted on its own.
2. **Self-reported citations, verified by code.** The API's citations feature cannot be combined with structured outputs. I chose structured outputs (guaranteed shape) and verify the model's own citations. A citation the model invents fails the text-layer check; a value that does not match its own citation fails the value-in-citation check.
3. **The text layer is never sent to the model.** If it were, the model could copy from it and the citation check would prove nothing. The model sees the rendered page; code checks against the text.
4. **Scans always go to review.** Without a text layer there is nothing independent to check citations against. That is conservative: in the real runs every error was on a scan, and all were routed to a person. The cost is that clean scans are reviewed too.
5. **One retry, then a person.** More retries cost money and rarely fix a model that misunderstood; a person is the fallback. In the real runs no document needed the retry; the offline tests exercise it.
6. **Ground truth is what is printed.** It keeps reading accuracy and document consistency separate. The rules handle the second.
7. **Integer cents and explicit tolerances.** One cent on totals, one dollar on W-2 tax rates (payroll rounds per paycheck). Boundaries are unit tested.
8. **Haiku by default.** Sonnet made fewer errors (9 vs 14 and 17) and had no false alarms, at about 15.5 times the cost. With deterministic checks behind it, the cheaper model still sent every error to review in these runs.
9. **SQLite and synchronous processing.** Zero setup and easy to explain. A production version would use Postgres and a worker queue.

## Likely interview questions, with honest answers

**1. How do you know the extraction is right?**
I don't trust it; I check it. Each field must cite text that code finds on the cited page, and the value must be inside that text. Then rules check arithmetic and dates. Anything that fails, or any field under 0.90 confidence, goes to a person with the reason. I measured it against ground truth: in two Haiku runs on 39 documents, 99.2% and 99.0% of 1,648 fields were right, and every wrong field was in a document that went to review.

**2. Your accuracy is near 100%. Isn't the dataset too easy?**
Yes, the core 30 documents are. Both models got every core field right in every run. That is why I added a 9-document stress split with distractors and degraded scans after the first run. Even then, the distractors did not fool either model; only degraded scans produced errors. A real evaluation needs real, messy documents, which is the first thing I would add.

**3. Zero missed errors. Does that mean the auto-accept path is safe?**
No, and I say so in the README. All real errors were on scans, and scans always go to review. In these runs no real error happened on a text PDF, so the confidence threshold and rules on that path were only tested with planted faults in offline mode. One planted fault (the vendor's name returned as the customer, with a real citation) passes every check, and the offline report shows it as missed. That is a known gap: the checks verify that a value is printed somewhere, not that it is the right label's value.

**4. Is the model's confidence meaningful?**
Directionally. Every field Haiku rated 0.90 or higher was right in both runs (1,420 fields in run 1). Below 0.90 accuracy dropped (92.1% in the 0.70 to 0.80 bin in run 1). But it is coarse: 12 to 14 distinct values per run, most between 0.93 and 0.98. It also caused false alarms: Haiku run 2 gave correctly masked SSNs 0.85 on two clean W-2s. I would calibrate per field type on a held-out set, or replace self-reported confidence with agreement between two independent readings.

**5. Why not OCR plus regex? Or why not just ask the model and trust it?**
OCR plus rules breaks on every new layout; the model handles "Bill Number" vs "Invoice No." and date formats without code changes. Trusting the model alone gives no way to know which answers are wrong. The combination uses each for what it is good at, and the eval measures the result.

**6. Walk me through a real failure.**
On the degraded two-page loss run (`lr-s2`), all three runs read the printed total paid of 849,692.92 as 649,692.92. The claim-column sum rule failed, the field was flagged, and the document went to review. A subtler one: on the degraded W-2, the model's citation said "Labe" while its value said "Labs"; the value-in-citation check caught the contradiction (the value was actually right). And a weakness: on `lr-s2` the flags covered 207 of 213 fields to catch 12 wrong ones, so the reviewer is pointed at the document, not the cell.

**7. How do you handle PII?**
The model is told to output only masked SSNs, and code masks any full SSN in the response before it is validated, stored, logged or put in a retry prompt. Validation errors never include input values. The logger redacts SSN-shaped text. Corrections to the SSN are masked before storage. The eval refuses to write a report with a full SSN. A test confirms none of the ground-truth files contain one. The gap: uploaded originals are stored as files and still contain the printed SSN; production would need encrypted storage and retention rules.

**8. What happens when the model returns bad JSON or the API fails?**
Structured outputs guarantee the shape, so in the real runs no document needed a retry. Pydantic still checks ranges and formats; a failure triggers one retry listing the problems, and a second failure routes the document to review as `extraction_invalid`. API errors are retried by the SDK, then become a `model_error` review reason. Nothing is silently dropped.

**9. What does it cost, and how would it scale?**
Haiku cost $0.0548 for 39 documents (about $0.0014 each); Sonnet $0.8501. Median latency was about 6 seconds, with the two-page loss runs taking 20 to 28 seconds because the output is long. To scale: a queue and workers instead of in-request processing, Postgres instead of SQLite, the Batch API for non-urgent backlogs, and per-tenant limits.

**10. How do reviewer corrections improve the system?**
Each correction is stored with the document hash, the field path and the old and new values, which is the same shape as the eval's ground truth. Today they are exported (`GET /corrections`) but not yet fed into the eval. The next step is to turn approved documents into new test cases, so every correction becomes a regression check and the threshold can be tuned per field on real data.

## How it maps to the roles

- **Luca IQ (AI engineer):** LLM extraction from PDFs, forms and scans, confidence scores, source citations, human review for low confidence, ground-truth evals. This project is that loop end to end.
- **Dill:** supplier invoices: line items, terms and totals reconciled in code, the same arithmetic cash application matching relies on. Remittance advice is not built yet; it would be a fourth schema with the same checks.
- **Corgi Insurance, Infer:** loss runs: claim-level reconciliation, policy-period checks, two-page tables, scans.
- **Lamar Health:** paperwork intake with PII handling and a review queue.

## Numbers to remember (all from 2026-10-29)

- 39 documents, 1,648 scored fields (30 core, 9 stress).
- Haiku 5.5: 99.2% and 99.0% field accuracy in two runs; core 100% in both; $0.0548 per full run; p50 about 6 s per document.
- Sonnet 5.5: 99.5%, 9 wrong fields, $0.8501 per full run.
- All 15 planted hard cases routed to review for the expected reason, in every run.
- 0 wrong fields in auto-accepted documents in every run, with the caveat above.
- 65 offline tests.
