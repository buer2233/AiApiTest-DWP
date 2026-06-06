import pytest

from test_case.page_api.public.base_api import BaseAPI


class DummyResponse:
    status_code = 200
    reason = "OK"
    text = '{"code": 200, "data": {"name": "demo"}}'

    def json(self):
        return {"code": 200, "data": {"name": "demo"}}


class DummySession:
    def __init__(self):
        self.calls = []
        self.headers = {}
        self.cookies = {}
        self.proxies = {}

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return DummyResponse()


def test_build_url_joins_base_url_and_relative_path():
    api = BaseAPI(base_url="https://example.com/api")

    assert api.build_url("/users") == "https://example.com/api/users"
    assert api.build_url("users") == "https://example.com/api/users"


def test_build_url_keeps_absolute_url():
    api = BaseAPI(base_url="https://example.com")

    assert api.build_url("https://other.example/path") == "https://other.example/path"


def test_request_asserts_status_code_and_returns_json():
    api = BaseAPI(base_url="https://example.com")
    session = DummySession()
    api.base_request = session

    result = api.request("GET", "/users", status_code=200, params={"page": 1})

    assert result == {"code": 200, "data": {"name": "demo"}}
    assert session.calls[0][0] == "GET"
    assert session.calls[0][1] == "https://example.com/users"
    assert session.calls[0][2]["params"] == {"page": 1}


def test_request_can_return_raw_response():
    api = BaseAPI(base_url="https://example.com")
    api.base_request = DummySession()

    response = api.request("GET", "/users", return_response=True)

    assert isinstance(response, DummyResponse)


def test_get_value_reads_nested_data_and_raises_clear_assertion():
    api = BaseAPI(base_url="https://example.com")
    data = {"data": [{"fields": ["name"]}]}

    assert api.get_value(data, ["data", 0, "fields"]) == ["name"]

    with pytest.raises(AssertionError, match="不存在取值"):
        api.get_value(data, ["data", 1, "fields"])
