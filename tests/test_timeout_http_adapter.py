from requests.models import Response

from utils.timeout_http_adapter import TimeoutHTTPAdapter


class DummyRequest:
    url = "https://example.com/api"
    body = b'{"name": "demo"}'
    headers = {"Content-Type": "application/json"}


def test_adapter_sets_default_timeout(monkeypatch):
    captured_kwargs = {}

    def fake_send(self, request, **kwargs):
        captured_kwargs.update(kwargs)
        response = Response()
        response.status_code = 200
        response._content = b'{"code": 200}'
        response.url = request.url
        return response

    monkeypatch.setattr("requests.adapters.HTTPAdapter.send", fake_send)

    adapter = TimeoutHTTPAdapter(timeout=12)
    response = adapter.send(DummyRequest())

    assert response.status_code == 200
    assert captured_kwargs["timeout"] == 12


def test_adapter_prints_business_error_when_rule_matches(monkeypatch, capsys):
    def fake_send(self, request, **kwargs):
        response = Response()
        response.status_code = 200
        response._content = b'{"code": 500, "message": "failed"}'
        response.url = request.url
        return response

    monkeypatch.setattr("requests.adapters.HTTPAdapter.send", fake_send)

    adapter = TimeoutHTTPAdapter(
        timeout=12,
        business_error_rules={"code": {"success_values": [0, 200]}},
    )
    response = adapter.send(DummyRequest())

    assert response.status_code == 200
    assert "接口异常信息开始" in capsys.readouterr().out
