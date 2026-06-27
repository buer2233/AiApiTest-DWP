"""F6 用例同步 - ast 静态解析器单元测试（AC6.5/AC6.6 + 边界）。"""
import textwrap
from pathlib import Path

from apps.testcases.services.parser import parse_directory


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestParser:
    def test_parse_function_and_class(self, tmp_path):
        case_root = tmp_path / "test_case"
        _write(
            case_root / "test_login_case" / "test_login.py",
            '''
            import allure

            def test_ok():
                """正常登录"""
                pass

            class TestLogin:
                def test_in_class(self):
                    pass
            ''',
        )
        results = parse_directory(case_root, path_prefix="test_case")
        node_ids = {r["node_id"] for r in results}
        assert "test_case/test_login_case/test_login.py::test_ok" in node_ids
        assert (
            "test_case/test_login_case/test_login.py::TestLogin::test_in_class" in node_ids
        )
        assert all(r["module_key"] == "test_login_case" for r in results)

    def test_title_priority_title_over_story(self, tmp_path):
        # AC6.6：title 优先于 story
        case_root = tmp_path / "test_case"
        _write(
            case_root / "m" / "test_a.py",
            '''
            import allure

            @allure.title("标题A")
            @allure.story("故事A")
            def test_a():
                """文档A"""
                pass
            ''',
        )
        r = parse_directory(case_root)[0]
        assert r["case_title"] == "标题A"
        assert r["story"] == "故事A"

    def test_title_fallback_to_story(self, tmp_path):
        # AC6.6：无 title 时取 story
        case_root = tmp_path / "test_case"
        _write(
            case_root / "m" / "test_b.py",
            '''
            import allure

            @allure.story("故事B")
            def test_b():
                """
                文档B
                """
                pass
            ''',
        )
        r = parse_directory(case_root)[0]
        assert r["case_title"] == "故事B"

    def test_title_fallback_docstring_first_nonempty(self, tmp_path):
        # AC6.6：无 title 无 story 时取 docstring 首个非空行
        case_root = tmp_path / "test_case"
        _write(
            case_root / "m" / "test_c.py",
            '''
            def test_c():
                """

                文档C首个非空行
                第二行
                """
                pass
            ''',
        )
        r = parse_directory(case_root)[0]
        assert r["case_title"] == "文档C首个非空行"

    def test_severity_parsed(self, tmp_path):
        # AC6.5：severity 解析为小写
        case_root = tmp_path / "test_case"
        _write(
            case_root / "m" / "test_s.py",
            '''
            import allure

            @allure.severity(allure.severity_level.CRITICAL)
            def test_s():
                pass
            ''',
        )
        r = parse_directory(case_root)[0]
        assert r["severity"] == "critical"

    def test_story_parsed(self, tmp_path):
        # AC6.5：story 解析入库
        case_root = tmp_path / "test_case"
        _write(
            case_root / "m" / "test_st.py",
            '''
            import allure

            @allure.story("登录场景")
            def test_st():
                pass
            ''',
        )
        r = parse_directory(case_root)[0]
        assert r["story"] == "登录场景"

    def test_parametrize_recorded_function_level(self, tmp_path):
        # F6 边界：参数化按函数级记录一条，node_id 不含 [param]
        case_root = tmp_path / "test_case"
        _write(
            case_root / "m" / "test_p.py",
            '''
            import pytest

            @pytest.mark.parametrize("x", [1, 2, 3])
            def test_p(x):
                pass
            ''',
        )
        results = parse_directory(case_root)
        assert len(results) == 1
        assert results[0]["node_id"].endswith("::test_p")
        assert "[" not in results[0]["node_id"]

    def test_non_test_functions_ignored(self, tmp_path):
        # 仅解析 test_ 开头的函数
        case_root = tmp_path / "test_case"
        _write(
            case_root / "m" / "test_h.py",
            '''
            def helper():
                pass

            def test_real():
                pass
            ''',
        )
        results = parse_directory(case_root)
        assert len(results) == 1
        assert results[0]["function_name"] == "test_real"
