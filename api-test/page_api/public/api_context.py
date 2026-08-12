# -*- coding: utf-8 -*-
"""API 上下文模块。

提供 APIContext 类，作为所有模块接口的统一入口。
它包装已登录的 requests.Session，通过命名空间（约定命名自动加载）
让用例直接用 login_admin.{模块名}.{方法}() 调用任意模块的接口，
无需手动 import 或实例化。
"""

import os

from page_api.public.base_api import BaseAPI


class APIContext:
    """登录态共享的 API 上下文，作为所有模块接口的统一入口。

    核心职责：
        1. 持有已登录的 requests.Session（从 LoginAPI 实例提取）
        2. 通过命名空间属性自动加载任意 API 模块，注入 Session
        3. 通过 .login 属性保留对原始 LoginAPI 实例的访问

    命名空间自动加载规则：
        访问 login_admin.{模块名} 时，按两级策略查找：

        1. 主模块：page_api/{name}_api/{name}_api.py → {Name}API
        2. 子模块（回退）：扫描所有 page_api/*_api/ 目录，
           查找 {name}_api.py 子模块文件 → {Name}API

        例如：
            login_admin.portal   → page_api/portal_api/portal_api.py → PortalAPI
            login_admin.reqlist  → page_api/workflow_api/reqlist_api.py → ReqlistAPI（子模块）
            login_admin.login    → 已预加载的 LoginAPI 实例

        新增模块时零配置——只要按规范创建目录和文件，命名空间自动生效。

    为什么需要 APIContext？
        BaseAPI 每个实例默认独立创建 requests.Session，各实例之间
        Cookie 不共享。即使 login_admin fixture 已完成登录，新建
        AnnounceAPI() 实例也会得到一个空 Session，等于没登录。

        APIContext 提取已登录的 Session，通过命名空间自动加载
        任意模块并注入 Session，实现跨模块登录态透传。

    用法:
        def test_something(login_admin):
            # 登录模块（.login 预加载）
            login_admin.login.get_os_info()

            # 公告模块（首次访问自动加载并缓存）
            login_admin.announce.get_announce_list()

            # 子模块（放在 workflow_api/ 下的 reqlist_api.py）
            login_admin.reqlist.get_doing_base_info()
    """

    def __init__(self, login_api, caller=None):
        """初始化 API 上下文。

        Args:
            login_api: 已完成登录的 LoginAPI 实例。
                       其内部 Session 包含登录 Cookie。
            caller: 调用人标识（如 'sysadmin'），用于日志追踪。
        """
        # 提取已登录的 Session 和 base_url，供后续命名空间加载复用。
        self._session = login_api.get_base_request()
        self._base_url = login_api.base_url
        # 保留 LoginAPI 实例，方便用例直接调用登录相关方法。
        self.login = login_api
        # 调用人标识，透传给所有通过 .use() 创建的 API 实例。
        self._caller = caller or getattr(login_api, '_caller', 'unknown')
        # 命名空间实例缓存：首次访问时加载，后续命中缓存。
        self._cache = {}

    def __getattr__(self, name):
        """命名空间自动加载：按约定命名查找并实例化 API 模块。

        查找策略：
            1. 主模块：page_api/{name}_api/{name}_api.py → {Name}API
            2. 子模块：扫描所有 page_api/*_api/ 目录，
               查找 {name}_api.py 子模块文件 → {Name}API

        首次访问时导入模块、实例化并注入 Session，后续访问命中缓存。

        Args:
            name: 模块短名，如 'portal'、'reqlist'。

        Returns:
            BaseAPI 子类实例，已共享登录 Session。

        Raises:
            AttributeError: 模块不存在或类名不匹配时，给出明确的修复指引。
        """
        # 保护私有属性，避免无限递归。
        if name.startswith("_"):
            raise AttributeError(name)

        # 命中缓存直接返回，避免重复实例化。
        if name in self._cache:
            return self._cache[name]

        # 按约定命名构造类名：title() 将 "my_module" → "MyModuleAPI"
        class_name = f"{name.title().replace('_', '')}API"

        # 策略 1：主模块 page_api/{name}_api/{name}_api.py
        api_class = self._try_import(f"page_api.{name}_api.{name}_api", class_name)

        # 策略 2：子模块 — 扫描所有 page_api/*_api/ 目录下的 {name}_api.py
        if api_class is None:
            api_class = self._search_submodule(name, class_name)

        # 策略 3：base_api 变体 — 同目录下的 {name}_base_api.py
        if api_class is None:
            api_class = self._try_import(f"page_api.{name}_api.{name}_base_api", class_name)

        if api_class is None:
            raise AttributeError(
                f"未找到 API 模块 '{name}'。"
                f"请确认以下任一位置存在：\n"
                f"  1. page_api/{name}_api/{name}_api.py（主模块）\n"
                f"  2. page_api/*_api/{name}_api.py（子模块）\n"
                f"  3. page_api/{name}_api/{name}_base_api.py（base_api 变体）\n"
                f"且包含 {class_name} 类。"
            )

        # 通过 .use() 创建实例，自动注入登录 Session。
        instance = self.use(api_class)
        self._cache[name] = instance
        return instance

    # --------------------------------内部方法---------------------------------------

    @staticmethod
    def _try_import(module_name, class_name):
        """尝试导入指定模块并获取目标类。

        Args:
            module_name: 完整模块路径，如 "page_api.portal_api.portal_api"。
            class_name: 目标类名。

        Returns:
            type | None: 成功返回类对象，失败返回 None。
        """
        try:
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)
        except (ImportError, AttributeError):
            return None

    def _search_submodule(self, name, class_name):
        """扫描所有 page_api/*_api/ 目录，查找 {name}_api.py 子模块文件。

        Args:
            name: 模块短名，如 'reqlist'。
            class_name: 目标类名，如 'ReqlistAPI'。

        Returns:
            type | None: 成功返回类对象，失败返回 None。
        """
        # 计算 page_api/ 目录的绝对路径（当前文件在 page_api/public/ 下）。
        page_api_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

        try:
            dir_entries = os.listdir(page_api_dir)
        except OSError:
            return None

        for dir_name in dir_entries:
            # 只遍历 _api 结尾的目录，且跳过当前 name 对应的主模块目录。
            if not dir_name.endswith("_api"):
                continue
            if dir_name == f"{name}_api":
                continue  # 主模块已在 _try_import 中尝试过

            sub_module_name = f"page_api.{dir_name}.{name}_api"
            result = self._try_import(sub_module_name, class_name)
            if result is not None:
                return result

        return None

    def use(self, api_class, **kwargs):
        """创建指定 API 类的实例，自动注入登录 Session。

        通过 BaseAPI 的 session 参数，将已登录的 Session 注入到
        新创建的 API 实例中，实现跨模块 Cookie 共享。

        Args:
            api_class: BaseAPI 子类，如 AnnounceAPI、FormAPI。
            **kwargs: 传给 api_class.__init__ 的额外参数
                      （如 timeout、headers 等）。

        Returns:
            api_class 实例，已共享登录 Session。
        """
        return api_class(
            base_url=self._base_url,
            session=self._session,
            caller=self._caller,
            **kwargs,
        )