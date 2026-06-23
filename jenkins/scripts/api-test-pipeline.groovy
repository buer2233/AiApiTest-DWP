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

    node {
        def apiTestDir = 'api-test'
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
                checkout scm
            }

            stage('Prepare Python') {
                runCommand(
                    "cd ${apiTestDir} && python --version",
                    "cd ${apiTestDir} && python --version"
                )
            }

            stage('Install API Test Requirements') {
                runCommand(
                    "cd ${apiTestDir} && python -m pip install -r requirements.txt",
                    "cd ${apiTestDir} && python -m pip install -r requirements.txt"
                )
            }

            stage('Run API Tests') {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    runCommand(
                        "cd ${apiTestDir} && python -m tools.ci_runner --from-jenkins-env",
                        "cd ${apiTestDir} && python -m tools.ci_runner --from-jenkins-env"
                    )
                }
            }

            stage('Generate Allure Report') {
                runCommand(
                    "cd ${apiTestDir} && python - <<'PY'\nimport json\nfrom pathlib import Path\nsummary = Path('runtime/ci-runs') / '${runId}' / 'summary.json'\nprint(summary.read_text(encoding='utf-8') if summary.exists() else '{}')\nPY",
                    "cd ${apiTestDir} && python -c \"from pathlib import Path; p=Path('runtime/ci-runs')/'${runId}'/'summary.json'; print(p.read_text(encoding='utf-8') if p.exists() else '{}')\""
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
}

return this
