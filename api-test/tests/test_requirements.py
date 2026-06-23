from pathlib import Path


API_TEST_ROOT = Path(__file__).resolve().parents[1]


def _requirements_lines() -> list[str]:
    return [
        line.strip()
        for line in (API_TEST_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_pytest_html_dependency_includes_py_package_for_py_xml_import():
    requirements = _requirements_lines()

    assert "pytest-html==3.1.1" in requirements
    assert "py==1.11.0" in requirements


def test_windows_only_pyreadline_is_guarded_by_platform_marker():
    requirements = _requirements_lines()

    assert 'pyreadline3==3.5.6; platform_system == "Windows"' in requirements
