import importlib.util
import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_ADDON_PATH = PROJECT_ROOT / ".claude" / "skills" / "api-test-common" / "capture" / "capture_addon.py"


class DummyLogger:
    def warn(self, _msg):
        pass

    def info(self, _msg):
        pass


class DummyRequest:
    def __init__(self, path, host="movie.douban.com", port=443):
        self.path = path
        self.host = host
        self.port = port
        self.method = "GET"
        self.scheme = "https"
        self.url = f"https://{host}{path}"
        self.headers = {}
        self.content = None

    def get_text(self, strict=False):
        return None


class DummyResponse:
    def __init__(self, status_code=200, content_type="application/json", body=b'{"code": 0}'):
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self.raw_content = body

    def get_text(self, strict=False):
        return self.raw_content.decode("utf-8")


class DummyFlow:
    def __init__(self, path, response=None):
        self.request = DummyRequest(path)
        self.response = response if response is not None else DummyResponse()


def load_capture_addon(monkeypatch):
    mitmproxy_module = types.ModuleType("mitmproxy")
    mitmproxy_module.ctx = types.SimpleNamespace(log=DummyLogger())
    mitmproxy_module.http = types.SimpleNamespace(HTTPFlow=object)
    monkeypatch.setitem(sys.modules, "mitmproxy", mitmproxy_module)

    spec = importlib.util.spec_from_file_location("capture_addon_for_test", CAPTURE_ADDON_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_empty_allowed_prefixes_disables_prefix_filter(monkeypatch, tmp_path):
    module = load_capture_addon(monkeypatch)
    prefix_file = tmp_path / "allowed_prefixes.txt"
    prefix_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(module, "PREFIX_FILE", str(prefix_file))

    assert module._load_prefixes() == []

    addon = object.__new__(module.ApiCaptureAddon)
    addon.baseurl = "https://movie.douban.com"
    addon.prefixes = []
    addon.blocked_prefixes = []

    assert addon._should_capture(DummyFlow("/subject/1292052/"))


def test_allowed_prefixes_file_filters_when_it_has_values(monkeypatch, tmp_path):
    module = load_capture_addon(monkeypatch)
    prefix_file = tmp_path / "allowed_prefixes.txt"
    prefix_file.write_text("# comment\n/api/\n/web/\n", encoding="utf-8")
    monkeypatch.setattr(module, "PREFIX_FILE", str(prefix_file))

    assert module._load_prefixes() == ["/api/", "/web/"]

    addon = object.__new__(module.ApiCaptureAddon)
    addon.baseurl = "https://movie.douban.com"
    addon.prefixes = ["/api/"]
    addon.blocked_prefixes = []

    assert addon._should_capture(DummyFlow("/api/demo"))
    assert not addon._should_capture(DummyFlow("/subject/1292052/"))


def test_static_suffix_is_still_filtered_without_prefix_filter(monkeypatch):
    module = load_capture_addon(monkeypatch)
    addon = object.__new__(module.ApiCaptureAddon)
    addon.baseurl = "https://movie.douban.com"
    addon.prefixes = []
    addon.blocked_prefixes = []

    assert not addon._should_capture(DummyFlow("/static/app.js"))


def test_empty_blocked_prefixes_disables_block_filter(monkeypatch, tmp_path):
    module = load_capture_addon(monkeypatch)
    blocked_file = tmp_path / "blocked_prefixes.txt"
    blocked_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(module, "BLOCKED_PREFIX_FILE", str(blocked_file))

    assert module._load_blocked_prefixes() == []

    addon = object.__new__(module.ApiCaptureAddon)
    addon.baseurl = "https://movie.douban.com"
    addon.prefixes = []
    addon.blocked_prefixes = []

    assert addon._should_capture(DummyFlow("/api/private/demo"))


def test_blocked_prefixes_file_filters_when_it_has_values(monkeypatch, tmp_path):
    module = load_capture_addon(monkeypatch)
    blocked_file = tmp_path / "blocked_prefixes.txt"
    blocked_file.write_text("# comment\n/api/private/\n/tracking/\n", encoding="utf-8")
    monkeypatch.setattr(module, "BLOCKED_PREFIX_FILE", str(blocked_file))

    assert module._load_blocked_prefixes() == ["/api/private/", "/tracking/"]

    addon = object.__new__(module.ApiCaptureAddon)
    addon.baseurl = "https://movie.douban.com"
    addon.prefixes = []
    addon.blocked_prefixes = ["/api/private/"]

    assert not addon._should_capture(DummyFlow("/api/private/demo"))
    assert addon._should_capture(DummyFlow("/api/public/demo"))


def test_allowed_prefixes_are_applied_before_blocked_prefixes(monkeypatch):
    module = load_capture_addon(monkeypatch)
    addon = object.__new__(module.ApiCaptureAddon)
    addon.baseurl = "https://movie.douban.com"
    addon.prefixes = ["/api/allowed/"]
    addon.blocked_prefixes = ["/api/allowed/private/", "/open/"]

    assert not addon._should_capture(DummyFlow("/open/demo"))
    assert not addon._should_capture(DummyFlow("/api/allowed/private/demo"))
    assert addon._should_capture(DummyFlow("/api/allowed/public/demo"))


def test_build_record_does_not_include_login_marker(monkeypatch):
    module = load_capture_addon(monkeypatch)
    addon = object.__new__(module.ApiCaptureAddon)

    record = addon._build_record(DummyFlow("/login"))

    assert "is_login" not in record
