import copy
import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from intake.anthropic_model import AnthropicModel
from intake.extract import extract
from intake.model_client import ModelError
from intake.pipeline import process
from intake.schemas import output_json_schema
from intake.scripted_model import ScriptedModel
from tests.conftest import doc, good_answer


def test_schema_retry_then_success_sends_problems_not_values():
    d = doc("w2-01")
    bad = copy.deepcopy(good_answer("w2-01"))
    bad["wages"]["confidence"] = 1.4
    bad["tax_year"]["value"] = "twenty twenty five"
    model = ScriptedModel({d.sha256: [bad, good_answer("w2-01")]})
    out = extract(d, "w2", model)
    assert out.extraction is not None and out.attempts == 2
    retry_prompt = model.requests[1]["content"][1]["text"]
    assert "wages.confidence" in retry_prompt and "tax_year.value" in retry_prompt
    assert "twenty" not in retry_prompt  # input values are never echoed back


def test_two_invalid_answers_route_to_review():
    d = doc("inv-01")
    model = ScriptedModel({d.sha256: ["not json", json.dumps({"vendor_name": 3})]})
    r = process(d, "invoice", model, threshold=0.9)
    assert r.attempts == 2 and r.route == "needs_review"
    assert r.reasons[0].code == "extraction_invalid" and r.fields == []


def test_page_out_of_range_is_a_validation_error():
    d = doc("inv-01")
    a = good_answer("inv-01")
    a["total"]["page"] = 3
    out = extract(d, "invoice", ScriptedModel({d.sha256: [a, a]}))
    assert out.extraction is None
    assert any("total.page" in p for p in out.problems)


def test_unmasked_ssn_value_never_fails_validation_because_code_masks_first():
    d = doc("w2-01")
    a = good_answer("w2-01")
    a["employee_ssn"]["value"] = "000-24-5506"
    out = extract(d, "w2", ScriptedModel({d.sha256: [a]}))
    assert out.attempts == 1 and out.extraction.employee_ssn.value == "XXX-XX-5506"


def test_max_tokens_cutoff_triggers_retry():
    d = doc("inv-01")

    class Cut(ScriptedModel):
        def complete(self, **kw):
            resp = super().complete(**kw)
            if len(self.requests) == 1:
                resp.stop_reason = "max_tokens"
            return resp

    out = extract(d, "invoice", Cut({d.sha256: [good_answer("inv-01")]}))
    assert out.attempts == 2 and out.extraction is not None


def test_model_error_routes_to_review():
    d = doc("inv-01")
    r = process(d, "invoice", ScriptedModel({}), threshold=0.9)
    assert r.route == "needs_review" and r.reasons[0].code == "model_error"


def test_json_schema_is_strict_and_has_no_unsupported_keywords():
    def walk(node):
        if isinstance(node, dict):
            for bad in ("minimum", "maximum", "title", "default"):
                assert bad not in node
            if node.get("type") == "object" and "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for t in ("invoice", "w2", "loss_run"):
        walk(output_json_schema(t))


# ---------------------------------------------------------------- AnthropicModel with a stub

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


class StubMessages:
    def __init__(self, outcome):
        self.outcome, self.kwargs = outcome, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_anthropic_model_request_shape_for_pdf():
    d = doc("inv-01")
    resp = SimpleNamespace(stop_reason="end_turn",
                           content=[SimpleNamespace(type="thinking", thinking=""),
                                    SimpleNamespace(type="text",
                                                    text=json.dumps(good_answer("inv-01")))],
                           usage=SimpleNamespace(input_tokens=4600, output_tokens=1500))
    stub = StubMessages(resp)
    r = process(d, "invoice", AnthropicModel("claude-haiku-5-5",
                                             client=SimpleNamespace(messages=stub)),
                threshold=0.9)
    assert r.route == "auto_accept" and r.input_tokens == 4600
    assert r.cost_usd == pytest.approx((4600 * 0.10 + 1500 * 0.50) / 1e6)
    block = stub.kwargs["messages"][0]["content"][0]
    assert block["type"] == "document" and block["source"]["media_type"] == "application/pdf"
    assert stub.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "temperature" not in stub.kwargs


def test_anthropic_model_uses_image_block_for_png():
    d = doc("inv-08")
    stub = StubMessages(SimpleNamespace(stop_reason="end_turn", content=[
        SimpleNamespace(type="text", text=json.dumps(good_answer("inv-08")))],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1)))
    AnthropicModel("m", client=SimpleNamespace(messages=stub)).complete(
        system="s", content=[d.content_block()], schema={})
    assert stub.kwargs["messages"][0]["content"][0]["type"] == "image"


@pytest.mark.parametrize("exc", [
    anthropic.RateLimitError("rl", response=httpx2.Response(429, request=REQUEST), body=None),
    anthropic.InternalServerError("5xx", response=httpx2.Response(500, request=REQUEST),
                                  body=None),
    anthropic.APITimeoutError(request=REQUEST),
])
def test_anthropic_errors_become_model_error(exc):
    m = AnthropicModel("m", client=SimpleNamespace(messages=StubMessages(exc)))
    with pytest.raises(ModelError):
        m.complete(system="s", content=[], schema={})


def test_refusal_becomes_model_error():
    m = AnthropicModel("m", client=SimpleNamespace(messages=StubMessages(SimpleNamespace(
        stop_reason="refusal", content=[], usage=None))))
    with pytest.raises(ModelError):
        m.complete(system="s", content=[], schema={})
