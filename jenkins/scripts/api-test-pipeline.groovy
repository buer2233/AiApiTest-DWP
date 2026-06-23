def runCommand(String unixCommand, String windowsCommand) {
    if (isUnix()) {
        sh unixCommand
    } else {
        bat windowsCommand
    }
}

def call() {
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
            runCommand(
                "cd ${apiTestDir} && python -m venv .venv && ${unixPython} -m pip install -r requirements.txt",
                "cd ${apiTestDir} && python -m venv .venv && ${windowsPython} -m pip install -r requirements.txt"
            )
        }

        stage('Run API Tests') {
            catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                runCommand(
                    "cd ${apiTestDir} && ${unixPython} -m tools.ci_runner --from-jenkins-env",
                    "cd ${apiTestDir} && ${windowsPython} -m tools.ci_runner --from-jenkins-env"
                )
            }
        }

        stage('Generate Allure Report') {
            runCommand(
                "cd ${apiTestDir} && ${unixPython} - <<'PY'\nimport json\nimport sys\nfrom pathlib import Path\nsummary_path = Path('runtime/ci-runs') / '${runId}' / 'summary.json'\nsummary = json.loads(summary_path.read_text(encoding='utf-8'))\nprint(json.dumps(summary, ensure_ascii=False, indent=2))\nif summary.get('allure_report_status') != 'generated':\n    print('Allure HTML report was not generated: ' + summary.get('allure_report_message', ''), file=sys.stderr)\n    raise SystemExit(1)\nPY",
                "cd ${apiTestDir} && ${windowsPython} -c \"import json, sys; from pathlib import Path; p=Path('runtime/ci-runs')/'${runId}'/'summary.json'; s=json.loads(p.read_text(encoding='utf-8')); print(json.dumps(s, ensure_ascii=False, indent=2)); status=s.get('allure_report_status'); msg=s.get('allure_report_message', ''); sys.exit(0 if status == 'generated' else (print('Allure HTML report was not generated: ' + msg, file=sys.stderr) or 1))\""
            )
        }

        stage('Archive Runtime Artifacts') {
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
}

return this
