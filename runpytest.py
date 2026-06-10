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
6. main：解析命令行参数，执行 pytest，生成 Allure 报告，并按需打开报告。
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
        clean: 是否在运行前清理旧的 Allure 结果目录。
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


def main(case_path="test_case", marker=None, open_report=False, clean=True):
    """命令行主入口。
    负责解析用户传入的 pytest 执行参数，准备运行目录，执行接口自动化用例，
    检测 Allure CLI 后生成报告，并在用户指定时自动打开报告页面。
    Args:
        case_path: 默认执行的 pytest 用例目录或文件路径。
        marker: 默认使用的 pytest marker 表达式。
        open_report: 默认是否在生成 Allure 报告后自动打开报告。
        clean: 默认是否在运行前清理旧的 Allure 原始结果，默认清理以避免历史用例混入本次报告。
    """
    # 定义命令行参数，便于通过 runpytest.py 统一控制用例范围和报告行为。
    parser = argparse.ArgumentParser(description="Run API pytest cases and generate Allure report.")
    parser.add_argument(
        "--case-path", default=case_path, help="pytest case path, default: test_case"
    )
    parser.add_argument(
        "-m", "--marker", default=marker, help="pytest marker expression"
    )
    parser.add_argument(
        "--open-report",
        action=argparse.BooleanOptionalAction,
        default=open_report,
        help="open Allure report after generation",
    )
    parser.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=clean,
        help="clean old allure-results before run, default: True",
    )
    args = parser.parse_args()

    # 先创建运行所需目录，再启动 pytest，避免输出报告或日志时目录不存在。
    ensure_runtime_dirs()

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

        # 只有报告生成成功且用户传入 --open-report 时，才调用 allure open。
        if args.open_report and allure_result.returncode == 0:
            run_command([allure_executable, "open", str(allure_report_dir)])
    else:
        print("未检测到 Allure CLI，已跳过 allure generate。请安装 Allure 命令行工具后重新生成报告。")

    # 使用 pytest 的退出码作为脚本退出码，方便 CI 或调用方判断测试是否通过。
    raise SystemExit(pytest_result.returncode)


if __name__ == "__main__":

    # main()  # 默认的全量执行
    main(case_path='test_case/test_gbif_case')  # 单独执行某个模块的用例
