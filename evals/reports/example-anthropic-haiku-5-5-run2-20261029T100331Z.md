# Eval report: anthropic / claude-haiku-5-5 / split all

Generated 20261029T100331Z (UTC). Confidence threshold 0.9.

> Anthropic mode: answers come from the real Claude API.

## Summary

| Metric | Value |
|---|---|
| Documents | 39 |
| Fields scored | 1648 |
| Field accuracy, all | 99.0% (1631/1648) |
| Auto-accepted documents | 22 |
| Documents sent to review | 17 |
| Hard cases sent to review | 15 of 15 |
| Hard cases flagged for the expected reason | 15 |
| Clean documents sent to review | 2 of 24 |
| ...of which had no wrong field (false alarms) | 2 |
| Wrong fields | 17 |
| Wrong fields in reviewed documents (caught, document level) | 17 |
| ...wrong values the model produced / fields it never produced | 17 / 0 |
| Wrong produced values individually flagged (caught, field level) | 17 of 17 |
| Wrong fields in auto-accepted documents (missed) | 0 |
| Documents that needed the schema retry | 0 |
| Extraction failures (invalid twice, or API error) | 0 |
| PII strings masked by code | 0 |
| Total cost (USD) | 0.0547 |
| Mean cost per document (USD) | 0.0014 |
| Input / output tokens | 186,305 / 72,140 |
| Latency per document, mean / p50 / p95 / max (ms) | 6807.8 / 5946.2 / 12641.6 / 24284.8 |

## Field accuracy

| Slice | Accuracy |
|---|---|
| split: core | 100.0% (1124/1124) |
| split: stress | 96.8% (507/524) |
| type: invoice | 99.9% (645/646) |
| type: loss_run | 98.2% (854/870) |
| type: w2 | 100.0% (132/132) |
| variant: date_out_of_period | 100.0% (39/39) |
| variant: degraded_scan_jpeg | 97.0% (32/33) |
| variant: degraded_scan_two_page | 92.5% (197/213) |
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
| fields in auto-accepted docs | 100.0% (1028/1028) |
| fields in review docs | 97.3% (603/620) |
| flagged fields | 92.9% (221/238) |
| unflagged fields | 100.0% (1410/1410) |

## Wrong fields

| Doc | Field | Truth | Predicted | Conf. | Citation | Flags | Route |
|---|---|---|---|---|---|---|---|
| inv-s3 | line_items[0].unit_price | 23.85 | 23.95 | 0.85 | unverifiable | low_confidence, rule:line_items[0]_qty_times_price | needs_review |
| lr-s2 | total_paid | 849692.92 | 649692.92 | 0.6 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | total_reserved | 354898.15 | 554898.15 | 0.6 | unverifiable | low_confidence, rule:claims_reserved_sum_to_total_reserved | needs_review |
| lr-s2 | claims[1].paid | 35364.11 | 35064.11 | 0.75 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[1].incurred | 35364.11 | 35064.11 | 0.75 | unverifiable | low_confidence, rule:claims_incurred_sum_to_total_incurred | needs_review |
| lr-s2 | claims[2].paid | 44050.7 | 44060.7 | 0.7 | unverifiable | low_confidence, rule:claims[2]_paid_plus_reserve_equals_incurred, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[3].claim_number | BFC24-39763 | BFC24-39783 | 0.7 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[4].date_of_loss | 2024-05-20 | 2024-06-20 | 0.7 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[9].claim_number | BFC24-92127 | BFC24-02127 | 0.7 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[10].paid | 1868.28 | 1858.28 | 0.7 | unverifiable | low_confidence, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[10].incurred | 22567.15 | 22557.15 | 0.7 | unverifiable | low_confidence, rule:claims_incurred_sum_to_total_incurred | needs_review |
| lr-s2 | claims[17].paid | 27880.72 | 27860.72 | 0.7 | unverifiable | low_confidence, rule:claims[17]_paid_plus_reserve_equals_incurred, rule:claims_paid_sum_to_total_paid | needs_review |
| lr-s2 | claims[17].reserved | 9088.07 | 9098.07 | 0.7 | unverifiable | low_confidence, rule:claims[17]_paid_plus_reserve_equals_incurred, rule:claims_reserved_sum_to_total_reserved | needs_review |
| lr-s2 | claims[17].incurred | 36968.79 | 35958.79 | 0.7 | unverifiable | low_confidence, rule:claims[17]_paid_plus_reserve_equals_incurred, rule:claims_incurred_sum_to_total_incurred | needs_review |
| lr-s2 | claims[22].claim_number | BFC24-62045 | BFC24-62049 | 0.75 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[28].claim_number | BFC24-95581 | BFC24-99681 | 0.75 | unverifiable | low_confidence | needs_review |
| lr-s2 | claims[29].claim_number | BFC24-35590 | BFC24-35690 | 0.7 | unverifiable | low_confidence | needs_review |

## Confidence calibration

Each field's self-reported confidence against whether it was right. Row fields share their row's confidence, so bins are not independent samples.

| Confidence bin | Fields | Mean confidence | Observed accuracy |
|---|---|---|---|
| [0.00, 0.50) | 0 |  |  |
| [0.50, 0.70) | 3 | 0.6 | 0.333 |
| [0.70, 0.80) | 204 | 0.719 | 0.931 |
| [0.80, 0.90) | 13 | 0.842 | 0.923 |
| [0.90, 0.95) | 222 | 0.925 | 1.0 |
| [0.95, 0.98) | 1185 | 0.955 | 1.0 |
| [0.98, 1.00] | 21 | 0.98 | 1.0 |

## Threshold sweep (same run, other checks unchanged)

| Threshold | Auto-accepted docs | Auto-accepted fields | Wrong fields auto-accepted |
|---|---|---|---|
| 0.5 | 24 | 1050 | 0 |
| 0.7 | 24 | 1050 | 0 |
| 0.8 | 24 | 1050 | 0 |
| 0.85 | 24 | 1050 | 0 |
| 0.9 | 22 | 1028 | 0 |
| 0.95 | 16 | 828 | 0 |
| 0.97 | 2 | 66 | 0 |

## Documents

| Doc | Variant | Expected | Route | Reasons | Wrong/fields | Tries | Tokens in/out | Cost | ms |
|---|---|---|---|---|---|---|---|---|---|
| inv-01 | standard | accept | auto_accept |  | 0/26 | 1 | 4689/1364 | 0.00115 | 5787.3 |
| inv-02 | standard | accept | auto_accept |  | 0/38 | 1 | 4761/1659 | 0.00131 | 6433.1 |
| inv-03 | standard | accept | auto_accept |  | 0/34 | 1 | 4751/1468 | 0.00121 | 5946.2 |
| inv-04 | standard | accept | auto_accept |  | 0/30 | 1 | 4709/1343 | 0.00114 | 7284.0 |
| inv-05 | two_page | accept | auto_accept |  | 0/114 | 1 | 6852/3785 | 0.00258 | 11593.3 |
| inv-06 | total_mismatch | review | needs_review | rule_failed | 0/38 | 1 | 4774/1682 | 0.00132 | 6286.6 |
| inv-07 | missing_field | review | needs_review | missing_required | 0/38 | 1 | 4752/1693 | 0.00132 | 5738.7 |
| inv-08 | scanned_png | review | needs_review | no_text_layer | 0/26 | 1 | 4788/1274 | 0.00112 | 5624.5 |
| inv-09 | scanned_pdf | review | needs_review | no_text_layer | 0/38 | 1 | 4294/1880 | 0.00137 | 6779.2 |
| inv-10 | standard | accept | auto_accept |  | 0/26 | 1 | 4662/1323 | 0.00113 | 5271.3 |
| inv-s1 | ship_to_distractor | accept | auto_accept |  | 0/22 | 1 | 4709/1107 | 0.00102 | 4124.5 |
| inv-s2 | deposit_balance_due | accept | auto_accept |  | 0/38 | 1 | 4771/1820 | 0.00139 | 7920.3 |
| inv-s3 | degraded_scan_jpeg | review | needs_review | low_confidence, no_text_layer, rule_failed | 1/22 | 1 | 3508/1477 | 0.00109 | 5667.5 |
| inv-s4 | discount_line | accept | auto_accept |  | 0/42 | 1 | 4786/1959 | 0.00146 | 6753.5 |
| inv-s5 | page_subtotal | accept | auto_accept |  | 0/114 | 1 | 6859/4036 | 0.00270 | 12641.6 |
| lr-01 | standard | accept | auto_accept |  | 0/51 | 1 | 4895/2294 | 0.00164 | 8008.8 |
| lr-02 | standard | accept | auto_accept |  | 0/57 | 1 | 4943/1923 | 0.00146 | 6530.9 |
| lr-03 | standard | accept | auto_accept |  | 0/51 | 1 | 4892/2165 | 0.00157 | 7622.8 |
| lr-04 | two_page | accept | auto_accept |  | 0/213 | 1 | 7852/7188 | 0.00438 | 20661.0 |
| lr-05 | total_mismatch | review | needs_review | rule_failed | 0/51 | 1 | 4901/2192 | 0.00159 | 7606.7 |
| lr-06 | date_out_of_period | review | needs_review | low_confidence, rule_failed | 0/39 | 1 | 4806/1559 | 0.00126 | 6350.4 |
| lr-07 | no_claims | accept | auto_accept |  | 0/9 | 1 | 4573/875 | 0.00089 | 3934.1 |
| lr-08 | scanned_png | review | needs_review | no_text_layer | 0/45 | 1 | 4888/1999 | 0.00149 | 6941.3 |
| lr-09 | scanned_pdf | review | needs_review | no_text_layer | 0/33 | 1 | 4342/1748 | 0.00131 | 6511.2 |
| lr-10 | standard | accept | auto_accept |  | 0/57 | 1 | 4955/2476 | 0.00173 | 7965.3 |
| lr-s1 | split_paid_columns | accept | auto_accept |  | 0/51 | 1 | 4922/2234 | 0.00161 | 7783.2 |
| lr-s2 | degraded_scan_two_page | review | needs_review | low_confidence, no_text_layer, rule_failed | 16/213 | 1 | 5905/7582 | 0.00438 | 24284.8 |
| w2-01 | standard | accept | needs_review | low_confidence | 0/11 | 1 | 4332/944 | 0.00091 | 5133.3 |
| w2-02 | standard | accept | auto_accept |  | 0/11 | 1 | 4335/846 | 0.00086 | 3543.2 |
| w2-03 | standard | accept | auto_accept |  | 0/11 | 1 | 4337/887 | 0.00088 | 4602.7 |
| w2-04 | standard | accept | auto_accept |  | 0/11 | 1 | 4329/787 | 0.00083 | 3472.4 |
| w2-05 | missing_field | review | needs_review | missing_required | 0/11 | 1 | 4326/782 | 0.00082 | 3478.4 |
| w2-06 | ss_tax_mismatch | review | needs_review | rule_failed | 0/11 | 1 | 4325/759 | 0.00081 | 3553.2 |
| w2-07 | scanned_png | review | needs_review | low_confidence, no_text_layer | 0/11 | 1 | 4596/837 | 0.00088 | 3774.4 |
| w2-08 | scanned_pdf | review | needs_review | no_text_layer | 0/11 | 1 | 3956/859 | 0.00083 | 4449.0 |
| w2-09 | standard | accept | auto_accept |  | 0/11 | 1 | 4326/850 | 0.00086 | 3751.1 |
| w2-10 | standard | accept | needs_review | low_confidence | 0/11 | 1 | 4336/816 | 0.00084 | 4285.7 |
| w2-s1 | high_earner | accept | auto_accept |  | 0/11 | 1 | 4340/887 | 0.00088 | 3914.7 |
| w2-s2 | degraded_scan_jpeg | review | needs_review | citation_failed, low_confidence, no_text_layer | 0/11 | 1 | 3228/781 | 0.00071 | 3492.3 |

## Review reasons per document

- `inv-06`: 2382.85 + 166.80 = 2549.65, total is 2567.65
- `inv-07`: required field invoice_date is empty
- `inv-08`: scanned document: citations cannot be checked against text
- `inv-09`: scanned document: citations cannot be checked against text
- `inv-s3`: po_number confidence 0.80 < 0.90; line_items[0].description confidence 0.85 < 0.90; line_items[0].quantity confidence 0.85 < 0.90; line_items[0].unit_price confidence 0.85 < 0.90; line_items[0].amount confidence 0.85 < 0.90; scanned document: citations cannot be checked against text; 10.0 x 23.95 != 238.50
- `lr-05`: claim incurred sums to 306,470.53, printed total is 311,470.53; 224,777.67 + 81,692.86 != 311,470.53
- `lr-06`: total_reserved confidence 0.85 < 0.90; claims [1] have a date of loss outside 2024-01-01..2025-01-01
- `lr-08`: scanned document: citations cannot be checked against text
- `lr-09`: scanned document: citations cannot be checked against text
- `lr-s2`: policy_number confidence 0.85 < 0.90; policy_period_start confidence 0.85 < 0.90; policy_period_end confidence 0.85 < 0.90; claims[0].claim_number confidence 0.75 < 0.90; claims[0].date_of_loss confidence 0.75 < 0.90; claims[0].status confidence 0.75 < 0.90; claims[0].paid confidence 0.75 < 0.90; claims[0].reserved confidence 0.75 < 0.90
- `w2-01`: employee_ssn confidence 0.85 < 0.90
- `w2-05`: required field employer_ein is empty
- `w2-06`: box 4 is 4694.56; 6.2% of box 3 is 4294.56
- `w2-07`: employee_ssn confidence 0.85 < 0.90; scanned document: citations cannot be checked against text
- `w2-08`: scanned document: citations cannot be checked against text
- `w2-10`: employee_ssn confidence 0.85 < 0.90
- `w2-s2`: employer_name confidence 0.80 < 0.90; employer_name citation value_not_in_citation; scanned document: citations cannot be checked against text
