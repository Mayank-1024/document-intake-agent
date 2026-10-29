# Eval report: anthropic / claude-haiku-5-5 / split all

Generated 20261029T100154Z (UTC). Confidence threshold 0.9.

> Anthropic mode: answers come from the real Claude API.

## Summary

| Metric | Value |
|---|---|
| Documents | 39 |
| Fields scored | 1648 |
| Field accuracy, all | 99.2% (1634/1648) |
| Auto-accepted documents | 23 |
| Documents sent to review | 16 |
| Hard cases sent to review | 15 of 15 |
| Hard cases flagged for the expected reason | 15 |
| Clean documents sent to review | 1 of 24 |
| ...of which had no wrong field (false alarms) | 1 |
| Wrong fields | 14 |
| Wrong fields in reviewed documents (caught, document level) | 14 |
| ...wrong values the model produced / fields it never produced | 14 / 0 |
| Wrong produced values individually flagged (caught, field level) | 14 of 14 |
| Wrong fields in auto-accepted documents (missed) | 0 |
| Documents that needed the schema retry | 0 |
| Extraction failures (invalid twice, or API error) | 0 |
| PII strings masked by code | 0 |
| Total cost (USD) | 0.0548 |
| Mean cost per document (USD) | 0.0014 |
| Input / output tokens | 186,305 / 72,313 |
| Latency per document, mean / p50 / p95 / max (ms) | 6969.3 / 6064.7 / 12935.5 / 27702.2 |

## Field accuracy

| Slice | Accuracy |
|---|---|
| split: core | 100.0% (1124/1124) |
| split: stress | 97.3% (510/524) |
| type: invoice | 99.7% (644/646) |
| type: loss_run | 98.6% (858/870) |
| type: w2 | 100.0% (132/132) |
| variant: date_out_of_period | 100.0% (39/39) |
| variant: degraded_scan_jpeg | 93.9% (31/33) |
| variant: degraded_scan_two_page | 94.4% (201/213) |
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
| variant: standard | 100.0% (436/436) |
| variant: total_mismatch | 100.0% (89/89) |
| variant: two_page | 100.0% (327/327) |
| fields in auto-accepted docs | 100.0% (1012/1012) |
| fields in review docs | 97.8% (622/636) |
| flagged fields | 94.3% (232/246) |
| unflagged fields | 100.0% (1402/1402) |

## Wrong fields

| Doc | Field | Truth | Predicted | Conf. | Citation | Flags | Route |
|---|---|---|---|---|---|---|---|
| inv-s3 | line_items[0].unit_price | 23.85 | 23.95 | 0.8 | unverifiable | low_confidence | needs_review |
| inv-s3 | line_items[0].amount | 238.5 | 239.5 | 0.8 | unverifiable | low_confidence, rule:line_items_sum_to_subtotal | needs_review |
| lr-s2 | total_paid | 849692.92 | 649692.92 | 0.6 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid, rule:total_paid_plus_reserved_equals_incurred | needs_review |
| lr-s2 | claims[2].paid | 44050.7 | 44060.7 | 0.75 | unverifiable | low_confidence, rule:claims[2]_paid_plus_reserve_equals_incurred, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[3].claim_number | BFC24-39763 | BFC24-39783 | 0.75 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[4].date_of_loss | 2024-05-20 | 2024-06-29 | 0.75 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[7].paid | 46904.74 | 46804.74 | 0.72 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[7].reserved | 15320.79 | 15420.79 | 0.72 | unverifiable | low_confidence, rule:claims_reserved_sum_to_total_reserved | needs_review |
| lr-s2 | claims[9].claim_number | BFC24-92127 | BFC24-02127 | 0.75 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[10].paid | 1868.28 | 1858.28 | 0.72 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[10].incurred | 22567.15 | 22557.15 | 0.72 | unverifiable | low_confidence, rule:claims_incurred_sum_to_total_incurred | needs_review |
| lr-s2 | claims[17].incurred | 36968.79 | 35968.79 | 0.72 | unverifiable | low_confidence, rule:claims[17]_paid_plus_reserve_equals_incurred, rule:claims_incurred_sum_to_total_incurred | needs_review |
| lr-s2 | claims[28].claim_number | BFC24-95581 | BFC24-99681 | 0.8 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[29].claim_number | BFC24-35590 | BFC24-35690 | 0.72 | unverifiable | low_confidence | needs_review |

## Confidence calibration

Each field's self-reported confidence against whether it was right. Row fields share their row's confidence, so bins are not independent samples.

| Confidence bin | Fields | Mean confidence | Observed accuracy |
|---|---|---|---|
| [0.00, 0.50) | 0 |  |  |
| [0.50, 0.70) | 3 | 0.6 | 0.667 |
| [0.70, 0.80) | 126 | 0.729 | 0.921 |
| [0.80, 0.90) | 99 | 0.806 | 0.97 |
| [0.90, 0.95) | 434 | 0.929 | 1.0 |
| [0.95, 0.98) | 968 | 0.955 | 1.0 |
| [0.98, 1.00] | 18 | 0.98 | 1.0 |

## Threshold sweep (same run, other checks unchanged)

| Threshold | Auto-accepted docs | Auto-accepted fields | Wrong fields auto-accepted |
|---|---|---|---|
| 0.5 | 24 | 1050 | 0 |
| 0.7 | 24 | 1050 | 0 |
| 0.8 | 24 | 1050 | 0 |
| 0.85 | 24 | 1050 | 0 |
| 0.9 | 23 | 1012 | 0 |
| 0.95 | 11 | 489 | 0 |
| 0.97 | 1 | 9 | 0 |

## Documents

| Doc | Variant | Expected | Route | Reasons | Wrong/fields | Tries | Tokens in/out | Cost | ms |
|---|---|---|---|---|---|---|---|---|---|
| inv-01 | standard | accept | auto_accept |  | 0/26 | 1 | 4689/1407 | 0.00117 | 6098.5 |
| inv-02 | standard | accept | auto_accept |  | 0/38 | 1 | 4761/1635 | 0.00129 | 6726.9 |
| inv-03 | standard | accept | auto_accept |  | 0/34 | 1 | 4751/1452 | 0.00120 | 6162.4 |
| inv-04 | standard | accept | auto_accept |  | 0/30 | 1 | 4709/1556 | 0.00125 | 6609.5 |
| inv-05 | two_page | accept | auto_accept |  | 0/114 | 1 | 6852/3779 | 0.00257 | 12540.0 |
| inv-06 | total_mismatch | review | needs_review | rule_failed | 0/38 | 1 | 4774/1972 | 0.00146 | 7780.8 |
| inv-07 | missing_field | review | needs_review | missing_required | 0/38 | 1 | 4752/1590 | 0.00127 | 5459.9 |
| inv-08 | scanned_png | review | needs_review | no_text_layer | 0/26 | 1 | 4788/1319 | 0.00114 | 5641.8 |
| inv-09 | scanned_pdf | review | needs_review | low_confidence, no_text_layer | 0/38 | 1 | 4294/1664 | 0.00126 | 6064.7 |
| inv-10 | standard | accept | auto_accept |  | 0/26 | 1 | 4662/1279 | 0.00111 | 4781.7 |
| inv-s1 | ship_to_distractor | accept | auto_accept |  | 0/22 | 1 | 4709/964 | 0.00095 | 3782.1 |
| inv-s2 | deposit_balance_due | accept | needs_review | low_confidence | 0/38 | 1 | 4771/1801 | 0.00138 | 7619.9 |
| inv-s3 | degraded_scan_jpeg | review | needs_review | low_confidence, no_text_layer, rule_failed | 2/22 | 1 | 3508/1333 | 0.00102 | 4936.2 |
| inv-s4 | discount_line | accept | auto_accept |  | 0/42 | 1 | 4786/1921 | 0.00144 | 6590.4 |
| inv-s5 | page_subtotal | accept | auto_accept |  | 0/114 | 1 | 6859/4052 | 0.00271 | 12935.5 |
| lr-01 | standard | accept | auto_accept |  | 0/51 | 1 | 4895/2198 | 0.00159 | 7860.2 |
| lr-02 | standard | accept | auto_accept |  | 0/57 | 1 | 4943/2410 | 0.00170 | 7940.6 |
| lr-03 | standard | accept | auto_accept |  | 0/51 | 1 | 4892/2125 | 0.00155 | 7575.5 |
| lr-04 | two_page | accept | auto_accept |  | 0/213 | 1 | 7852/7061 | 0.00432 | 20534.1 |
| lr-05 | total_mismatch | review | needs_review | rule_failed | 0/51 | 1 | 4901/2166 | 0.00157 | 8276.3 |
| lr-06 | date_out_of_period | review | needs_review | rule_failed | 0/39 | 1 | 4806/1840 | 0.00140 | 8100.2 |
| lr-07 | no_claims | accept | auto_accept |  | 0/9 | 1 | 4573/864 | 0.00089 | 3929.1 |
| lr-08 | scanned_png | review | needs_review | no_text_layer | 0/45 | 1 | 4888/2006 | 0.00149 | 6921.8 |
| lr-09 | scanned_pdf | review | needs_review | no_text_layer | 0/33 | 1 | 4342/1676 | 0.00127 | 5908.3 |
| lr-10 | standard | accept | auto_accept |  | 0/57 | 1 | 4955/2450 | 0.00172 | 7969.6 |
| lr-s1 | split_paid_columns | accept | auto_accept |  | 0/51 | 1 | 4922/2238 | 0.00161 | 8052.2 |
| lr-s2 | degraded_scan_two_page | review | needs_review | low_confidence, no_text_layer, rule_failed | 12/213 | 1 | 5905/7566 | 0.00437 | 27702.2 |
| w2-01 | standard | accept | auto_accept |  | 0/11 | 1 | 4332/887 | 0.00088 | 4720.4 |
| w2-02 | standard | accept | auto_accept |  | 0/11 | 1 | 4335/758 | 0.00081 | 3626.1 |
| w2-03 | standard | accept | auto_accept |  | 0/11 | 1 | 4337/846 | 0.00086 | 3981.2 |
| w2-04 | standard | accept | auto_accept |  | 0/11 | 1 | 4329/836 | 0.00085 | 3697.7 |
| w2-05 | missing_field | review | needs_review | missing_required | 0/11 | 1 | 4326/944 | 0.00090 | 3922.3 |
| w2-06 | ss_tax_mismatch | review | needs_review | low_confidence, rule_failed | 0/11 | 1 | 4325/865 | 0.00086 | 3846.7 |
| w2-07 | scanned_png | review | needs_review | no_text_layer | 0/11 | 1 | 4596/862 | 0.00089 | 4314.2 |
| w2-08 | scanned_pdf | review | needs_review | no_text_layer | 0/11 | 1 | 3956/836 | 0.00081 | 4628.6 |
| w2-09 | standard | accept | auto_accept |  | 0/11 | 1 | 4326/736 | 0.00080 | 3509.8 |
| w2-10 | standard | accept | auto_accept |  | 0/11 | 1 | 4336/793 | 0.00083 | 4046.3 |
| w2-s1 | high_earner | accept | auto_accept |  | 0/11 | 1 | 4340/737 | 0.00080 | 3099.9 |
| w2-s2 | degraded_scan_jpeg | review | needs_review | citation_failed, low_confidence, no_text_layer | 0/11 | 1 | 3228/889 | 0.00077 | 3908.2 |

## Review reasons per document

- `inv-06`: 2382.85 + 166.80 = 2549.65, total is 2567.65
- `inv-07`: required field invoice_date is empty
- `inv-08`: scanned document: citations cannot be checked against text
- `inv-09`: invoice_date confidence 0.80 < 0.90; due_date confidence 0.80 < 0.90; scanned document: citations cannot be checked against text
- `inv-s2`: subtotal confidence 0.88 < 0.90
- `inv-s3`: po_number confidence 0.80 < 0.90; line_items[0].description confidence 0.80 < 0.90; line_items[0].quantity confidence 0.80 < 0.90; line_items[0].unit_price confidence 0.80 < 0.90; line_items[0].amount confidence 0.80 < 0.90; line_items[1].description confidence 0.85 < 0.90; line_items[1].quantity confidence 0.85 < 0.90; line_items[1].unit_price confidence 0.85 < 0.90
- `lr-05`: claim incurred sums to 306,470.53, printed total is 311,470.53; 224,777.67 + 81,692.86 != 311,470.53
- `lr-06`: claims [1] have a date of loss outside 2024-01-01..2025-01-01
- `lr-08`: scanned document: citations cannot be checked against text
- `lr-09`: scanned document: citations cannot be checked against text
- `lr-s2`: claims[0].claim_number confidence 0.80 < 0.90; claims[0].date_of_loss confidence 0.80 < 0.90; claims[0].status confidence 0.80 < 0.90; claims[0].paid confidence 0.80 < 0.90; claims[0].reserved confidence 0.80 < 0.90; claims[0].incurred confidence 0.80 < 0.90; claims[1].claim_number confidence 0.80 < 0.90; claims[1].date_of_loss confidence 0.80 < 0.90
- `w2-05`: required field employer_ein is empty
- `w2-06`: employee_ssn confidence 0.85 < 0.90; box 4 is 4694.56; 6.2% of box 3 is 4294.56
- `w2-07`: scanned document: citations cannot be checked against text
- `w2-08`: scanned document: citations cannot be checked against text
- `w2-s2`: employer_name confidence 0.80 < 0.90; employer_name citation value_not_in_citation; scanned document: citations cannot be checked against text
