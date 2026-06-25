// Jenkins API 自动化测试 Pipeline 主脚本。
// 本脚本负责定义 Jenkins 参数、兼容 Windows/Linux agent、调用 api-test CI 执行器、
// 校验 Allure HTML 报告生成结果，并归档 runtime/ci-runs/<run_id> 下的运行产物。

def runCommand(String unixCommand, String windowsCommand) {
    // 根据 Jenkins agent 操作系统选择 sh 或 bat，避免在 Pipeline 中写死单一平台命令。
    if (isUnix()) {
        sh unixCommand
    } else {
        bat windowsCommand
    }
}

def call() {
    // Jenkins job 参数必须和 api-test/tools/ci_runner.py 的 --from-jenkins-env 契约保持一致。
    properties([
        parameters([
            string(
                name: 'CASE_PATH',
                defaultValue: 'test_case/test_gbif_case',
                description: 'pytest module or case path relative to api-test'
            ),
            text(
                name: 'PYTEST_NODE_IDS',
                defaultValue: '',
                description: 'pytest node ids separated by newlines or commas'
            ),
            choice(
                name: 'RETRY_MODE',
                choices: ['none', 'selected', 'all-failed', 'module'].join('\n'),
                description: 'Retry mode passed to api-test/tools/ci_runner.py'
            ),
            string(
                name: 'RETRY_COUNT',
                defaultValue: '0',
                description: 'pytest-rerunfailures retry count'
            ),
            booleanParam(
                name: 'CLEAN_ALLURE',
                defaultValue: true,
                description: 'Clean Allure results before pytest run'
            ),
            booleanParam(
                name: 'OPEN_REPORT',
                defaultValue: false,
                description: 'Open Allure report after generation; keep false in CI'
            )
        ])
    ])

    def apiTestDir = 'api-test'
    def unixPython = '.venv/bin/python'
    def windowsPython = '.venv\\Scripts\\python'
    def runId = env.BUILD_TAG ?: "jenkins-${env.BUILD_NUMBER}"
    def runDir = "${apiTestDir}/runtime/ci-runs/${runId}"

    // 通过环境变量向 ci_runner 传递参数，避免 Groovy 复制 pytest 和失败重试规则。
    withEnv([
        "CASE_PATH=${params.CASE_PATH}",
        "PYTEST_NODE_IDS=${params.PYTEST_NODE_IDS ?: ''}",
        "RETRY_MODE=${params.RETRY_MODE}",
        "RETRY_COUNT=${params.RETRY_COUNT}",
        "CLEAN_ALLURE=${params.CLEAN_ALLURE}",
        "OPEN_REPORT=${params.OPEN_REPORT}",
        "RUN_ID=${runId}",
        'CI_RUNNER_ENV=jenkins'
    ]) {
        stage('Checkout') {
            // 本地挂载仓库的 Jenkins 容器可跳过 checkout，真实 Jenkins job 仍使用 scm 检出。
            if (env.LOCAL_WORKSPACE_REPO == 'true') {
                echo "Using local mounted repository at ${pwd()}"
            } else {
                checkout scm
            }
        }

        stage('Prepare Python') {
            // 先输出 Python 版本，便于 Jenkins 日志中定位 agent 工具链问题。
            runCommand(
                "cd ${apiTestDir} && python --version",
                "cd ${apiTestDir} && python --version"
            )
        }

        stage('Install API Test Requirements') {
            // 每次构建在 api-test 目录创建隔离虚拟环境，避免污染 Jenkins agent 全局 Python。
            runCommand(
                "cd ${apiTestDir} && python -m venv .venv && ${unixPython} -m pip install -r requirements.txt",
                "cd ${apiTestDir} && python -m venv .venv && ${windowsPython} -m pip install -r requirements.txt"
            )
        }

        stage('Run API Tests') {
            // 用例断言失败是测试结果，不是 Jenkins 基础设施失败；ci_runner 会把失败明细写入 summary 和 Allure。
            runCommand(
                "cd ${apiTestDir} && ${unixPython} -m tools.ci_runner --from-jenkins-env",
                "cd ${apiTestDir} && ${windowsPython} -m tools.ci_runner --from-jenkins-env"
            )
        }

        stage('Generate Allure Report') {
            // 读取 ci_runner 写出的 summary.json，显式校验 Allure HTML 是否生成成功。
            runCommand(
                "cd ${apiTestDir} && ${unixPython} - <<'PY'\nimport json\nimport sys\nfrom pathlib import Path\nsummary_path = Path('runtime/ci-runs') / '${runId}' / 'summary.json'\nsummary = json.loads(summary_path.read_text(encoding='utf-8'))\nprint(json.dumps(summary, ensure_ascii=False, indent=2))\nif summary.get('allure_report_status') != 'generated':\n    print('Allure HTML report was not generated: ' + summary.get('allure_report_message', ''), file=sys.stderr)\n    raise SystemExit(1)\nPY",
                "cd ${apiTestDir} && ${windowsPython} -c \"import json, sys; from pathlib import Path; p=Path('runtime/ci-runs')/'${runId}'/'summary.json'; s=json.loads(p.read_text(encoding='utf-8')); print(json.dumps(s, ensure_ascii=False, indent=2)); status=s.get('allure_report_status'); msg=s.get('allure_report_message', ''); sys.exit(0 if status == 'generated' else (print('Allure HTML report was not generated: ' + msg, file=sys.stderr) or 1))\""
            )
        }

        stage('Archive Runtime Artifacts') {
            // 归档完整运行目录，便于后端或人工追踪 summary、Allure 原始结果和 HTML 报告。
            archiveArtifacts(
                artifacts: "${runDir}/**",
                allowEmptyArchive: true,
                fingerprint: true
            )
        }

        stage('Publish Allure') {
            try {
                // 如果 Jenkins 已安装 Allure 插件，则直接发布 allure-results。
                allure([
                    includeProperties: false,
                    jdk: '',
                    results: [[path: "${runDir}/allure-results"]]
                ])
            } catch (NoSuchMethodError ignored) {
                // 没有插件时不中断归档链路，用户仍可下载 runtime 产物查看报告。
                echo 'Allure Jenkins plugin is not installed; runtime artifacts were archived instead.'
            }
        }
    }
}

// Jenkins load 需要返回脚本对象，Jenkinsfile 才能调用 pipelineScript.call()。
return this
