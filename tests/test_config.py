from urllib.parse import urlparse

import config


def test_base_url_is_required_and_contains_scheme():
    assert config.base_url
    parsed = urlparse(config.base_url)
    assert parsed.scheme in {"http", "https"}
    assert parsed.netloc


def test_website_name_defaults_to_base_url_domain():
    assert config.get_website_name() == urlparse(config.base_url).netloc


def test_runtime_capture_paths_are_under_runtime_dir():
    assert config.latest_capture_path.startswith(config.runtime_dir)
    assert config.capture_selection_path.startswith(config.runtime_dir)
    assert config.latest_capture_path.endswith("latest.jsonl")
    assert config.capture_selection_path.endswith("capture_selection.md")
