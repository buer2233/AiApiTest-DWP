import json

import pytest

from tools.pytest_nodeids import load_lastfailed, normalize_nodeids, write_nodeids


def write_lastfailed(cache_dir, payload):
    cache_file = cache_dir / "v" / "cache" / "lastfailed"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return cache_file


def test_load_lastfailed_reads_pytest_cache_and_preserves_nodeids(tmp_path):
    cache_dir = tmp_path / ".pytest_cache"
    first = "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword"
    second = "test_case/test_demo_case/test_demo_api.py::TestDemoAPI::test_param[中文/abc]"
    write_lastfailed(cache_dir, {first: True, second: True})

    assert load_lastfailed(cache_dir) == [first, second]


def test_load_lastfailed_returns_empty_list_when_cache_missing(tmp_path):
    assert load_lastfailed(tmp_path / ".pytest_cache") == []


def test_load_lastfailed_raises_clear_error_when_cache_json_is_invalid(tmp_path):
    cache_dir = tmp_path / ".pytest_cache"
    cache_file = cache_dir / "v" / "cache" / "lastfailed"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{invalid-json", encoding="utf-8")

    with pytest.raises(ValueError, match="lastfailed"):
        load_lastfailed(cache_dir)


def test_normalize_nodeids_removes_empty_values_and_duplicates_without_rewriting_nodeids():
    nodeid = "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword"
    parametrized = "test_case/test_demo.py::TestDemo::test_param[a/b]"

    assert normalize_nodeids(["", f"  {nodeid}  ", nodeid, "\n", parametrized]) == [
        nodeid,
        parametrized,
    ]


def test_write_nodeids_creates_parent_dirs_and_writes_json_list(tmp_path):
    nodeids = [
        "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword",
        "test_case/test_demo.py::TestDemo::test_param[a/b]",
    ]
    output_path = tmp_path / "runtime" / "ci-runs" / "run-1" / "failed_nodeids.json"

    write_nodeids(nodeids, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == nodeids
