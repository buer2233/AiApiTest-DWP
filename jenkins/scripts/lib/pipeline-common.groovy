// 公共 Pipeline 工具与 stage 模板。
// 三个独立 pipeline（daily-full / module-rerun / failed-rerun）通过 load 复用本文件，
// 仅各自定义参数与模式相关环境变量；执行流程统一在此，避免重复，
// 并满足「Groovy 不复制 pytest / 失败重试 / node id / Allure 解析逻辑」的约束。

// 根据 agent 操作系统选择 sh 或 bat，兼容 Linux 与 Windows。
def runCommand(String unixCommand, String windowsCommand) {
    if (isUnix()) {
        sh unixCommand
    } else {
        bat windowsCommand
    }
}

// 统一 run id 解析：优先 BUILD_TAG，回退 BUILD_NUMBER。
def resolveRunId() {
    return env.BUILD_TAG ?: "jenkins-${env.BUILD_NUMBER}"
}

// 公共执行流程。模式相关参数由调用方通过 withEnv 注入
// （RETRY_MODE / CASE_PATH / PYTEST_NODE_IDS / RETRY_COUNT 等），
// 本流程统一以 --from-jenkins-env 调用 ci_runner，使用 workspace 相对路径。
def runStages() {
    def apiTestDir = 'api-test'
    def unixPython = '.venv/bin/python'
    def windowsPython = '.venv\\Scripts\\python'
    def runId = resolveRunId()
    def runDir = "${apiTestDir}/runtime/ci-runs/${runId}"

    stage('Checkout') {
        // 本地挂载仓库的 Jenkins 容器可跳过 checkout；真实 job 仍 scm 检出。
        if (env.LOCAL_WORKSPACE_REPO == 'true') {
            echo "Using local mounted repository at ${pwd()}"
        } else {
            checkout scm
        }
    }

    stage('Prepare Python') {
        runCommand(
            "cd ${apiTestDir} && python --version",
            "cd ${apiTestDir} && python --version"
        )
    }

    stage('Install API Test Requirements') {
        // 每次构建在 api-test 下创建隔离虚拟环境，避免污染 agent 全局 Python。
        runCommand(
            "cd ${apiTestDir} && python -m venv .venv && ${unixPython} -m pip install -r requirements.txt",
            "cd ${apiTestDir} && python -m venv .venv && ${windowsPython} -m pip install -r requirements.txt"
        )
    }

    stage('Run API Tests') {
        // 用例断言失败属于测试结果而非基础设施失败；ci_runner 将失败明细写入 summary 与 Allure。
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
        // 归档完整运行目录，便于后端或人工追踪 summary、Allure 结果与 HTML 报告。
        archiveArtifacts(
            artifacts: "${runDir}/**",
            allowEmptyArchive: true,
            fingerprint: true
        )
    }

    stage('Publish Allure') {
        try {
            allure([
                includeProperties: false,
                jdk: '',
                results: [[path: "${runDir}/allure-results"]]
            ])
        } catch (NoSuchMethodError ignored) {
            echo 'Allure Jenkins plugin is not installed; runtime artifacts were archived instead.'
        }
    }
}

// Jenkins load 需要返回脚本对象，调用方才能使用本文件的方法。
return this
