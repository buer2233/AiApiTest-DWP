#!/usr/bin/env python3
"""Jenkins 调用的薄入口；所有可测试逻辑位于 platform_bootstrap 包。"""

from platform_bootstrap.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
