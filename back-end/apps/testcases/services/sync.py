"""用例同步服务：解析 → upsert → 软删消失用例。"""
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from common.exceptions import BizError
from common.response import BizCode

from ..models import TestCaseSnapshot
from .parser import parse_directory


def sync_test_cases():
    """扫描 API_TEST_ROOT/test_case 并同步快照表，返回统计计数。"""
    case_root = Path(settings.API_TEST_ROOT) / "test_case"
    if not case_root.is_dir():
        raise BizError(BizCode.CASE_ROOT_INVALID, "用例根目录不存在或不可读")

    now = timezone.now()
    parsed = parse_directory(case_root, path_prefix="test_case")
    scanned = len(parsed)
    created = updated = 0
    seen_node_ids = []

    for item in parsed:
        node_id = item["node_id"]
        defaults = {k: v for k, v in item.items() if k != "node_id"}
        defaults["is_active"] = True
        defaults["synced_at"] = now
        _, is_created = TestCaseSnapshot.objects.update_or_create(
            node_id=node_id, defaults=defaults
        )
        seen_node_ids.append(node_id)
        if is_created:
            created += 1
        else:
            updated += 1

    # 本次未扫描到的、仍启用的用例 → 软删
    deactivated = (
        TestCaseSnapshot.objects.filter(is_active=True)
        .exclude(node_id__in=seen_node_ids)
        .update(is_active=False, synced_at=now)
    )

    return {
        "scanned": scanned,
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "synced_at": now.isoformat(),
    }
