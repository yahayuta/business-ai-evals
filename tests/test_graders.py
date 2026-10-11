from evalkit.graders import grade, normalize_order_id, parse_json

LABELS = ["order_status", "cancel_order", "return_refund", "complaint"]
EXPECTED = {"category": "cancel_order", "order_id": "ORD-10990", "sentiment": "neutral"}


def test_parse_json_plain_and_fenced():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! Here it is: {"a": 1} hope that helps') == {"a": 1}


def test_parse_json_rejects_non_objects():
    assert parse_json("not json") is None
    assert parse_json("[1, 2]") is None


def test_normalize_order_id():
    assert normalize_order_id("#10990") == "ORD-10990"
    assert normalize_order_id("order 10990") == "ORD-10990"
    assert normalize_order_id("ord-10990") == "ORD-10990"
    assert normalize_order_id(None) is None
    assert normalize_order_id("null") is None


def test_pass_after_normalisation():
    g = grade(EXPECTED, '{"category": "Cancel_Order", "order_id": "#10990", "sentiment": "neutral"}', LABELS)
    assert g.passed and g.error_type is None


def test_error_precedence():
    assert grade(EXPECTED, "cancel please", LABELS).error_type == "invalid_json"
    assert (
        grade(EXPECTED, '{"category": "cancel_order", "order_id": "ORD-10990"}', LABELS).error_type == "missing_field"
    )
    assert (
        grade(EXPECTED, '{"category": "refund", "order_id": "ORD-10990", "sentiment": "neutral"}', LABELS).error_type
        == "invalid_label"
    )
    # category is checked before order_id
    g = grade(EXPECTED, '{"category": "return_refund", "order_id": null, "sentiment": "neutral"}', LABELS)
    assert g.error_type == "wrong_category"
    assert g.field_correct == {"category": False, "order_id": False, "sentiment": True}


def test_invented_order_id_is_an_error():
    expected = {"category": "complaint", "order_id": None, "sentiment": "negative"}
    g = grade(expected, '{"category": "complaint", "order_id": "ORD-11111", "sentiment": "negative"}', LABELS)
    assert g.error_type == "wrong_order_id"
