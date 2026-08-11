import conftest


class _Argument:
    _long_opts = ["--base-url"]


class _AnonymousParser:
    options = [_Argument()]


class _Parser:
    _anonymous = _AnonymousParser()


def test_option_registered_detects_plugin_owned_base_url_option():
    assert conftest._option_registered(_Parser(), "--base-url") is True
