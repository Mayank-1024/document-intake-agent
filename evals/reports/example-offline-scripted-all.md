# Eval report: offline / scripted / split all

Generated 20261029T100528Z (UTC). Confidence threshold 0.9.

> Offline mode: answers come from a scripted model built from ground truth with hand-injected faults (evals/offline_faults.py). This verifies the checks, routing and scoring. It is NOT a measure of model quality.

Injected faults:

- `inv-03`: confident wrong total, true citation (value_not_in_citation + arithmetic rule)
- `inv-04`: misspelled vendor with an invented citation (not_found)
- `inv-10`: customer_name set to the vendor name, citing the vendor line (built to be missed)
- `w2-02`: first answer invalid (confidence 1.4, non-ISO date), second answer valid (retry)
- `w2-03`: model returns the full SSN; code masks it before storage
- `w2-04`: correct wages with confidence 0.60 (false alarm, review)
- `lr-01`: claims[0].paid has swapped digits, row citation is the true row (citation + rule)
- `lr-02`: one claim row dropped (sum rules fail; missing row fields count as errors)
- `lr-10`: both answers invalid (extraction_invalid, review)

## Summary

| Metric | Value |
|---|---|
| Documents | 39 |
| Fields scored | 1648 |
| Field accuracy, all | 95.9% (1581/1648) |
| Auto-accepted documents | 18 |
| Documents sent to review | 21 |
| Hard cases sent to review | 15 of 15 |
| Hard cases flagged for the expected reason | 15 |
| Clean documents sent to review | 6 of 24 |
| ...of which had no wrong field (false alarms) | 1 |
| Wrong fields | 67 |
| Wrong fields in reviewed documents (caught, document level) | 66 |
| ...wrong values the model produced / fields it never produced | 4 / 63 |
| Wrong produced values individually flagged (caught, field level) | 3 of 4 |
| Wrong fields in auto-accepted documents (missed) | 1 |
| Documents that needed the schema retry | 2 |
| Extraction failures (invalid twice, or API error) | 1 |
| PII strings masked by code | 2 |
| Total cost (USD) |  |
| Mean cost per document (USD) |  |
| Input / output tokens | 0 / 0 |
| Latency per document, mean / p50 / p95 / max (ms) | 3.8 / 2.2 / 8.1 / 18.6 |

## Field accuracy

| Slice | Accuracy |
|---|---|
| split: core | 94.0% (1057/1124) |
| split: stress | 100.0% (524/524) |
| type: invoice | 99.5% (643/646) |
| type: loss_run | 92.6% (806/870) |
| type: w2 | 100.0% (132/132) |
| variant: date_out_of_period | 100.0% (39/39) |
| variant: degraded_scan_jpeg | 100.0% (33/33) |
| variant: degraded_scan_two_page | 100.0% (213/213) |
| variant: deposit_balance_due | 100.0% (38/38) |
| variant: discount_line | 100.0% (42/42) |
| variant: high_earner | 100.0% (11/11) |
| variant: missing_field | 100.0% (49/49) |
| variant: no_claims | 100.0% (9/9) |
| variant: page_subtotal | 100.0% (114/114) |
| variant: scanned_pdf | 100.0% (82/82) |
| variant: scanned_png | 100.0% (82/82) |
| variant: ship_to_distractor | 100.0% (22/22) |
| variant: split_paid_columns | 100.0% (51/51) |
| variant: ss_tax_mismatch | 100.0% (11/11) |
| variant: standard | 84.6% (369/436) |
| variant: total_mismatch | 100.0% (89/89) |
| variant: two_page | 100.0% (327/327) |
| fields in auto-accepted docs | 99.9% (809/810) |
| fields in review docs | 92.1% (772/838) |
| flagged fields | 93.9% (46/49) |
| unflagged fields | 96.0% (1535/1599) |

## Wrong fields

| Doc | Field | Truth | Predicted | Conf. | Citation | Flags | Route |
|---|---|---|---|---|---|---|---|
| inv-03 | total | 3231.99 | 3331.99 | 0.97 | value_not_in_citation | citation:value_not_in_citation, rule:subtotal_plus_tax_equals_total | needs_review |
| inv-04 | vendor_name | Marrow Creek Electrical Supply | Marorw Creek Electrical Supply | 0.97 | not_found | citation:not_found | needs_review |
| inv-10 | customer_name | Sundial Print Works | Ostrander Fasteners Inc. | 0.95 | verified |  | auto_accept |
| lr-01 | claims[0].paid | 35540.38 | 53540.38 | 0.97 | value_not_in_citation | citation:value_not_in_citation, rule:claims[0]_paid_plus_reserve_equals_incurred, rule:claims_paid_sum_to_total_paid | needs_review |

Fields never produced (dropped rows or failed extraction):

- lr-02 (needs_review): 6 fields, e.g. claims[1].claim_number, claims[1].date_of_loss, claims[1].status, claims[1].paid
- lr-10 (needs_review): 57 fields, e.g. carrier_name, insured_name, policy_number, policy_period_start

## Confidence calibration

Each field's self-reported confidence against whether it was right. Row fields share their row's confidence, so bins are not independent samples.

| Confidence bin | Fields | Mean confidence | Observed accuracy |
|---|---|---|---|
| [0.00, 0.50) | 0 |  |  |
| [0.50, 0.70) | 1 | 0.6 | 1.0 |
| [0.70, 0.80) | 0 |  |  |
| [0.80, 0.90) | 0 |  |  |
| [0.90, 0.95) | 0 |  |  |
| [0.95, 0.98) | 1584 | 0.97 | 0.997 |
| [0.98, 1.00] | 0 |  |  |

## Threshold sweep (same run, other checks unchanged)

| Threshold | Auto-accepted docs | Auto-accepted fields | Wrong fields auto-accepted |
|---|---|---|---|
| 0.5 | 19 | 821 | 1 |
| 0.7 | 18 | 810 | 1 |
| 0.8 | 18 | 810 | 1 |
| 0.85 | 18 | 810 | 1 |
| 0.9 | 18 | 810 | 1 |
| 0.95 | 18 | 810 | 1 |
| 0.97 | 17 | 784 | 0 |

## Documents

| Doc | Variant | Expected | Route | Reasons | Wrong/fields | Tries | Tokens in/out | Cost | ms |
|---|---|---|---|---|---|---|---|---|---|
| inv-01 | standard | accept | auto_accept |  | 0/26 | 1 | 0/0 |  | 8.1 |
| inv-02 | standard | accept | auto_accept |  | 0/38 | 1 | 0/0 |  | 7.9 |
| inv-03 | standard | accept | needs_review | citation_failed, rule_failed | 1/34 | 1 | 0/0 |  | 5.8 |
| inv-04 | standard | accept | needs_review | citation_failed | 1/30 | 1 | 0/0 |  | 3.7 |
| inv-05 | two_page | accept | auto_accept |  | 0/114 | 1 | 0/0 |  | 6.2 |
| inv-06 | total_mismatch | review | needs_review | rule_failed | 0/38 | 1 | 0/0 |  | 2.2 |
| inv-07 | missing_field | review | needs_review | missing_required | 0/38 | 1 | 0/0 |  | 2.2 |
| inv-08 | scanned_png | review | needs_review | no_text_layer | 0/26 | 1 | 0/0 |  | 4.9 |
| inv-09 | scanned_pdf | review | needs_review | no_text_layer | 0/38 | 1 | 0/0 |  | 5.7 |
| inv-10 | standard | accept | auto_accept |  | 1/26 | 1 | 0/0 |  | 1.9 |
| inv-s1 | ship_to_distractor | accept | auto_accept |  | 0/22 | 1 | 0/0 |  | 1.6 |
| inv-s2 | deposit_balance_due | accept | auto_accept |  | 0/38 | 1 | 0/0 |  | 2.0 |
| inv-s3 | degraded_scan_jpeg | review | needs_review | no_text_layer | 0/22 | 1 | 0/0 |  | 1.4 |
| inv-s4 | discount_line | accept | auto_accept |  | 0/42 | 1 | 0/0 |  | 2.1 |
| inv-s5 | page_subtotal | accept | auto_accept |  | 0/114 | 1 | 0/0 |  | 4.2 |
| lr-01 | standard | accept | needs_review | citation_failed, rule_failed | 1/51 | 1 | 0/0 |  | 2.5 |
| lr-02 | standard | accept | needs_review | rule_failed | 6/57 | 1 | 0/0 |  | 2.7 |
| lr-03 | standard | accept | auto_accept |  | 0/51 | 1 | 0/0 |  | 2.5 |
| lr-04 | two_page | accept | auto_accept |  | 0/213 | 1 | 0/0 |  | 18.6 |
| lr-05 | total_mismatch | review | needs_review | rule_failed | 0/51 | 1 | 0/0 |  | 2.7 |
| lr-06 | date_out_of_period | review | needs_review | rule_failed | 0/39 | 1 | 0/0 |  | 2.1 |
| lr-07 | no_claims | accept | auto_accept |  | 0/9 | 1 | 0/0 |  | 1.4 |
| lr-08 | scanned_png | review | needs_review | no_text_layer | 0/45 | 1 | 0/0 |  | 7.9 |
| lr-09 | scanned_pdf | review | needs_review | no_text_layer | 0/33 | 1 | 0/0 |  | 4.2 |
| lr-10 | standard | accept | needs_review | extraction_invalid | 57/57 | 2 | 0/0 |  | 2.1 |
| lr-s1 | split_paid_columns | accept | auto_accept |  | 0/51 | 1 | 0/0 |  | 2.7 |
| lr-s2 | degraded_scan_two_page | review | needs_review | no_text_layer | 0/213 | 1 | 0/0 |  | 13.4 |
| w2-01 | standard | accept | auto_accept |  | 0/11 | 1 | 0/0 |  | 1.4 |
| w2-02 | standard | accept | auto_accept |  | 0/11 | 2 | 0/0 |  | 1.9 |
| w2-03 | standard | accept | auto_accept |  | 0/11 | 1 | 0/0 |  | 1.3 |
| w2-04 | standard | accept | needs_review | low_confidence | 0/11 | 1 | 0/0 |  | 1.2 |
| w2-05 | missing_field | review | needs_review | missing_required | 0/11 | 1 | 0/0 |  | 1.2 |
| w2-06 | ss_tax_mismatch | review | needs_review | rule_failed | 0/11 | 1 | 0/0 |  | 1.3 |
| w2-07 | scanned_png | review | needs_review | no_text_layer | 0/11 | 1 | 0/0 |  | 4.8 |
| w2-08 | scanned_pdf | review | needs_review | no_text_layer | 0/11 | 1 | 0/0 |  | 6.4 |
| w2-09 | standard | accept | auto_accept |  | 0/11 | 1 | 0/0 |  | 1.2 |
| w2-10 | standard | accept | auto_accept |  | 0/11 | 1 | 0/0 |  | 1.2 |
| w2-s1 | high_earner | accept | auto_accept |  | 0/11 | 1 | 0/0 |  | 1.2 |
| w2-s2 | degraded_scan_jpeg | review | needs_review | no_text_layer | 0/11 | 1 | 0/0 |  | 1.2 |

## Review reasons per document

- `inv-03`: total citation value_not_in_citation; 3020.55 + 211.44 = 3231.99, total is 3331.99
- `inv-04`: vendor_name citation not_found
- `inv-06`: 2382.85 + 166.80 = 2549.65, total is 2567.65
- `inv-07`: required field invoice_date is empty
- `inv-08`: scanned document: citations cannot be checked against text
- `inv-09`: scanned document: citations cannot be checked against text
- `inv-s3`: scanned document: citations cannot be checked against text
- `lr-01`: claims[0].paid citation value_not_in_citation; 53540.38 + 0.00 != 35540.38; claim paid sums to 225,279.99, printed total is 207,279.99
- `lr-02`: claim paid sums to 164,426.09, printed total is 199,559.67; claim incurred sums to 268,271.98, printed total is 303,405.56
- `lr-05`: claim incurred sums to 306,470.53, printed total is 311,470.53; 224,777.67 + 81,692.86 != 311,470.53
- `lr-06`: claims [1] have a date of loss outside 2024-01-01..2025-01-01
- `lr-08`: scanned document: citations cannot be checked against text
- `lr-09`: scanned document: citations cannot be checked against text
- `lr-10`: response invalid after 2 attempts
- `lr-s2`: scanned document: citations cannot be checked against text
- `w2-04`: wages confidence 0.60 < 0.90
- `w2-05`: required field employer_ein is empty
- `w2-06`: box 4 is 4694.56; 6.2% of box 3 is 4294.56
- `w2-07`: scanned document: citations cannot be checked against text
- `w2-08`: scanned document: citations cannot be checked against text
- `w2-s2`: scanned document: citations cannot be checked against text
