# Eval report: support-ticket-triage

## Overview

| Variant | Accuracy | Valid JSON | category | order_id | sentiment | p50 latency | Tokens (in/out) | Est. cost |
|---|---|---|---|---|---|---|---|---|
| `baseline` | **57.5%** | 92.5% | 82.5% | 75.0% | 75.0% | 573 ms | 2,037 / 906 | $0.0008 |
| `few_shot` | **65.0%** | 95.0% | 82.5% | 85.0% | 85.0% | 735 ms | 7,717 / 758 | $0.0016 |
| `few_shot_schema` | **97.5%** | 100.0% | 97.5% | 100.0% | 100.0% | 744 ms | 15,157 / 740 | $0.0027 |

## Where it fails

Each failed case gets one error type (first match in this order).

| Error type | `baseline` | `few_shot` | `few_shot_schema` |
|---|---|---|---|
| invalid_json | 3 | 2 | 0 |
| missing_field | 1 | 0 | 0 |
| invalid_label | 0 | 0 | 0 |
| wrong_category | 4 | 5 | 1 |
| wrong_order_id | 6 | 3 | 0 |
| wrong_sentiment | 3 | 4 | 0 |

## Accuracy by case tag

| Tag | `baseline` | `few_shot` | `few_shot_schema` |
|---|---|---|---|
| ambiguous | 33.3% | 44.4% | 88.9% |
| id_format | 54.5% | 90.9% | 100.0% |
| no_id | 50.0% | 50.0% | 100.0% |

## Category confusion matrix (`few_shot_schema`)

Rows are the expected label, columns the predicted one.

| expected \ predicted | order status | cancel order | return refund | address change | product question | payment issue | complaint | (other) | (none) | recall |
|---|---|---|---|---|---|---|---|---|---|---|
| order status | **7** |  |  |  |  |  |  |  |  | 100.0% |
| cancel order |  | **6** |  |  |  |  |  |  |  | 100.0% |
| return refund |  |  | **5** |  |  |  | 1 |  |  | 83.3% |
| address change |  |  |  | **5** |  |  |  |  |  | 100.0% |
| product question |  |  |  |  | **6** |  |  |  |  | 100.0% |
| payment issue |  |  |  |  |  | **5** |  |  |  | 100.0% |
| complaint |  |  |  |  |  |  | **5** |  |  | 100.0% |

## Failed cases

### `baseline` (17 failed)

| Case | Error | Input | Expected | Output |
|---|---|---|---|---|
| T002 | invalid_json | Can you tell me when order #10871 will ship? | category=order_status, order_id=ORD-10871, sentiment=neutral | `Category: order_status. The customer sounds negative.` |
| T004 | invalid_json | Just checking the delivery date for ORD-12210, thanks a lot! | category=order_status, order_id=ORD-12210, sentiment=positive | `Category: order_status. The customer sounds neutral.` |
| T007 | wrong_sentiment | I want to cancel my order before it ships. The number is 11345. | category=cancel_order, order_id=ORD-11345, sentiment=neutral | `{"category": "cancel_order", "order_id": "#11345", "sentiment": "negative"}` |
| T011 | invalid_json | The jacket from ORD-10450 doesn't fit. How do I return it? | category=return_refund, order_id=ORD-10450, sentiment=neutral | `Category: return_refund. The customer sounds neutral.` |
| T014 | wrong_category | Item arrived broken. I want my money back. ORD-12118 | category=return_refund, order_id=ORD-12118, sentiment=negative | `{"category": "complaint", "order_id": null, "sentiment": "neutral"}` |
| T015 | wrong_order_id | What is your return policy for sale items? | category=return_refund, order_id=None, sentiment=neutral | `Sure! Here is the classification: '''json {"category": "return_refund", "order_id": "ORD-10697", "sentiment": "neutral"}` |
| T019 | wrong_order_id | Can I have my order delivered to my office? I'll be out all day. | category=address_change, order_id=None, sentiment=neutral | `Sure! Here is the classification: '''json {"category": "address_change", "order_id": "ORD-10229", "sentiment": "neutral"` |
| T022 | missing_field | Does the 2L water bottle fit in a standard car cup holder? | category=product_question, order_id=None, sentiment=neutral | `{"category": "product_question", "order_id": null}` |
| T023 | wrong_sentiment | Love the notebooks! Do you sell refills for the A5 size? | category=product_question, order_id=None, sentiment=positive | `{"category": "product_question", "order_id": null, "sentiment": "neutral"}` |
| T025 | wrong_order_id | The size chart is confusing. Is M closer to a US S or M? | category=product_question, order_id=None, sentiment=negative | `Sure! Here is the classification: '''json {"category": "product_question", "order_id": "ORD-11189", "sentiment": "neutra` |
| T027 | wrong_order_id | Payment failed at checkout but the money left my account. Order 11590? | category=payment_issue, order_id=ORD-11590, sentiment=negative | `Sure! Here is the classification: '''json {"category": "payment_issue", "order_id": null, "sentiment": "negative"} '''` |
| T029 | wrong_order_id | I used a coupon but the discount wasn't applied to #12150. | category=payment_issue, order_id=ORD-12150, sentiment=negative | `Sure! Here is the classification: '''json {"category": "payment_issue", "order_id": null, "sentiment": "neutral"} '''` |
| T035 | wrong_order_id | Honestly disappointed. The quality of ORD-12240 is nothing like the photos. | category=complaint, order_id=ORD-12240, sentiment=negative | `{"category": "complaint", "order_id": null, "sentiment": "negative"}` |
| T036 | wrong_category | Order ORD-10380 arrived early and everything is perfect. Where can I leave a review? | category=product_question, order_id=ORD-10380, sentiment=positive | `{"category": "complaint", "order_id": "ORD-10380", "sentiment": "positive"}` |
| T037 | wrong_category | I need to cancel #11888 and get a refund for the shipping fee too. | category=cancel_order, order_id=ORD-11888, sentiment=neutral | `Sure! Here is the classification: '''json {"category": "return_refund", "order_id": "#11888", "sentiment": "neutral"} ''` |
| ... | | 2 more | | |

### `few_shot` (14 failed)

| Case | Error | Input | Expected | Output |
|---|---|---|---|---|
| T001 | wrong_sentiment | Hi, where is my order ORD-10234? It was supposed to arrive yesterday. | category=order_status, order_id=ORD-10234, sentiment=neutral | `{"category": "order_status", "order_id": "ORD-10234", "sentiment": "negative"}` |
| T005 | wrong_category | My package says delivered but I never got it. Order ORD-10555. | category=order_status, order_id=ORD-10555, sentiment=negative | `{"category": "complaint", "order_id": null, "sentiment": "negative"}` |
| T008 | wrong_category | Cancel order #12003 now. I've been waiting two weeks and I'm done. | category=cancel_order, order_id=ORD-12003, sentiment=negative | `{"category": "return_refund", "order_id": "ORD-12003", "sentiment": "negative"}` |
| T014 | wrong_category | Item arrived broken. I want my money back. ORD-12118 | category=return_refund, order_id=ORD-12118, sentiment=negative | `{"category": "complaint", "order_id": "ORD-12118", "sentiment": "negative"}` |
| T018 | wrong_sentiment | Please update the shipping address for #12077 before it leaves the warehouse! | category=address_change, order_id=ORD-12077, sentiment=neutral | `{"category": "address_change", "order_id": "ORD-12077", "sentiment": "negative"}` |
| T022 | wrong_order_id | Does the 2L water bottle fit in a standard car cup holder? | category=product_question, order_id=None, sentiment=neutral | `{"category": "product_question", "order_id": "ORD-12987", "sentiment": "neutral"}` |
| T023 | invalid_json | Love the notebooks! Do you sell refills for the A5 size? | category=product_question, order_id=None, sentiment=positive | `Category: product_question. The customer sounds positive.` |
| T024 | invalid_json | When will the grey hoodie be back in stock? | category=product_question, order_id=None, sentiment=neutral | `Category: product_question. The customer sounds neutral.` |
| T026 | wrong_sentiment | My card was charged twice for ORD-10789. | category=payment_issue, order_id=ORD-10789, sentiment=negative | `{"category": "payment_issue", "order_id": "ORD-10789", "sentiment": "neutral"}` |
| T028 | wrong_order_id | Can I pay by bank transfer instead of card? | category=payment_issue, order_id=None, sentiment=neutral | `{"category": "payment_issue", "order_id": "ORD-10522", "sentiment": "neutral"}` |
| T032 | wrong_order_id | Third time I'm writing about this and nobody answers. Terrible service. | category=complaint, order_id=None, sentiment=negative | `{"category": "complaint", "order_id": "ORD-11010", "sentiment": "negative"}` |
| T034 | wrong_sentiment | Your support agent was rude to me on the phone yesterday. | category=complaint, order_id=None, sentiment=negative | `Sure! Here is the classification: '''json {"category": "complaint", "order_id": null, "sentiment": "neutral"} '''` |
| T035 | wrong_category | Honestly disappointed. The quality of ORD-12240 is nothing like the photos. | category=complaint, order_id=ORD-12240, sentiment=negative | `{"category": "return_refund", "order_id": "ORD-12240", "sentiment": "negative"}` |
| T036 | wrong_category | Order ORD-10380 arrived early and everything is perfect. Where can I leave a review? | category=product_question, order_id=ORD-10380, sentiment=positive | `{"category": "complaint", "order_id": "ORD-10380", "sentiment": "positive"}` |

### `few_shot_schema` (1 failed)

| Case | Error | Input | Expected | Output |
|---|---|---|---|---|
| T014 | wrong_category | Item arrived broken. I want my money back. ORD-12118 | category=return_refund, order_id=ORD-12118, sentiment=negative | `{"category": "complaint", "order_id": "ORD-12118", "sentiment": "negative"}` |

