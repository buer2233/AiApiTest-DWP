# -*- coding: utf-8 -*-
"""E9 数据中心看板（board）模块接口封装。

r349149：数字面板过滤条件「不包含/开头不是/结尾不包含/不包含于」对空值字段的
匹配口径变更，受影响入口为 getData 与 getDataWithConfig。
"""

import json

import allure

from page_api.public.base_api import BaseAPI


def compress_lz(text: str) -> str:
    """按 E9 ``DecryptLZ.decrypt`` 的逆过程做 LZW 压缩。

    E9 的 ``MobileCommonUtil.decompressByLZ`` 使用逗号分隔的整数码：
    小于 65536 的码是字面字符码值，65536 起为字典条目。
    本实现与其解码器严格互逆，供 getDataWithConfig 构造 ``data`` 参数。
    """
    # Author: Claude
    # Create Date: 2026-08-18
    # IsAI: True
    if not text:
        return ""
    dictionary: dict[str, int] = {}
    dict_size = 65536
    codes: list[str] = []
    word = text[0]
    for char in text[1:]:
        combined = word + char
        if combined in dictionary:
            word = combined
            continue
        codes.append(str(dictionary[word]) if len(word) > 1 else str(ord(word)))
        dictionary[combined] = dict_size
        dict_size += 1
        word = char
    codes.append(str(dictionary[word]) if len(word) > 1 else str(ord(word)))
    return ",".join(codes)


def build_widget_config_data(
    datamodel: str = "",
    config: str = "",
    dimensions: tuple | list = (),
    measures: tuple | list = (),
    filters: tuple | list = (),
    widget_type: str = "BAR",
) -> str:
    """构造 getDataWithConfig 的 ``data`` 参数（JSON 序列化后 LZW 压缩）。"""
    # Author: Claude
    # Create Date: 2026-08-18
    # IsAI: True
    payload = {
        "datamodel": datamodel,
        "config": config,
        "dimensions": list(dimensions),
        "measures": list(measures),
        "filters": list(filters),
        "type": widget_type,
    }
    return compress_lz(json.dumps(payload, ensure_ascii=False))


class BoardWidgetAPI(BaseAPI):
    """E9 数据中心看板组件接口。"""

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：创建看板组件")
    def create_widget(
        self,
        name,
        widget_type,
        board,
        datamodel="",
        dm_type="",
        layout="{}",
        config="",
        mobile_layout="",
        status_code=200,
        **kwargs,
    ):
        """在看板下创建组件（如 DIGITALPANEL），返回主键 id。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/widget/create"
        error_msg = kwargs.pop("error_msg", "创建看板组件")
        form_data = {
            "name": name,
            "type": widget_type,
            "board": str(board),
            "datamodel": str(datamodel),
            "dmType": dm_type,
            "layout": layout,
            "config": config,
            "mobileLayout": mobile_layout,
        }
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：配置看板组件（维度/度量/过滤条件）")
    def config_widget(self, config_payload, status_code=200, **kwargs):
        """写入组件配置；``config_payload`` 为完整 JSON 字符串，内部做 LZW 压缩。

        JSON 需包含 ``id`` 与 ``dimensions``/``measures``/``filters``，
        可选 ``name``/``type``/``datamodel``/``dmType``/``config``。
        """
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/widget/config"
        error_msg = kwargs.pop("error_msg", "配置看板组件")
        form_data = {"data": compress_lz(config_payload)}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：删除看板组件")
    def delete_widget(self, widget_id, status_code=200, **kwargs):
        """按 id 删除组件。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/widget/delete"
        error_msg = kwargs.pop("error_msg", "删除看板组件")
        return self.get(
            url,
            status_code=status_code,
            params={"id": str(widget_id), **kwargs},
            headers=self._browser_headers(),
            error_msg=error_msg,
        )

    @allure.step("接口：获取看板组件数据")
    def get_data(self, widget_id, status_code=200, **kwargs):
        """按已保存的组件配置取数（过滤条件来自组件保存的 filters）。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/widget/getData"
        error_msg = kwargs.pop("error_msg", "获取看板组件数据")
        form_data = {"id": str(widget_id)}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：按临时配置获取看板组件数据")
    def get_data_with_config(self, data, status_code=200, **kwargs):
        """按请求携带的临时配置取数。

        ``data`` 为 LZW 压缩后的 JSON 字符串，可用 ``build_widget_config_data`` 构造。
        """
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/widget/getDataWithConfig"
        error_msg = kwargs.pop("error_msg", "按临时配置获取看板组件数据")
        form_data = {"data": data}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )
