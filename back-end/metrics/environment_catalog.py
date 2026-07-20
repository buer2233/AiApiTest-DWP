"""Stage13 测试环境目录的数据库投影与同步状态机服务。"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from django.db import DataError, IntegrityError, transaction
from django.utils import timezone

from metrics.models import (
    EnvironmentCatalogState,
    EnvironmentCatalogSyncAttempt,
    TestEnvironment,
    normalize_environment_base_url,
)


CATALOG_KEY = EnvironmentCatalogState.CATALOG_KEY
CATALOG_FIELDS = frozenset({"base_url", "url_name", "url_desc"})
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ENV_KEY_MAX_LENGTH = TestEnvironment._meta.get_field("env_key").max_length
_ENV_NAME_MAX_LENGTH = TestEnvironment._meta.get_field("env_name").max_length
_BASE_URL_MAX_LENGTH = TestEnvironment._meta.get_field("base_url").max_length


class EnvironmentCatalogError(RuntimeError):
    """服务层可安全暴露给 API 的目录错误基类。"""

    code = "environment_catalog_error"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code


class EnvironmentCatalogValidationError(EnvironmentCatalogError):
    code = "validation_error"


class EnvironmentCatalogBusyError(EnvironmentCatalogError):
    code = "environment_config_sync_busy"


class EnvironmentCatalogDuplicateError(EnvironmentCatalogError):
    code = "duplicate_environment"


class EnvironmentCatalogStateError(EnvironmentCatalogError):
    code = "invalid_sync_state"


class EnvironmentCatalogSyncNotRetryableError(EnvironmentCatalogError):
    code = "sync_not_retryable"


@dataclass(frozen=True)
class CatalogImportResult:
    created_count: int
    updated_count: int
    deactivated_count: int


def _payload_sha256(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def git_blob_sha(content: bytes) -> str:
    """计算 Git blob SHA，确保状态记录的是文件而非仓库 HEAD。"""
    return hashlib.sha1(f"blob {len(content)}\0".encode("utf-8") + content).hexdigest()


def _validate_git_sha(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _GIT_SHA_PATTERN.fullmatch(value):
        raise EnvironmentCatalogValidationError(
            f"{field_name} 必须是 40 位小写十六进制 Git SHA。",
            code=f"invalid_{field_name}",
        )
    return value


class _DuplicateYamlKeyError(yaml.YAMLError):
    """避免 PyYAML 静默使用最后一个重复 key。"""


class _UniqueKeyLoader(yaml.SafeLoader):
    """严格加载镜像内的静态初始化目录。"""


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateYamlKeyError(f"duplicate yaml key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def normalize_catalog(catalog: Mapping[str, object]) -> dict[str, dict[str, str]]:
    """验证 Jenkins 回调的结构化目录；本服务不读取运行时工作区。"""
    if not isinstance(catalog, Mapping) or not catalog:
        raise EnvironmentCatalogValidationError("环境目录必须是非空 mapping。", code="empty_catalog")

    normalized: dict[str, dict[str, str]] = {}
    seen_urls: set[str] = set()
    for raw_env_key, raw_entry in catalog.items():
        if not isinstance(raw_env_key, str) or not raw_env_key.strip():
            raise EnvironmentCatalogValidationError("环境 env_key 必须是非空字符串。", code="invalid_environment_key")
        env_key = raw_env_key.strip()
        if len(env_key) > _ENV_KEY_MAX_LENGTH:
            raise EnvironmentCatalogValidationError("环境 env_key 长度超过限制。", code="environment_key_too_long")
        if env_key in normalized:
            raise EnvironmentCatalogValidationError("环境目录包含重复 env_key。", code="duplicate_environment_key")
        if not isinstance(raw_entry, Mapping):
            raise EnvironmentCatalogValidationError("环境配置必须是 mapping。", code="invalid_environment_entry")

        fields = set(raw_entry)
        if fields - CATALOG_FIELDS:
            raise EnvironmentCatalogValidationError("环境目录包含未允许字段。", code="unknown_environment_field")
        if CATALOG_FIELDS - fields:
            raise EnvironmentCatalogValidationError("环境目录缺少必填字段。", code="missing_environment_field")

        entry: dict[str, str] = {}
        for field_name in sorted(CATALOG_FIELDS):
            value = raw_entry[field_name]
            if not isinstance(value, str) or not value.strip():
                raise EnvironmentCatalogValidationError("环境目录字段不能为空。", code="empty_environment_field")
            entry[field_name] = value.strip()
        if len(entry["url_name"]) > _ENV_NAME_MAX_LENGTH:
            raise EnvironmentCatalogValidationError("环境 url_name 长度超过限制。", code="environment_name_too_long")
        try:
            entry["base_url"] = normalize_environment_base_url(entry["base_url"])
        except ValueError as exc:
            raise EnvironmentCatalogValidationError(str(exc), code="invalid_base_url") from exc
        if len(entry["base_url"]) > _BASE_URL_MAX_LENGTH:
            raise EnvironmentCatalogValidationError("环境 base_url 长度超过限制。", code="environment_base_url_too_long")
        if entry["base_url"] in seen_urls:
            raise EnvironmentCatalogValidationError("环境目录包含重复 base_url。", code="duplicate_base_url")
        seen_urls.add(entry["base_url"])
        normalized[env_key] = entry

    return {env_key: normalized[env_key] for env_key in sorted(normalized)}


def load_image_catalog(source_path: Path) -> dict[str, dict[str, str]]:
    """只供首次初始化读取随镜像复制的 YAML，失败不触碰数据库。"""
    try:
        raw_catalog = yaml.load(source_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except FileNotFoundError as exc:
        raise EnvironmentCatalogValidationError("镜像内环境目录文件不存在。", code="environment_catalog_not_found") from exc
    except (_DuplicateYamlKeyError, yaml.YAMLError) as exc:
        raise EnvironmentCatalogValidationError("镜像内环境目录 YAML 格式不合法。", code="invalid_yaml") from exc
    return normalize_catalog(raw_catalog)


def _locked_state() -> EnvironmentCatalogState:
    EnvironmentCatalogState.objects.get_or_create(catalog_key=CATALOG_KEY)
    return EnvironmentCatalogState.objects.select_for_update().get(catalog_key=CATALOG_KEY)


def _ensure_no_active_attempt() -> None:
    if EnvironmentCatalogSyncAttempt.objects.filter(status__in=EnvironmentCatalogSyncAttempt.ACTIVE_STATUSES).exists():
        raise EnvironmentCatalogBusyError("已有活动的环境配置同步请求。")


def _active_catalog_payload() -> dict[str, dict[str, str]]:
    payload = {
        environment.env_key: {
            "base_url": environment.base_url,
            "url_name": environment.env_name,
            "url_desc": environment.url_desc,
        }
        for environment in TestEnvironment.objects.filter(is_active=True).order_by("env_key", "id")
    }
    return normalize_catalog(payload)


def _ensure_active_environment_remains(environment: TestEnvironment, *, is_active: bool) -> None:
    """环境目录必须保留至少一个启用项，避免生成不合法的空 YAML。"""
    if environment.is_active and not is_active and not TestEnvironment.objects.filter(is_active=True).exclude(
        pk=environment.pk
    ).exists():
        raise EnvironmentCatalogValidationError(
            "至少保留一个启用测试环境。",
            code="last_active_environment",
        )


def _create_attempt_locked(
    *,
    state: EnvironmentCatalogState,
    direction: str,
    payload: dict[str, object],
    requested_by=None,
    expected_yaml_blob_sha: str | None = None,
) -> EnvironmentCatalogSyncAttempt:
    _ensure_no_active_attempt()
    expected_sha = expected_yaml_blob_sha if expected_yaml_blob_sha is not None else state.yaml_blob_sha
    _validate_git_sha(expected_sha, field_name="expected_yaml_blob_sha")
    attempt = EnvironmentCatalogSyncAttempt(
        direction=direction,
        expected_yaml_blob_sha=expected_sha,
        payload_json=payload,
        payload_sha256=_payload_sha256(payload),
        requested_by=requested_by,
    )
    try:
        attempt.save()
    except IntegrityError as exc:
        raise EnvironmentCatalogBusyError("已有活动的环境配置同步请求。") from exc
    state.status = EnvironmentCatalogState.Status.PENDING
    state.last_error_code = ""
    state.last_error_summary = ""
    state.save()
    return attempt


def create_mysql_to_yaml_sync_attempt(*, requested_by=None) -> EnvironmentCatalogSyncAttempt:
    """冻结当前启用环境快照，并原子创建 MySQL 写回 YAML 请求。"""
    with transaction.atomic():
        state = _locked_state()
        return _create_attempt_locked(
            state=state,
            direction=EnvironmentCatalogSyncAttempt.Direction.MYSQL_TO_YAML,
            payload=_active_catalog_payload(),
            requested_by=requested_by,
        )


def create_yaml_to_mysql_sync_attempt(*, requested_by=None) -> EnvironmentCatalogSyncAttempt:
    """创建受 Jenkins 隔离 checkout 执行的 YAML 导入请求。"""
    with transaction.atomic():
        state = _locked_state()
        return _create_attempt_locked(
            state=state,
            direction=EnvironmentCatalogSyncAttempt.Direction.YAML_TO_MYSQL,
            payload={},
            requested_by=requested_by,
        )


def create_environment_with_sync(*, env_key: str, url_name: str, base_url: str, url_desc: str, requested_by=None):
    """平台 CRUD 的创建入口：环境记录与同步请求必须同一事务提交。"""
    catalog = normalize_catalog(
        {env_key: {"base_url": base_url, "url_name": url_name, "url_desc": url_desc}}
    )
    normalized_key, entry = next(iter(catalog.items()))
    with transaction.atomic():
        state = _locked_state()
        _ensure_no_active_attempt()
        if TestEnvironment.objects.filter(env_key=normalized_key).exists() or TestEnvironment.objects.filter(
            base_url=entry["base_url"]
        ).exists():
            raise EnvironmentCatalogDuplicateError("环境 key 或 base_url 已存在。")
        environment = TestEnvironment.objects.create(
            env_key=normalized_key,
            env_name=entry["url_name"],
            base_url=entry["base_url"],
            url_desc=entry["url_desc"],
            is_active=True,
        )
        attempt = _create_attempt_locked(
            state=state,
            direction=EnvironmentCatalogSyncAttempt.Direction.MYSQL_TO_YAML,
            payload=_active_catalog_payload(),
            requested_by=requested_by,
        )
    return environment, attempt


def update_environment_with_sync(
    environment: TestEnvironment,
    *,
    url_name: str,
    base_url: str,
    url_desc: str,
    is_active: bool,
    requested_by=None,
):
    """编辑既有环境的可变字段；env_key 不参与输入，因此创建后不可改名。"""
    catalog = normalize_catalog(
        {environment.env_key: {"base_url": base_url, "url_name": url_name, "url_desc": url_desc}}
    )
    _, entry = next(iter(catalog.items()))
    if not isinstance(is_active, bool):
        raise EnvironmentCatalogValidationError("环境 is_active 必须是布尔值。", code="invalid_is_active")
    with transaction.atomic():
        state = _locked_state()
        _ensure_no_active_attempt()
        locked_environment = TestEnvironment.objects.select_for_update().get(pk=environment.pk)
        _ensure_active_environment_remains(locked_environment, is_active=is_active)
        if TestEnvironment.objects.exclude(pk=locked_environment.pk).filter(base_url=entry["base_url"]).exists():
            raise EnvironmentCatalogDuplicateError("环境 base_url 已存在。")
        locked_environment.env_name = entry["url_name"]
        locked_environment.base_url = entry["base_url"]
        locked_environment.url_desc = entry["url_desc"]
        locked_environment.is_active = is_active
        locked_environment.save()
        attempt = _create_attempt_locked(
            state=state,
            direction=EnvironmentCatalogSyncAttempt.Direction.MYSQL_TO_YAML,
            payload=_active_catalog_payload(),
            requested_by=requested_by,
        )
    return locked_environment, attempt


def set_environment_active_with_sync(
    environment: TestEnvironment,
    *,
    is_active: bool,
    requested_by=None,
):
    """逻辑停用或恢复环境，并创建新的 YAML 写回请求。"""
    if not isinstance(is_active, bool):
        raise EnvironmentCatalogValidationError("环境 is_active 必须是布尔值。", code="invalid_is_active")
    with transaction.atomic():
        state = _locked_state()
        _ensure_no_active_attempt()
        locked_environment = TestEnvironment.objects.select_for_update().get(pk=environment.pk)
        _ensure_active_environment_remains(locked_environment, is_active=is_active)
        locked_environment.is_active = is_active
        locked_environment.save()
        attempt = _create_attempt_locked(
            state=state,
            direction=EnvironmentCatalogSyncAttempt.Direction.MYSQL_TO_YAML,
            payload=_active_catalog_payload(),
            requested_by=requested_by,
        )
    return locked_environment, attempt


def apply_yaml_catalog_import(catalog: Mapping[str, object]) -> CatalogImportResult:
    """把已从隔离 checkout 解析的目录一次性投影到数据库。"""
    normalized_catalog = normalize_catalog(catalog)
    with transaction.atomic():
        return _apply_normalized_catalog(normalized_catalog)


def _apply_normalized_catalog(normalized_catalog: Mapping[str, Mapping[str, str]]) -> CatalogImportResult:
    existing_by_key = {
        environment.env_key: environment
        for environment in TestEnvironment.objects.select_for_update().all()
    }
    existing_by_base_url = {
        environment.base_url: environment
        for environment in existing_by_key.values()
    }
    for env_key, entry in normalized_catalog.items():
        url_owner = existing_by_base_url.get(entry["base_url"])
        if url_owner is not None and url_owner.env_key not in normalized_catalog:
            raise EnvironmentCatalogValidationError(
                "环境目录不能复用未包含环境的 base_url。",
                code="existing_base_url_conflict",
            )

    reserved_urls = set(existing_by_base_url) | {
        entry["base_url"]
        for entry in normalized_catalog.values()
    }
    # 先临时腾空所有会变更的唯一 URL，支持环境之间交换或循环迁移地址。
    for env_key, entry in normalized_catalog.items():
        environment = existing_by_key.get(env_key)
        if environment is None or environment.base_url == entry["base_url"]:
            continue
        temporary_url = f"https://environment-catalog-tmp-{uuid.uuid4().hex}.invalid"
        while temporary_url in reserved_urls:
            temporary_url = f"https://environment-catalog-tmp-{uuid.uuid4().hex}.invalid"
        reserved_urls.add(temporary_url)
        environment.base_url = temporary_url
        environment.save(update_fields=["base_url"])

    created_count = 0
    updated_count = 0
    for env_key, entry in normalized_catalog.items():
        environment = existing_by_key.get(env_key)
        if environment is None:
            TestEnvironment.objects.create(
                env_key=env_key,
                env_name=entry["url_name"],
                base_url=entry["base_url"],
                url_desc=entry["url_desc"],
                is_active=True,
            )
            created_count += 1
            continue
        environment.env_name = entry["url_name"]
        environment.base_url = entry["base_url"]
        environment.url_desc = entry["url_desc"]
        environment.is_active = True
        environment.save()
        updated_count += 1

    deactivated_count = TestEnvironment.objects.filter(is_active=True).exclude(
        env_key__in=normalized_catalog
    ).update(is_active=False, updated_at=timezone.now())
    return CatalogImportResult(
        created_count=created_count,
        updated_count=updated_count,
        deactivated_count=deactivated_count,
    )


def mark_sync_attempt_queued(attempt: EnvironmentCatalogSyncAttempt, *, queue_id: str) -> EnvironmentCatalogSyncAttempt:
    with transaction.atomic():
        locked_attempt = EnvironmentCatalogSyncAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked_attempt.status != locked_attempt.Status.PENDING:
            raise EnvironmentCatalogStateError("同步请求不能进入 queued 状态。")
        locked_attempt.status = locked_attempt.Status.QUEUED
        locked_attempt.queue_id = queue_id
        locked_attempt.save()
        state = _locked_state()
        state.status = EnvironmentCatalogState.Status.QUEUED
        state.save()
    return locked_attempt


def mark_sync_attempt_running(
    attempt: EnvironmentCatalogSyncAttempt,
    *,
    build_number: int | None = None,
    jenkins_build_url: str = "",
) -> EnvironmentCatalogSyncAttempt:
    with transaction.atomic():
        locked_attempt = EnvironmentCatalogSyncAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked_attempt.status not in {locked_attempt.Status.PENDING, locked_attempt.Status.QUEUED}:
            raise EnvironmentCatalogStateError("同步请求不能进入 running 状态。")
        # 远端已受理但 queued 持久化及补偿都失败时，受控内部回调可从 pending 继续。
        locked_attempt.status = locked_attempt.Status.RUNNING
        locked_attempt.build_number = build_number
        locked_attempt.jenkins_build_url = jenkins_build_url
        locked_attempt.save()
        state = _locked_state()
        state.status = EnvironmentCatalogState.Status.RUNNING
        state.save()
    return locked_attempt


def _require_running(attempt: EnvironmentCatalogSyncAttempt) -> None:
    if attempt.status != attempt.Status.RUNNING:
        raise EnvironmentCatalogStateError("同步回调只允许处理 running 请求。")


def _mark_attempt_failed_locked(
    locked_attempt: EnvironmentCatalogSyncAttempt,
    *,
    error_code: str,
    error_summary: str,
) -> EnvironmentCatalogSyncAttempt:
    """在调用方的原子事务内持久化失败状态并释放活动请求键。"""
    locked_attempt.status = locked_attempt.Status.FAILED
    locked_attempt.error_code = error_code
    locked_attempt.error_summary = error_summary
    locked_attempt.finished_at = timezone.now()
    locked_attempt.save()
    state = _locked_state()
    state.status = EnvironmentCatalogState.Status.FAILED
    state.last_error_code = error_code
    state.last_error_summary = error_summary
    state.save()
    return locked_attempt


def _mark_callback_parameter_validation_failed_locked(
    locked_attempt: EnvironmentCatalogSyncAttempt,
    validation_error: EnvironmentCatalogValidationError,
) -> EnvironmentCatalogSyncAttempt:
    """回调参数错误使用固定摘要落库，避免把原始输入写入审计记录。"""
    return _mark_attempt_failed_locked(
        locked_attempt,
        error_code=validation_error.code,
        error_summary="同步回调参数校验失败，请修正后重试。",
    )


def complete_mysql_to_yaml_sync_attempt(
    attempt: EnvironmentCatalogSyncAttempt,
    *,
    observed_yaml_blob_sha: str,
    written_yaml_blob_sha: str,
    commit_sha: str,
) -> EnvironmentCatalogSyncAttempt:
    """处理 Jenkins 写回回调；冲突绝不覆盖状态中原有 YAML SHA。"""
    callback_error: EnvironmentCatalogValidationError | None = None
    with transaction.atomic():
        locked_attempt = EnvironmentCatalogSyncAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked_attempt.direction != locked_attempt.Direction.MYSQL_TO_YAML:
            raise EnvironmentCatalogStateError("同步请求方向与写回回调不一致。")
        if locked_attempt.status == locked_attempt.Status.SYNCED:
            return locked_attempt
        _require_running(locked_attempt)
        try:
            observed_sha = _validate_git_sha(observed_yaml_blob_sha, field_name="observed_yaml_blob_sha")
            written_sha = _validate_git_sha(written_yaml_blob_sha, field_name="written_yaml_blob_sha")
            resolved_commit_sha = _validate_git_sha(commit_sha, field_name="commit_sha")
        except EnvironmentCatalogValidationError as exc:
            _mark_callback_parameter_validation_failed_locked(locked_attempt, exc)
            callback_error = exc
        else:
            state = _locked_state()
            locked_attempt.observed_yaml_blob_sha = observed_sha
            locked_attempt.finished_at = timezone.now()
            if observed_sha != locked_attempt.expected_yaml_blob_sha:
                locked_attempt.status = locked_attempt.Status.CONFLICT
                locked_attempt.error_code = "yaml_blob_sha_conflict"
                locked_attempt.error_summary = "当前 YAML blob SHA 与请求冻结值不一致。"
                locked_attempt.save()
                state.status = EnvironmentCatalogState.Status.CONFLICT
                state.last_error_code = locked_attempt.error_code
                state.last_error_summary = locked_attempt.error_summary
                state.save()
                return locked_attempt

            locked_attempt.status = locked_attempt.Status.SYNCED
            locked_attempt.commit_sha = resolved_commit_sha
            locked_attempt.save()
            state.status = EnvironmentCatalogState.Status.SYNCED
            state.yaml_blob_sha = written_sha
            state.last_commit_sha = resolved_commit_sha
            state.last_synced_at = locked_attempt.finished_at
            state.last_error_code = ""
            state.last_error_summary = ""
            state.save()
    if callback_error is not None:
        raise callback_error
    return locked_attempt


def complete_yaml_to_mysql_sync_attempt(
    attempt: EnvironmentCatalogSyncAttempt,
    *,
    catalog: Mapping[str, object],
    observed_yaml_blob_sha: str,
    commit_sha: object = "",
) -> tuple[EnvironmentCatalogSyncAttempt, CatalogImportResult]:
    """处理 YAML 导入回调，目录校验失败需同步落库为 failed。"""
    callback_error: EnvironmentCatalogError | None = None
    with transaction.atomic():
        locked_attempt = EnvironmentCatalogSyncAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked_attempt.direction != locked_attempt.Direction.YAML_TO_MYSQL:
            raise EnvironmentCatalogStateError("同步请求方向与导入回调不一致。")
        if locked_attempt.status == locked_attempt.Status.SYNCED:
            return locked_attempt, CatalogImportResult(0, 0, 0)
        _require_running(locked_attempt)
        try:
            observed_sha = _validate_git_sha(observed_yaml_blob_sha, field_name="observed_yaml_blob_sha")
            resolved_commit_sha = (
                ""
                if type(commit_sha) is str and commit_sha == ""
                else _validate_git_sha(commit_sha, field_name="commit_sha")
            )
        except EnvironmentCatalogValidationError as exc:
            _mark_callback_parameter_validation_failed_locked(locked_attempt, exc)
            callback_error = exc
        else:
            try:
                normalized_catalog = normalize_catalog(catalog)
            except EnvironmentCatalogValidationError as exc:
                _mark_attempt_failed_locked(
                    locked_attempt,
                    error_code=exc.code,
                    error_summary="环境目录校验失败，请修正配置后重试。",
                )
                callback_error = exc
            else:
                try:
                    with transaction.atomic():
                        result = _apply_normalized_catalog(normalized_catalog)
                except EnvironmentCatalogValidationError as exc:
                    _mark_attempt_failed_locked(
                        locked_attempt,
                        error_code=exc.code,
                        error_summary="环境目录校验失败，请修正配置后重试。",
                    )
                    callback_error = exc
                except (DataError, IntegrityError):
                    callback_error = EnvironmentCatalogError(
                        "环境目录投影失败，请修正后重试。",
                        code="environment_catalog_projection_failed",
                    )
                    _mark_attempt_failed_locked(
                        locked_attempt,
                        error_code=callback_error.code,
                        error_summary="环境目录投影失败，请修正后重试。",
                    )
                else:
                    locked_attempt.status = locked_attempt.Status.SYNCED
                    locked_attempt.observed_yaml_blob_sha = observed_sha
                    locked_attempt.commit_sha = resolved_commit_sha
                    locked_attempt.finished_at = timezone.now()
                    locked_attempt.save()
                    state = _locked_state()
                    state.status = EnvironmentCatalogState.Status.SYNCED
                    state.yaml_blob_sha = observed_sha
                    state.last_commit_sha = resolved_commit_sha
                    state.last_synced_at = locked_attempt.finished_at
                    state.last_error_code = ""
                    state.last_error_summary = ""
                    state.save()
                    return locked_attempt, result
    if callback_error is not None:
        raise callback_error
    raise RuntimeError("环境目录导入回调未产生结果。")


def fail_sync_attempt(
    attempt: EnvironmentCatalogSyncAttempt,
    *,
    error_code: str,
    error_summary: str,
) -> EnvironmentCatalogSyncAttempt:
    """记录外部 Jenkins/YAML/Git 失败，不回滚已提交的平台 CRUD。"""
    with transaction.atomic():
        locked_attempt = EnvironmentCatalogSyncAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked_attempt.status == locked_attempt.Status.FAILED:
            return locked_attempt
        if locked_attempt.status not in locked_attempt.ACTIVE_STATUSES:
            raise EnvironmentCatalogStateError("终态同步请求不能标记为 failed。")
        _mark_attempt_failed_locked(
            locked_attempt,
            error_code=error_code,
            error_summary=error_summary,
        )
    return locked_attempt


def retry_sync_attempt(attempt: EnvironmentCatalogSyncAttempt, *, requested_by=None) -> EnvironmentCatalogSyncAttempt:
    """失败请求以新的不可变审计记录重试；冲突需先导入或重新编辑。"""
    with transaction.atomic():
        original = EnvironmentCatalogSyncAttempt.objects.select_for_update().get(pk=attempt.pk)
        if original.status != original.Status.FAILED:
            raise EnvironmentCatalogSyncNotRetryableError("只有 failed 同步请求可以直接重试。")
        state = _locked_state()
        return _create_attempt_locked(
            state=state,
            direction=original.direction,
            payload=original.payload_json,
            requested_by=requested_by if requested_by is not None else original.requested_by,
            expected_yaml_blob_sha=original.expected_yaml_blob_sha,
        )


def initialize_environment_catalog_from_image(source_path: Path) -> bool:
    """首次部署初始化一次镜像内目录；后续运行时 YAML 变更必须经 Jenkins 导入。"""
    with transaction.atomic():
        # 旧库只要已有任意环境即保持平台投影原状，不补状态、不覆盖目录。
        if TestEnvironment.objects.exists():
            return False
        state = _locked_state()
        if state.yaml_blob_sha:
            return False
        source_bytes = source_path.read_bytes()
        catalog = load_image_catalog(source_path)
        _apply_normalized_catalog(catalog)
        state.yaml_blob_sha = git_blob_sha(source_bytes)
        state.status = EnvironmentCatalogState.Status.SYNCED
        state.last_synced_at = timezone.now()
        state.last_error_code = ""
        state.last_error_summary = ""
        state.save()
    return True
