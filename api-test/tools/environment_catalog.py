"""测试环境目录的解析、规范化和确定性序列化工具。"""

import hashlib
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

import yaml

import config


ENVIRONMENT_FIELDS = frozenset({"base_url", "url_name", "url_desc"})


class EnvironmentCatalogValidationError(ValueError):
    """环境目录校验失败，携带可供调用方展示的脱敏诊断。"""

    def __init__(self, code: str, message: str, *, field: str | None = None, **context):
        super().__init__(message)
        self.code = code
        self.diagnostic = {"code": code, "message": message}
        if field:
            self.diagnostic["field"] = field
        self.diagnostic.update(context)


class _DuplicateYamlKeyError(yaml.YAMLError):
    """保留 PyYAML 默认行为会丢失的重复 mapping key。"""


class _UniqueKeyLoader(yaml.SafeLoader):
    """在构造 mapping 时拒绝重复 key，避免被后一个条目静默覆盖。"""


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateYamlKeyError(f"duplicate yaml key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_yaml_catalog(path: Path) -> Mapping:
    """读取 YAML mapping，并把语法和重复 key 错误转换为稳定诊断。"""
    try:
        payload = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except FileNotFoundError as exc:
        raise EnvironmentCatalogValidationError(
            "environment_catalog_not_found", "环境目录文件不存在。"
        ) from exc
    except _DuplicateYamlKeyError as exc:
        raise EnvironmentCatalogValidationError(
            "duplicate_environment_key", "环境目录包含重复 env_key。"
        ) from exc
    except yaml.YAMLError as exc:
        raise EnvironmentCatalogValidationError("invalid_yaml", "环境目录 YAML 格式不合法。") from exc

    if payload is None or payload == {}:
        raise EnvironmentCatalogValidationError("empty_catalog", "环境目录不能为空。")
    if not isinstance(payload, Mapping):
        raise EnvironmentCatalogValidationError(
            "invalid_catalog_mapping", "环境目录顶层必须是 env_key mapping。"
        )
    return payload


def _normalize_environment_entry(env_key: str, entry: object) -> dict[str, str]:
    """校验单个环境配置，并返回不包含运行状态或敏感字段的规范化值。"""
    if not isinstance(entry, Mapping):
        raise EnvironmentCatalogValidationError(
            "invalid_environment_entry", "环境配置必须是 mapping。", field=env_key
        )

    fields = set(entry)
    unknown_fields = fields - ENVIRONMENT_FIELDS
    if unknown_fields:
        raise EnvironmentCatalogValidationError(
            "unknown_environment_field", "环境目录包含未允许字段。", field=sorted(unknown_fields)[0]
        )
    missing_fields = ENVIRONMENT_FIELDS - fields
    if missing_fields:
        raise EnvironmentCatalogValidationError(
            "missing_environment_field", "环境目录缺少必填字段。", field=sorted(missing_fields)[0]
        )

    normalized = {}
    for field_name in sorted(ENVIRONMENT_FIELDS):
        value = entry[field_name]
        if not isinstance(value, str) or not value.strip():
            raise EnvironmentCatalogValidationError(
                "empty_environment_field", "环境目录字段不能为空。", field=field_name
            )
        normalized[field_name] = value.strip()

    try:
        normalized["base_url"] = config.validate_base_url(normalized["base_url"])
    except ValueError as exc:
        raise EnvironmentCatalogValidationError(
            "invalid_base_url", "环境 base_url 必须包含协议和域名。", field="base_url"
        ) from exc

    parsed_url = urlparse(normalized["base_url"])
    if parsed_url.username is not None or parsed_url.password is not None:
        raise EnvironmentCatalogValidationError(
            "credentials_not_allowed", "环境 base_url 不能包含凭据。", field="base_url"
        )
    return normalized


def load_environment_catalog(path: str | Path) -> dict[str, dict[str, str]]:
    """解析版本化环境目录，规范化 URL 并确保 env_key 和 URL 均唯一。"""
    payload = _load_yaml_catalog(Path(path))
    catalog: dict[str, dict[str, str]] = {}
    seen_urls: set[str] = set()
    for raw_env_key, entry in payload.items():
        if not isinstance(raw_env_key, str) or not raw_env_key.strip():
            raise EnvironmentCatalogValidationError(
                "invalid_environment_key", "环境 env_key 必须是非空字符串。"
            )
        env_key = raw_env_key.strip()
        if env_key in catalog:
            raise EnvironmentCatalogValidationError(
                "duplicate_environment_key", "环境目录包含重复的规范化 env_key。", field=env_key
            )
        normalized = _normalize_environment_entry(env_key, entry)
        if normalized["base_url"] in seen_urls:
            raise EnvironmentCatalogValidationError(
                "duplicate_base_url", "环境目录包含重复的规范化 base_url。", field="base_url"
            )
        seen_urls.add(normalized["base_url"])
        catalog[env_key] = normalized

    return {env_key: catalog[env_key] for env_key in sorted(catalog)}


def dump_environment_catalog(catalog: Mapping[str, Mapping[str, str]]) -> str:
    """将已校验目录输出为 UTF-8、两空格缩进且排序稳定的 YAML 文本。"""
    normalized_catalog = {}
    seen_urls: set[str] = set()
    for raw_env_key in sorted(catalog):
        if not isinstance(raw_env_key, str) or not raw_env_key.strip():
            raise EnvironmentCatalogValidationError(
                "invalid_environment_key", "环境 env_key 必须是非空字符串。"
            )
        env_key = raw_env_key.strip()
        if env_key in normalized_catalog:
            raise EnvironmentCatalogValidationError(
                "duplicate_environment_key", "环境目录包含重复的规范化 env_key。", field=env_key
            )
        normalized_entry = _normalize_environment_entry(env_key, catalog[raw_env_key])
        if normalized_entry["base_url"] in seen_urls:
            raise EnvironmentCatalogValidationError(
                "duplicate_base_url", "环境目录包含重复的规范化 base_url。", field="base_url"
            )
        seen_urls.add(normalized_entry["base_url"])
        normalized_catalog[env_key] = normalized_entry

    serialized = yaml.safe_dump(
        normalized_catalog,
        allow_unicode=True,
        default_flow_style=False,
        indent=2,
        sort_keys=True,
    )
    return serialized if serialized.endswith("\n") else serialized + "\n"


def git_blob_sha(content: str | bytes) -> str:
    """计算 YAML 内容对应的 Git SHA-1 blob 标识，不依赖仓库 HEAD。"""
    payload = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha1(f"blob {len(payload)}\0".encode("utf-8") + payload).hexdigest()


def verify_yaml_blob_sha(content: str | bytes, expected_blob_sha: str) -> str:
    """比对 YAML Git blob SHA；不匹配时抛出供 Jenkins/后端消费的结构化诊断。"""
    observed_blob_sha = git_blob_sha(content)
    if observed_blob_sha != expected_blob_sha:
        raise EnvironmentCatalogValidationError(
            "yaml_blob_sha_conflict",
            "YAML Git blob SHA does not match the expected value.",
            expected_yaml_blob_sha=expected_blob_sha,
            observed_yaml_blob_sha=observed_blob_sha,
        )
    return observed_blob_sha
