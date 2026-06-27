#!/usr/bin/env python
"""Django 命令行入口。默认使用 config.settings.base（生产/开发配置走环境变量）。"""
import os
import sys


def main():
    # 默认配置模块；测试由 pytest.ini 指定 config.settings.test
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django，请确认已安装依赖并激活虚拟环境。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
