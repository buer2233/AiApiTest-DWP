import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

"""
当前文件方法说明：
1. build_pytest_command：根据用例路径、marker、清理开关和 Allure 结果目录构造 pytest 执行命令。
2. build_timestamped_allure_report_dir：根据当前时间戳构造本次 Allure 报告输出目录。
3. build_allure_generate_command：根据 Allure 结果目录和报告目录构造 allure generate 命令。
4. run_command：统一执行外部命令，并返回 subprocess 执行结果。
5. ensure_runtime_dirs：确保报告、运行时、日志和 Allure 目录存在。
6. safe_clean_allure_results：安全清理 allure-results 可再生产物，失败降级为告警。
7. main：解析命令行参数，执行 pytest，生成 Allure 报告，并按需打开报告。
"""

import config


def build_pytest_command(
    case_path="test_case",
    marker=None,
    clean=False,
    allure_results_dir=None,
):
    """构造 pytest 执行命令。
    Args:
        case_path: pytest 要执行的用例目录或文件路径，默认执行 test_case。
        marker: pytest marker 表达式，用于筛选指定标记的用例。
        clean: 是否在执行前清理旧 Allure 结果；四期 T4.5 起清理由
            safe_clean_allure_results 预执行，命令不再携带
            --clean-alluredir——沙箱策略拦截目录删除时该 flag 会让
            pytest 直接 INTERNALERROR，预清理则可降级为告警继续执行。
        allure_results_dir: 自定义 Allure 结果目录；不传时使用 config.allure_results_dir。
    Returns:
        list[str]: 可直接传给 subprocess.run 的 pytest 命令参数列表。
    """
    results_dir = Path(allure_results_dir or config.allure_results_dir)

    command = [
        "python",
        "-m",
        "pytest",
        case_path,
        f"--alluredir={results_dir}",
    ]
    if marker:
        command.extend(["-m", marker])
    # 保留本地入口的历史契约；CI runner 使用独立 run 目录隔离结果。
    if clean:
        command.append("--clean-alluredir")
    if int(config.reruns) > 0:
        command.extend(["--reruns", str(config.reruns)])
    return command


def build_timestamped_allure_report_dir(base_report_dir=None, timestamp=None):
    """构造带时间戳的 Allure 报告目录。
    Args:
        base_report_dir: Allure 报告根目录；不传时使用 config.allure_report_dir。
        timestamp: 指定时间戳字符串；不传时使用当前时间生成。
    Returns:
        Path: 本次 Allure 报告应输出到的唯一目录。
    """
    # report/allure-report 作为报告根目录，每次报告放入一个独立的时间戳子目录。
    report_root = Path(base_report_dir or config.allure_report_dir)
    report_root.mkdir(parents=True, exist_ok=True)

    # 时间戳精确到秒，便于人工按生成时间识别报告目录。
    report_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = report_root / report_timestamp

    # 如果同一秒内重复生成或历史目录已存在，追加序号，确保不覆盖旧报告。
    index = 1
    while report_dir.exists():
        report_dir = report_root / f"{report_timestamp}_{index:03d}"
        index += 1
    return report_dir


def build_allure_open_hint(report_dir):
    """说明不能用 file:// 直接打开 Allure 静态页。
    Allure 是前端路由应用，点击 Categories 等会再拉 data/*.json。
    用 file:// 打开时浏览器会拦截这些请求，页面显示 404 Not found。
    """
    report_dir = Path(report_dir)
    return (
        f"Allure 报告目录: {report_dir}\n"
        "不要用浏览器直接打开 index.html（file:// 下点击 Categories 会 404）。\n"
        f'请执行: allure open "{report_dir}"'
    )


def build_allure_generate_command(results_dir=None, report_dir=None):
    """构造 Allure 报告生成命令。
    Args:
        results_dir: Allure 原始结果目录；不传时使用 config.allure_results_dir。
        report_dir: Allure HTML 报告输出目录；不传时使用带时间戳的报告目录。
    Returns:
        list[str]: 可直接传给 subprocess.run 的 allure generate 命令参数列表。
    """
    results_dir = Path(results_dir or config.allure_results_dir)
    report_dir = Path(report_dir or build_timestamped_allure_report_dir())
    return [
        "allure",
        "generate",
        str(results_dir),
        "-o",
        str(report_dir),
    ]


def run_command(command):
    """执行外部命令并返回执行结果。
    Args:
        command: subprocess.run 可识别的命令参数列表。
    Returns:
        subprocess.CompletedProcess: 命令执行完成后的结果对象，包含 returncode 等信息。
    """
    return subprocess.run(command, check=False)


def ensure_runtime_dirs():
    """创建运行测试和生成报告所需的目录。
    包括报告目录、运行时目录、日志目录和 Allure 结果目录。
    已存在的目录会被保留，不会删除历史文件。
    """
    for path in [
        config.report_dir,
        config.runtime_dir,
        config.logs_dir,
        config.allure_results_dir,
        config.allure_report_dir,
    ]:
        Path(path).mkdir(parents=True, exist_ok=True)


def safe_clean_allure_results(results_dir=None):
    """安全清理 allure-results：仅删除可再生执行产物，失败降级为告警。

    四期 T4.5：清理逐项执行，任何条目被沙箱策略、文件锁或权限拦截时
    只记录告警并继续，不抛异常（避免 pytest --clean-alluredir 触发
    INTERNALERROR 中断全流程）。目录本身保留，供本次执行继续写入。
    Args:
        results_dir: Allure 结果目录；不传时使用 config.allure_results_dir。
    Returns:
        tuple[bool, list[str]]: (是否全部清理成功, 告警信息列表)。
    """
    target = Path(results_dir or config.allure_results_dir)
    warnings = []
    if not target.is_dir():
        return True, warnings
    failed = []
    for entry in sorted(target.iterdir()):
        try:
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        except OSError as exc:
            failed.append(f"{entry.name}: {exc}")
    if failed:
        preview = "; ".join(failed[:5])
        warnings.append(
            f"allure-results 预清理未完全成功（{len(failed)} 项残留，可能混入本次报告）：{preview}"
        )
        return False, warnings
    return True, warnings


def main(case_path="test_case", marker=None, open_report=False, clean=True, argv=None):
    """命令行主入口。
    负责解析用户传入的 pytest 执行参数，准备运行目录，执行接口自动化用例，
    检测 Allure CLI 后生成报告，并在用户指定时自动打开报告页面。
    Args:
        case_path: 默认执行的 pytest 用例目录或文件路径。
        marker: 默认使用的 pytest marker 表达式。
        open_report: 默认是否在生成 Allure 报告后自动打开报告。
        clean: 默认是否在运行前清理旧的 Allure 原始结果，默认清理以避免历史用例混入本次报告。
        argv: 指定要解析的命令行参数列表；不传时读取真实命令行参数。
    """
    # 定义命令行参数，便于通过 runpytest.py 统一控制用例范围和报告行为。
    parser = argparse.ArgumentParser(description="执行 API pytest 用例并生成 Allure 报告。")
    parser.add_argument(
        "--case-path", default=case_path, help="pytest 用例路径，默认：test_case"
    )
    parser.add_argument(
        "-m", "--marker", default=marker, help="pytest 标记表达式"
    )
    parser.add_argument(
        "--open-report",
        action=argparse.BooleanOptionalAction,
        default=open_report,
        help="生成后打开 Allure 报告",
    )
    parser.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=clean,
        help="执行前清理旧的 allure-results，默认：True",
    )
    args = parser.parse_args(argv)

    # 先创建运行所需目录，再启动 pytest，避免输出报告或日志时目录不存在。
    ensure_runtime_dirs()

    # 四期 T4.5：清理改为安全预执行；沙箱/文件锁拦截时降级为告警，
    # 不再向 pytest 传 --clean-alluredir（该路径失败会 INTERNALERROR）。
    if args.clean:
        _clean_ok, clean_warnings = safe_clean_allure_results()
        for warning in clean_warnings:
            print(f"WARNING: {warning}")

    # 根据命令行参数构造 pytest 命令，并保留执行结果用于最终退出码。
    pytest_result = run_command(
        build_pytest_command(
            case_path=args.case_path,
            marker=args.marker,
            clean=args.clean,
        )
    )

    # Allure CLI 不是 Python 依赖，需先检查本机是否可用；不可用时仅跳过报告生成。
    allure_executable = shutil.which("allure")
    if allure_executable:
        # 使用真实可执行文件路径替换命令头，减少 PATH 解析差异带来的问题。
        allure_report_dir = build_timestamped_allure_report_dir()
        allure_command = build_allure_generate_command(report_dir=allure_report_dir)
        allure_command[0] = allure_executable
        allure_result = run_command(allure_command)

        if allure_result.returncode == 0:
            print(build_allure_open_hint(allure_report_dir))
        # 只有报告生成成功且用户传入 --open-report 时，才调用 allure open。
        if args.open_report and allure_result.returncode == 0:
            run_command([allure_executable, "open", str(allure_report_dir)])
    else:
        print("未检测到 Allure CLI，已跳过 allure generate。请安装 Allure 命令行工具后重新生成报告。")

    # 使用 pytest 的退出码作为脚本退出码，方便 CI 或调用方判断测试是否通过。
    raise SystemExit(pytest_result.returncode)


def run_default_main():
    """本地直接执行 runpytest.py 的默认入口。
    这里显式传入空参数列表，避免 IDE 历史运行配置中的 --case-path 覆盖默认值，
    保证点击运行当前文件时始终从 test_case 根目录收集所有模块用例。
    """
    main(case_path="test_case", argv=[])


if __name__ == "__main__":
    import sys

    # IDE 双击运行（无参数）保持全量；命令行传入 -m / --case-path 时尊重参数。
    if len(sys.argv) > 1:
        main()
    else:
        run_default_main()
