import hashlib
from pathlib import Path

import pytest

from tools.environment_catalog import (
    EnvironmentCatalogValidationError,
    dump_environment_catalog,
    git_blob_sha,
    load_environment_catalog,
    verify_yaml_blob_sha,
)


API_TEST_ROOT = Path(__file__).resolve().parents[1]


def test_environment_catalog_normalizes_urls_and_serializes_deterministically(tmp_path):
    catalog_path = tmp_path / "package_environment.yaml"
    catalog_path.write_text(
        """
stage13-qa:
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
  base_url: https://stage13-qa.example.invalid/api/
alpha:
  base_url: https://alpha.example.invalid
  url_desc: Alpha 环境
  url_name: Alpha
""".lstrip(),
        encoding="utf-8",
    )

    catalog = load_environment_catalog(catalog_path)
    serialized_once = dump_environment_catalog(catalog)
    serialized_twice = dump_environment_catalog(catalog)

    assert catalog == {
        "alpha": {
            "base_url": "https://alpha.example.invalid",
            "url_name": "Alpha",
            "url_desc": "Alpha 环境",
        },
        "stage13-qa": {
            "base_url": "https://stage13-qa.example.invalid/api",
            "url_name": "Stage13 QA",
            "url_desc": "自动化回归测试环境",
        },
    }
    assert serialized_once == serialized_twice
    assert serialized_once.encode("utf-8").decode("utf-8") == serialized_once
    assert serialized_once == (
        "alpha:\n"
        "  base_url: https://alpha.example.invalid\n"
        "  url_desc: Alpha 环境\n"
        "  url_name: Alpha\n"
        "stage13-qa:\n"
        "  base_url: https://stage13-qa.example.invalid/api\n"
        "  url_desc: 自动化回归测试环境\n"
        "  url_name: Stage13 QA\n"
    )


def test_environment_catalog_git_blob_sha_uses_yaml_content_not_repository_head():
    yaml_content = "stage13-qa:\n  base_url: https://stage13-qa.example.invalid/api\n"
    expected = hashlib.sha1(
        f"blob {len(yaml_content.encode('utf-8'))}\0".encode("utf-8")
        + yaml_content.encode("utf-8")
    ).hexdigest()

    assert git_blob_sha(yaml_content) == expected


def test_verify_yaml_blob_sha_returns_observed_sha_when_expected_content_matches():
    yaml_content = "stage13-qa:\n  base_url: https://stage13-qa.example.invalid/api\n"

    observed_sha = verify_yaml_blob_sha(yaml_content, git_blob_sha(yaml_content))

    assert observed_sha == git_blob_sha(yaml_content)


def test_verify_yaml_blob_sha_reports_structured_conflict_without_repository_access():
    yaml_content = "stage13-qa:\n  base_url: https://stage13-qa.example.invalid/api\n"
    expected_sha = "0" * 40

    with pytest.raises(EnvironmentCatalogValidationError) as exc_info:
        verify_yaml_blob_sha(yaml_content, expected_sha)

    assert exc_info.value.code == "yaml_blob_sha_conflict"
    assert exc_info.value.diagnostic == {
        "code": "yaml_blob_sha_conflict",
        "message": "YAML Git blob SHA does not match the expected value.",
        "expected_yaml_blob_sha": expected_sha,
        "observed_yaml_blob_sha": git_blob_sha(yaml_content),
    }


def test_versioned_package_environment_catalog_is_valid():
    catalog = load_environment_catalog(API_TEST_ROOT / "utils" / "package_environment.yaml")

    assert catalog


@pytest.mark.parametrize(
    ("yaml_content", "error_code"),
    [
        ("", "empty_catalog"),
        (
            """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
  secret_hint: forbidden
""".lstrip(),
            "unknown_environment_field",
        ),
        (
            """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
stage13-copy:
  base_url: https://stage13-qa.example.invalid/api/
  url_name: Stage13 Copy
  url_desc: 重复 URL
""".lstrip(),
            "duplicate_base_url",
        ),
        (
            """
stage13-qa:
  base_url: stage13-qa.example.invalid
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
""".lstrip(),
            "invalid_base_url",
        ),
        (
            """
stage13-qa:
  base_url: https://user:password@stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
""".lstrip(),
            "credentials_not_allowed",
        ),
        (
            """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: ''
  url_desc: 自动化回归测试环境
""".lstrip(),
            "empty_environment_field",
        ),
        (
            """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
""".lstrip(),
            "missing_environment_field",
        ),
        (
            """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
stage13-qa:
  base_url: https://stage13-other.example.invalid/api
  url_name: Stage13 Other
  url_desc: 重复 key
""".lstrip(),
            "duplicate_environment_key",
        ),
        (
            """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
' stage13-qa ':
  base_url: https://stage13-other.example.invalid/api
  url_name: Stage13 Other
  url_desc: 去空白后重复 key
""".lstrip(),
            "duplicate_environment_key",
        ),
        ("- not-a-mapping\n", "invalid_catalog_mapping"),
    ],
)
def test_environment_catalog_rejects_invalid_schema_and_urls(tmp_path, yaml_content, error_code):
    catalog_path = tmp_path / "package_environment.yaml"
    catalog_path.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(EnvironmentCatalogValidationError) as exc_info:
        load_environment_catalog(catalog_path)

    assert exc_info.value.code == error_code
    assert catalog_path.read_text(encoding="utf-8") == yaml_content


def test_environment_catalog_dump_rejects_normalized_key_and_url_collisions():
    valid_entry = {
        "base_url": "https://stage13-qa.example.invalid/api",
        "url_name": "Stage13 QA",
        "url_desc": "自动化回归测试环境",
    }

    with pytest.raises(EnvironmentCatalogValidationError) as key_error:
        dump_environment_catalog(
            {
                "stage13-qa": valid_entry,
                " stage13-qa ": {
                    **valid_entry,
                    "base_url": "https://stage13-other.example.invalid/api",
                },
            }
        )
    with pytest.raises(EnvironmentCatalogValidationError) as url_error:
        dump_environment_catalog(
            {
                "stage13-qa": valid_entry,
                "stage13-copy": {**valid_entry, "base_url": valid_entry["base_url"] + "/"},
            }
        )

    assert key_error.value.code == "duplicate_environment_key"
    assert url_error.value.code == "duplicate_base_url"
