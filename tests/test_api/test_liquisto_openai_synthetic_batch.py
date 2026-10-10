"""Synthetic offline verification; every HTTP request uses MockTransport."""
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from src.api.services import liquisto_mail_openai as provider
from src.api.services.liquisto_openai_budget import OpenAIBudgetError, OpenAIHttpBudget
from src.api.services.liquisto_openai_synthetic_batch import CASES, batch_request_bytes, run_batch


def test_persistent_atomic_http_limit_counts_every_attempt(tmp_path):
    path = tmp_path / "budget.sqlite"

    def attempt(_):
        try:
            OpenAIHttpBudget(path).reserve("count")
            return True
        except OpenAIBudgetError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(12)))
    assert results.count(True) == 5
    assert OpenAIHttpBudget(path).attempts() == 5
    with pytest.raises(OpenAIBudgetError):
        OpenAIHttpBudget(path).reserve("generate")


def test_fixed_batch_uses_only_its_own_synthetic_reference():
    body = json.loads(batch_request_bytes())
    cases = json.loads(body["input"][1]["content"])["synthetic_test_cases"]
    assert [case["case_id"] for case in cases] == list(CASES)
    assert len(cases[0]["context"]) == 1
    assert all(case["context"] == [] for case in cases[1:])
    assert "erfundenen Testwelt" in cases[0]["context"][0]["content"]
    assert set(body) == {"model", "input", "reasoning", "max_output_tokens", "store", "service_tier", "text"}
    assert body["max_output_tokens"] == 2560 and body["store"] is False
    assert set(body["text"]["format"]["schema"]["required"]) == set(CASES)
    bound = (8192 * provider.INPUT_PRICE_CEILING + 2560 * provider.OUTPUT_PRICE_CEILING)
    assert (bound + 999_999) // 1_000_000 == 3584


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "count", "generate", "usage", "case", "actions", "words"])
async def test_two_calls_maximum_no_retry_or_repeat(monkeypatch, tmp_path, failure):
    calls = []
    encoded = json.loads(batch_request_bytes())
    answers = {name: {"answer": "Synthetischer Test.", "prepared_actions": []} for name in CASES}
    if failure == "case":
        answers.pop("english")
    elif failure == "actions":
        answers["status"]["prepared_actions"] = ["send"]
    elif failure == "words":
        answers["status"]["answer"] = "word " * 61

    def handle(request):
        calls.append(str(request.url))
        if str(request.url) == provider.COUNT_ENDPOINT:
            count_body = json.loads(request.content)
            assert count_body == {name: encoded[name] for name in ("model", "input", "text", "reasoning")}
            return httpx.Response(403 if failure == "count" else 200,
                                  json={"object": "response.input_tokens", "input_tokens": 1024})
        assert str(request.url) == provider.ENDPOINT
        assert json.loads(request.content) == encoded
        return httpx.Response(429 if failure == "generate" else 200, json={
            "status": "completed", "usage": {"input_tokens": 1025 if failure == "usage" else 1024,
                                                "output_tokens": 256},
            "output": [{"type": "message", "role": "assistant", "status": "completed", "content": [
                {"type": "output_text", "annotations": [], "text": json.dumps(answers)},
            ]}],
        })

    original = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient", lambda **kwargs: original(
        transport=httpx.MockTransport(handle), **kwargs,
    ))
    budget = OpenAIHttpBudget(tmp_path / "budget.sqlite")
    key = SecretStr("fixture-only-key")
    if failure is None:
        usage = {}
        assert set(await run_batch(key, budget, usage_out=usage)) == set(CASES)
        assert usage == {"input_tokens": 1024, "output_tokens": 256,
                         "standard_generation_cost_ceiling_micro_usd": 410}
    else:
        with pytest.raises(provider.MailOpenAIError, match="no_retry"):
            await run_batch(key, budget)
    assert budget.attempts() == len(calls) == (1 if failure == "count" else 2)
    with pytest.raises(OpenAIBudgetError):
        await run_batch(key, OpenAIHttpBudget(budget.path))
    assert budget.attempts() == len(calls)


def runner():
    path = Path(__file__).resolve().parents[2] / "deploy/liquisto-assistant/run_openai_synthetic_batch.py"
    spec = importlib.util.spec_from_file_location("synthetic_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("content", ["", "OPENAI_API_KEY=fixture", "OLIVIA_OPENAI_API_KEY=",
                                      "OLIVIA_OPENAI_API_KEY=fixture\nOLIVIA_OPENAI_API_KEY=other",
                                      "OLIVIA_OPENAI_API_KEY=two words"])
def test_runner_rejects_invalid_synthetic_key_files(tmp_path, content):
    path = tmp_path / "synthetic.env"
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(ValueError):
        runner().protected_key(path)


@pytest.mark.parametrize("wrapper", ["", "'", '"'])
def test_runner_accepts_exactly_one_synthetic_key_and_safe_quotes(tmp_path, wrapper):
    path = tmp_path / "synthetic.env"
    path.write_text(f"# Synthetic fixture\nOLIVIA_OPENAI_API_KEY={wrapper}fixture-only{wrapper}\n",
                    encoding="utf-8")
    path.chmod(0o600)
    assert runner().protected_key(path).get_secret_value() == "fixture-only"


def test_describe_never_reads_key_or_consumes_budget(monkeypatch, capsys):
    module = runner()
    monkeypatch.setattr(module, "protected_key", lambda _: pytest.fail("key read"))
    monkeypatch.setattr(module, "run_batch", lambda *_: pytest.fail("provider called"))
    monkeypatch.setattr("sys.argv", ["runner", "--describe"])
    module.main()
    description = json.loads(capsys.readouterr().out)
    assert description["maximum_http_calls"] == 2
    assert description["maximum_standard_generation_cost_micro_usd"] == 3584


def test_output_reuse_fails_before_key_read_or_provider(monkeypatch, tmp_path):
    module = runner()
    output = tmp_path / "existing.json"
    output.write_text("preserve", encoding="utf-8")
    monkeypatch.setattr(module, "protected_key", lambda _: pytest.fail("key read"))
    monkeypatch.setattr(module, "run_batch", lambda *_: pytest.fail("provider called"))
    monkeypatch.setattr("sys.argv", ["runner", "--key-file", str(tmp_path / "key.env"),
                                    "--ledger-file", str(tmp_path / "budget.sqlite"),
                                    "--output-file", str(output),
                                    "--approved-price-snapshot", provider.PRICE_SNAPSHOT])
    with pytest.raises(SystemExit):
        module.main()
    assert output.read_text(encoding="utf-8") == "preserve"
