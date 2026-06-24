#!/usr/bin/env python
"""Django 命令行入口。
本文件用于执行后端管理命令，例如迁移、创建用户、启动开发服务和运行系统检查。
"""

import os
import sys


def main():
    """执行 Django 管理命令。
    默认加载 `config.settings`，然后把命令行参数交给 Django 处理。
    """
    # 没有显式指定 settings 时，统一使用本项目的默认后端配置。
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
