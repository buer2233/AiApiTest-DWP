from requests import Request
from requests.models import Response

from utils.timeout_http_adapter import TimeoutHTTPAdapter


def test_safe_body_redacts_sensitive_form_fields():
    request = Request(
        "POST",
        "https://example.invalid/login",
        data={"loginid": "sysadmin", "userpassword": "secret-password", "password": "secret-password"},
    ).prepare()

    safe_body = TimeoutHTTPAdapter._safe_body(request)

    assert "secret-password" not in safe_body
    assert "userpassword=%5BREDACTED%5D" in safe_body
    assert "password=%5BREDACTED%5D" in safe_body


def test_exception_diagnostics_redact_sensitive_response_headers_and_body():
    response = Response()
    response.status_code = 401
    response.headers["Set-Cookie"] = "authToken=secret-cookie"
    response.headers["X-Trace-Id"] = "trace-1"
    response._content = b'{"user_token":"secret-token","message":"invalid credentials"}'

    safe_headers = TimeoutHTTPAdapter._safe_headers(response.headers)
    safe_text = TimeoutHTTPAdapter._safe_response_text(response)

    assert safe_headers["Set-Cookie"] == "[REDACTED]"
    assert safe_headers["X-Trace-Id"] == "trace-1"
    assert "secret-cookie" not in str(safe_headers)
    assert "secret-token" not in safe_text
    assert "invalid credentials" in safe_text
