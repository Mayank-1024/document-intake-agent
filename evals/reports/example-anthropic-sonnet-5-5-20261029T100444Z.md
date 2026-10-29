# Eval report: anthropic / claude-sonnet-5-5 / split all

Generated 20261029T100444Z (UTC). Confidence threshold 0.9.

> Anthropic mode: answers come from the real Claude API.

## Summary

| Metric | Value |
|---|---|
| Documents | 39 |
| Fields scored | 1648 |
| Field accuracy, all | 99.5% (1639/1648) |
| Auto-accepted documents | 24 |
| Documents sent to review | 15 |
| Hard cases sent to review | 15 of 15 |
| Hard cases flagged for the expected reason | 15 |
| Clean documents sent to review | 0 of 24 |
| ...of which had no wrong field (false alarms) | 0 |
| Wrong fields | 9 |
| Wrong fields in reviewed documents (caught, document level) | 9 |
| ...wrong values the model produced / fields it never produced | 9 / 0 |
| Wrong produced values individually flagged (caught, field level) | 9 of 9 |
| Wrong fields in auto-accepted documents (missed) | 0 |
| Documents that needed the schema retry | 0 |
| Extraction failures (invalid twice, or API error) | 0 |
| PII strings masked by code | 0 |
| Total cost (USD) | 0.8501 |
| Mean cost per document (USD) | 0.0218 |
| Input / output tokens | 186,305 / 47,747 |
| Latency per document, mean / p50 / p95 / max (ms) | 6988.4 / 6106.3 / 13045.6 / 23245.8 |

## Field accuracy

| Slice | Accuracy |
|---|---|
| split: core | 100.0% (1124/1124) |
| split: stress | 98.3% (515/524) |
| type: invoice | 100.0% (646/646) |
| type: loss_run | 99.0% (861/870) |
| type: w2 | 100.0% (132/132) |
| variant: date_out_of_period | 100.0% (39/39) |
| variant: degraded_scan_jpeg | 100.0% (33/33) |
| variant: degraded_scan_two_page | 95.8% (204/213) |
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
| fields in auto-accepted docs | 100.0% (1050/1050) |
| fields in review docs | 98.5% (589/598) |
| flagged fields | 96.3% (233/242) |
| unflagged fields | 100.0% (1406/1406) |

## Wrong fields

| Doc | Field | Truth | Predicted | Conf. | Citation | Flags | Route |
|---|---|---|---|---|---|---|---|
| lr-s2 | total_paid | 849692.92 | 649692.92 | 0.85 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid, rule:total_paid_plus_reserved_equals_incurred | needs_review |
| lr-s2 | claims[3].claim_number | BFC24-39763 | BFC24-39703 | 0.8 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[4].date_of_loss | 2024-05-20 | 2024-05-29 | 0.8 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[9].claim_number | BFC24-92127 | BFC24-02127 | 0.8 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[22].claim_number | BFC24-62045 | BFC24-82049 | 0.8 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[28].claim_number | BFC24-95581 | BFC24-98581 | 0.8 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[28].paid | 47613.16 | 47613.18 | 0.8 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[28].incurred | 47613.16 | 47613.18 | 0.8 | unverifiable | low_confidence, rule:claims_incurred_sum_to_total_incurred | needs_review |
| lr-s2 | claims[29].claim_number | BFC24-35590 | BFC24-35690 | 0.8 | unverifiable | low_confidence | needs_review |

## Confidence calibration

Each field's self-reported confidence against whether it was right. Row fields share their row's confidence, so bins are not independent samples.

| Confidence bin | Fields | Mean confidence | Observed accuracy |
|---|---|---|---|
| [0.00, 0.50) | 0 |  |  |
| [0.50, 0.70) | 0 |  |  |
| [0.70, 0.80) | 0 |  |  |
| [0.80, 0.90) | 224 | 0.807 | 0.96 |
| [0.90, 0.95) | 29 | 0.918 | 1.0 |
| [0.95, 0.98) | 1167 | 0.967 | 1.0 |
| [0.98, 1.00] | 228 | 0.981 | 1.0 |

## Threshold sweep (same run, other checks unchanged)

| Threshold | Auto-accepted docs | Auto-accepted fields | Wrong fields auto-accepted |
|---|---|---|---|
| 0.5 | 24 | 1050 | 0 |
| 0.7 | 24 | 1050 | 0 |
| 0.8 | 24 | 1050 | 0 |
| 0.85 | 24 | 1050 | 0 |
| 0.9 | 24 | 1050 | 0 |
| 0.95 | 23 | 993 | 0 |
| 0.97 | 16 | 788 | 0 |

## Documents

| Doc | Variant | Expected | Route | Reasons | Wrong/fields | Tries | Tokens in/out | Cost | ms |
|---|---|---|---|---|---|---|---|---|---|
| inv-01 | standard | accept | auto_accept |  | 0/26 | 1 | 4689/859 | 0.01797 | 5068.2 |
| inv-02 | standard | accept | auto_accept |  | 0/38 | 1 | 4761/1116 | 0.02068 | 6409.3 |
| inv-03 | standard | accept | auto_accept |  | 0/34 | 1 | 4751/1012 | 0.01962 | 6154.1 |
| inv-04 | standard | accept | auto_accept |  | 0/30 | 1 | 4709/948 | 0.01890 | 5679.1 |
| inv-05 | two_page | accept | auto_accept |  | 0/114 | 1 | 6852/2738 | 0.04108 | 12594.8 |
| inv-06 | total_mismatch | review | needs_review | rule_failed | 0/38 | 1 | 4774/1148 | 0.02103 | 8155.3 |
| inv-07 | missing_field | review | needs_review | missing_required | 0/38 | 1 | 4752/1113 | 0.02063 | 6013.0 |
| inv-08 | scanned_png | review | needs_review | no_text_layer | 0/26 | 1 | 4788/839 | 0.01797 | 7869.1 |
| inv-09 | scanned_pdf | review | needs_review | no_text_layer | 0/38 | 1 | 4294/1107 | 0.01966 | 6106.3 |
| inv-10 | standard | accept | auto_accept |  | 0/26 | 1 | 4662/824 | 0.01756 | 4635.6 |
| inv-s1 | ship_to_distractor | accept | auto_accept |  | 0/22 | 1 | 4709/767 | 0.01709 | 6607.6 |
| inv-s2 | deposit_balance_due | accept | auto_accept |  | 0/38 | 1 | 4771/1097 | 0.02051 | 5845.8 |
| inv-s3 | degraded_scan_jpeg | review | needs_review | low_confidence, no_text_layer | 0/22 | 1 | 3508/762 | 0.01464 | 4524.2 |
| inv-s4 | discount_line | accept | auto_accept |  | 0/42 | 1 | 4786/1198 | 0.02155 | 7083.8 |
| inv-s5 | page_subtotal | accept | auto_accept |  | 0/114 | 1 | 6859/2725 | 0.04097 | 13045.6 |
| lr-01 | standard | accept | auto_accept |  | 0/51 | 1 | 4895/1471 | 0.02450 | 9396.7 |
| lr-02 | standard | accept | auto_accept |  | 0/57 | 1 | 4943/1592 | 0.02581 | 7844.3 |
| lr-03 | standard | accept | auto_accept |  | 0/51 | 1 | 4892/1471 | 0.02449 | 7780.2 |
| lr-04 | two_page | accept | auto_accept |  | 0/213 | 1 | 7852/4985 | 0.06555 | 22582.4 |
| lr-05 | total_mismatch | review | needs_review | rule_failed | 0/51 | 1 | 4901/1475 | 0.02455 | 8412.4 |
| lr-06 | date_out_of_period | review | needs_review | rule_failed | 0/39 | 1 | 4806/1211 | 0.02172 | 7193.7 |
| lr-07 | no_claims | accept | auto_accept |  | 0/9 | 1 | 4573/542 | 0.01457 | 3524.7 |
| lr-08 | scanned_png | review | needs_review | no_text_layer | 0/45 | 1 | 4888/1277 | 0.02255 | 8572.1 |
| lr-09 | scanned_pdf | review | needs_review | no_text_layer | 0/33 | 1 | 4342/1063 | 0.01931 | 6239.1 |
| lr-10 | standard | accept | auto_accept |  | 0/57 | 1 | 4955/1602 | 0.02593 | 8601.0 |
| lr-s1 | split_paid_columns | accept | auto_accept |  | 0/51 | 1 | 4922/1507 | 0.02491 | 7661.0 |
| lr-s2 | degraded_scan_two_page | review | needs_review | low_confidence, no_text_layer, rule_failed | 9/213 | 1 | 5905/4990 | 0.06171 | 23245.8 |
| w2-01 | standard | accept | auto_accept |  | 0/11 | 1 | 4332/522 | 0.01388 | 3542.3 |
| w2-02 | standard | accept | auto_accept |  | 0/11 | 1 | 4335/528 | 0.01395 | 3703.7 |
| w2-03 | standard | accept | auto_accept |  | 0/11 | 1 | 4337/532 | 0.01399 | 3650.0 |
| w2-04 | standard | accept | auto_accept |  | 0/11 | 1 | 4329/587 | 0.01453 | 3890.8 |
| w2-05 | missing_field | review | needs_review | missing_required | 0/11 | 1 | 4326/510 | 0.01375 | 5174.8 |
| w2-06 | ss_tax_mismatch | review | needs_review | rule_failed | 0/11 | 1 | 4325/523 | 0.01388 | 3312.3 |
| w2-07 | scanned_png | review | needs_review | no_text_layer | 0/11 | 1 | 4596/516 | 0.01435 | 3809.0 |
| w2-08 | scanned_pdf | review | needs_review | no_text_layer | 0/11 | 1 | 3956/509 | 0.01300 | 4546.1 |
| w2-09 | standard | accept | auto_accept |  | 0/11 | 1 | 4326/526 | 0.01391 | 3192.7 |
| w2-10 | standard | accept | auto_accept |  | 0/11 | 1 | 4336/525 | 0.01392 | 3561.0 |
| w2-s1 | high_earner | accept | auto_accept |  | 0/11 | 1 | 4340/531 | 0.01399 | 4011.6 |
| w2-s2 | degraded_scan_jpeg | review | needs_review | low_confidence, no_text_layer | 0/11 | 1 | 3228/499 | 0.01145 | 3309.5 |

## Review reasons per document

- `inv-06`: 2382.85 + 166.80 = 2549.65, total is 2567.65
- `inv-07`: required field invoice_date is empty
- `inv-08`: scanned document: citations cannot be checked against text
- `inv-09`: scanned document: citations cannot be checked against text
- `inv-s3`: po_number confidence 0.80 < 0.90; line_items[0].description confidence 0.85 < 0.90; line_items[0].quantity confidence 0.85 < 0.90; line_items[0].unit_price confidence 0.85 < 0.90; line_items[0].amount confidence 0.85 < 0.90; line_items[1].description confidence 0.85 < 0.90; line_items[1].quantity confidence 0.85 < 0.90; line_items[1].unit_price confidence 0.85 < 0.90
- `lr-05`: claim incurred sums to 306,470.53, printed total is 311,470.53; 224,777.67 + 81,692.86 != 311,470.53
- `lr-06`: claims [1] have a date of loss outside 2024-01-01..2025-01-01
- `lr-08`: scanned document: citations cannot be checked against text
- `lr-09`: scanned document: citations cannot be checked against text
- `lr-s2`: valuation_date confidence 0.85 < 0.90; claims[0].claim_number confidence 0.85 < 0.90; claims[0].date_of_loss confidence 0.85 < 0.90; claims[0].status confidence 0.85 < 0.90; claims[0].paid confidence 0.85 < 0.90; claims[0].reserved confidence 0.85 < 0.90; claims[0].incurred confidence 0.85 < 0.90; claims[1].claim_number confidence 0.85 < 0.90
- `w2-05`: required field employer_ein is empty
- `w2-06`: box 4 is 4694.56; 6.2% of box 3 is 4294.56
- `w2-07`: scanned document: citations cannot be checked against text
- `w2-08`: scanned document: citations cannot be checked against text
- `w2-s2`: federal_income_tax_withheld confidence 0.88 < 0.90; medicare_tax_withheld confidence 0.88 < 0.90; scanned document: citations cannot be checked against text
