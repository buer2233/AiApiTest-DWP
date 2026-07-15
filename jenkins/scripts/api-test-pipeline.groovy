// Jenkins API 自动化测试 Pipeline 主脚本。
// 本脚本负责定义 Jenkins 参数、兼容 Windows/Linux agent、委托隔离 runner，
// 并归档 runtime/ci-runs/<run_id> 与 runner-lifecycle/<run_id> 证据。

def runCommand(String unixCommand, String windowsCommand) {
    // 根据 Jenkins agent 操作系统选择 sh 或 bat，避免在 Pipeline 中写死单一平台命令。
    if (isUnix()) {
        sh unixCommand
    } else {
        bat windowsCommand
    }
}

def buildParameterDefinitions(Map config) {
    def fixedRetryMode = config.get('mode', null)
    def includeNodeIds = config.containsKey('includeNodeIds') ? config.includeNodeIds : true
    def includeModuleName = config.get('includeModuleName', false)
    def casePathDefaultEnv = config.get('casePathDefaultEnv', null)
    def casePathDefault = ''
    if (casePathDefaultEnv == 'JENKINS_MODULE_CASE_PATH') {
        // Jenkins sandbox 不允许动态下标访问环境变量，业务 Job 默认路径只显式读取白名单变量。
        casePathDefault = env.JENKINS_MODULE_CASE_PATH ?: ''
    } else if (casePathDefaultEnv == 'JENKINS_DEFAULT_CASE_PATH') {
        casePathDefault = env.JENKINS_DEFAULT_CASE_PATH ?: ''
    }
    if (!casePathDefault) {
        casePathDefault = casePathDefaultEnv ? '' : (env.JENKINS_DEFAULT_CASE_PATH ?: 'test_case/test_gbif_case')
    }

    // Jenkins job 参数必须和 api-test/tools/ci_runner.py 的 --from-jenkins-env 契约保持一致。
    def definitions = [
        string(
            name: 'CASE_PATH',
            defaultValue: casePathDefault,
            description: 'pytest module or case path relative to api-test'
        ),
        string(
            name: 'RUN_ID',
            defaultValue: '',
            description: 'Platform run key used as runtime artifact directory; empty falls back to Jenkins build tag'
        )
    ]

    if (includeModuleName) {
        definitions.add(
            string(
                name: 'MODULE_NAME',
                defaultValue: '',
                description: 'Display module name; does not change pytest selection'
            )
        )
    }

    if (includeNodeIds) {
        definitions.add(
            text(
                name: 'PYTEST_NODE_IDS',
                defaultValue: '',
                description: 'pytest node ids separated by newlines or commas'
            )
        )
    }

    if (fixedRetryMode == null) {
        definitions.add(
            choice(
                name: 'RETRY_MODE',
                choices: ['none', 'selected', 'all-failed', 'module'].join('\n'),
                description: 'Retry mode passed to api-test/tools/ci_runner.py'
            )
        )
    }

    definitions.addAll([
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
            description: 'Compatibility parameter only; Jenkins CI forces false to avoid starting a blocking Allure web server'
        )
    ])

    return definitions
}

def call(Map config = [:]) {
    def ciRunRetentionDays = env.CI_RUN_RETENTION_DAYS ?: '30'
    def jobProperties = [
        buildDiscarder(logRotator(daysToKeepStr: ciRunRetentionDays, artifactDaysToKeepStr: ciRunRetentionDays)),
        parameters(buildParameterDefinitions(config))
    ]
    def jobTriggers = config.get('jobTriggers', [])
    if (jobTriggers) {
        jobProperties.add(pipelineTriggers(jobTriggers))
    }
    properties(jobProperties)

    def runId = params.RUN_ID?.trim() ?: env.BUILD_TAG ?: "jenkins-${env.BUILD_NUMBER}"
    def runDir = "api-test/runtime/ci-runs/${runId}"
    def retryMode = config.get('mode', null) ?: params.RETRY_MODE
    def includeNodeIds = config.containsKey('includeNodeIds') ? config.includeNodeIds : true
    def pytestNodeIds = includeNodeIds ? (params.PYTEST_NODE_IDS ?: '') : ''
    def emptyNodeIdsMessage = config.get('emptyNodeIdsMessage', 'PYTEST_NODE_IDS is required for failed rerun')
    def emptyCasePathMessage = config.get('emptyCasePathMessage', 'CASE_PATH is required for this Jenkins job')

    if (config.get('requireNodeIds', false) && !pytestNodeIds.trim()) {
        // 失败重试必须显式传入平台选中的失败用例，避免误跑整个模块。
        error(emptyNodeIdsMessage)
    }
    if (config.get('requireCasePath', false) && !params.CASE_PATH?.trim()) {
        // 每日全量和模块重试必须显式绑定模块路径，避免 cron 跑到示例默认模块。
        error(emptyCasePathMessage)
    }

    // 通过环境变量向 ci_runner 传递参数，避免 Groovy 复制 pytest 和失败重试规则。
    withEnv([
        "CASE_PATH=${params.CASE_PATH}",
        "PYTEST_NODE_IDS=${pytestNodeIds}",
        "RETRY_MODE=${retryMode}",
        "RETRY_COUNT=${params.RETRY_COUNT}",
        "CLEAN_ALLURE=${params.CLEAN_ALLURE}",
        // Jenkins 是非交互环境，必须强制关闭 allure open，避免 Web server 常驻导致 stage 卡死。
        "OPEN_REPORT=false",
        "RUN_ID=${runId}",
        "MODULE_NAME=${params.MODULE_NAME ?: ''}",
        "CI_RUN_RETENTION_DAYS=${ciRunRetentionDays}",
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

        def primaryFailure = null
        try {
            stage('Run API Tests') {
                // 动态参数只通过 withEnv 传入，命令本身保持固定，避免 shell 二次解释。
                timeout(time: 60, unit: 'MINUTES') {
                    runCommand(
                        "python3 jenkins/scripts/api_runner_cli.py execute",
                        $/python jenkins\scripts\api_runner_cli.py execute/$
                    )
                }
            }
        } catch (Throwable failure) {
            primaryFailure = failure
        } finally {
            stage('Archive Runtime Artifacts') {
                try {
                    archiveArtifacts(
                        artifacts: "${runDir}/**,api-test/runtime/runner-lifecycle/${runId}/**",
                        allowEmptyArchive: true,
                        fingerprint: true
                    )
                } catch (Throwable archiveFailure) {
                    if (primaryFailure == null) {
                        primaryFailure = archiveFailure
                    } else {
                        echo "Runtime archive also failed after the primary failure: ${archiveFailure.getMessage()}"
                    }
                }
            }

            stage('Publish Allure') {
                try {
                    // Jenkins 插件只负责展示，失败时保留 helper 已导出的原始和 HTML 产物。
                    allure([
                        commandline: 'Allure Commandline',
                        includeProperties: false,
                        jdk: '',
                        resultPolicy: 'LEAVE_AS_IS',
                        results: [[path: "${runDir}/allure-results"]]
                    ])
                } catch (Throwable ignored) {
                    echo "Allure Jenkins plugin publish failed; runtime artifacts were archived instead: ${ignored.getMessage()}"
                }
            }
        }

        if (primaryFailure != null) {
            throw primaryFailure
        }
    }
}

// Jenkins load 需要返回脚本对象，Jenkinsfile 才能调用 pipelineScript.call()。
return this
