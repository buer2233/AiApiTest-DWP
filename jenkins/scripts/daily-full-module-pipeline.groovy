// 唯一 Daily 父 Pipeline：只编排 Worker、回收工件并委托 Task 1 工具做预检和聚合。

import groovy.json.JsonOutput
import groovy.json.JsonSlurperClassic

def runTask1Tool(String arguments) {
    if (isUnix()) {
        sh "python3 jenkins/scripts/daily_full_module_cli.py ${arguments}"
    } else {
        bat "python jenkins\\scripts\\daily_full_module_cli.py ${arguments}"
    }
}

def call() {
    def retentionDays = env.CI_RUN_RETENTION_DAYS ?: '30'
    def configuredDailyParentJobName = 'AiApiTest-DWP-Daily-Full-Module'
    def dailyProperties = [
        buildDiscarder(logRotator(daysToKeepStr: retentionDays, artifactDaysToKeepStr: retentionDays)),
        parameters([
            string(
                name: 'TARGET_BASE_URL',
                defaultValue: '',
                description: 'Optional registered environment URL; an empty value uses the private default'
            )
        ])
    ]
    // 旧分模块 Job 会保留并仍可手工构建；仅配置的唯一父 Job 可以恢复 Daily 定时器。
    if (env.JOB_NAME == configuredDailyParentJobName) {
        dailyProperties.add(pipelineTriggers([cron('0 2 * * *')]))
    }
    properties(dailyProperties)

    def parentRunId = "daily-${env.BUILD_NUMBER}"
    def controlDir = "daily-control/${parentRunId}"
    def preflightPath = "${controlDir}/preflight.json"
    def workerArtifactRoot = "daily-workers/${parentRunId}"
    def parentRunDir = "api-test/runtime/ci-runs/${parentRunId}"
    def dailyWorkerJobName = 'AiApiTest-DWP-Daily-Full-Module-Worker'

    stage('Daily Preflight') {
        if (isUnix()) {
            sh "mkdir -p ${controlDir}"
        } else {
            bat "if not exist ${controlDir} mkdir ${controlDir}"
        }
        withEnv(["DAILY_TARGET_BASE_URL=${params.TARGET_BASE_URL ?: ''}"]) {
            def preflightArguments = isUnix() ?
                'preflight --module-manifest api-test/utils/package_module.yaml --environment-catalog api-test/utils/package_environment.yaml --target-base-url "$DAILY_TARGET_BASE_URL" --output ' + preflightPath :
                'preflight --module-manifest api-test/utils/package_module.yaml --environment-catalog api-test/utils/package_environment.yaml --target-base-url "%DAILY_TARGET_BASE_URL%" --output ' + preflightPath
            runTask1Tool(preflightArguments)
        }
    }

    def preflight = new JsonSlurperClassic().parseText(readFile(preflightPath))
    def moduleKeys = preflight.module_keys ?: []
    if (!(moduleKeys instanceof List) || moduleKeys.isEmpty()) {
        error('Daily preflight did not return any module keys.')
    }
    def targetBaseUrl = preflight.target_base_url ?: ''
    def workerFailures = Collections.synchronizedList([])
    def workerArtifacts = Collections.synchronizedList([])
    def workerBranches = [:]

    moduleKeys.eachWithIndex { rawModuleKey, index ->
        def moduleKey = rawModuleKey.toString()
        def moduleIndex = index as int
        def workerRunId = "${parentRunId}-m${moduleIndex}"
        workerBranches["worker-${moduleIndex}"] = {
            try {
                def workerBuild = build(
                    job: dailyWorkerJobName,
                    wait: true,
                    propagate: false,
                    parameters: [
                        string(name: 'CASE_PATH', value: "test_case/${moduleKey}"),
                        string(name: 'MODULE_NAME', value: moduleKey),
                        string(name: 'RUN_ID', value: workerRunId),
                        string(name: 'TARGET_BASE_URL', value: targetBaseUrl)
                    ]
                )
                if (workerBuild.result != 'SUCCESS') {
                    workerFailures.add("${moduleKey}: ${workerBuild.result}")
                }
                copyArtifacts(
                    projectName: dailyWorkerJobName,
                    selector: specific("${workerBuild.number}"),
                    filter: "api-test/runtime/ci-runs/${workerRunId}/**",
                    target: "${workerArtifactRoot}/${moduleIndex}",
                    optional: false
                )
                workerArtifacts.add([
                    module_key: moduleKey,
                    run_dir: "${workerArtifactRoot}/${moduleIndex}/api-test/runtime/ci-runs/${workerRunId}"
                ])
            } catch (Throwable workerFailure) {
                // 单个 Worker 基础设施异常不得中断其他模块；聚合阶段统一给出父任务诊断。
                workerFailures.add("${moduleKey}: ${workerFailure.getMessage()}")
            }
        }
    }

    stage('Run Daily Workers') {
        // 每个分支等待对应 Worker；限流分类确保跨父构建最多同时运行 10 个 Worker。
        parallel workerBranches
    }

    stage('Aggregate Daily Results') {
        def artifactsPath = "${controlDir}/worker-artifacts.json"
        writeFile(
            file: artifactsPath,
            text: JsonOutput.toJson(workerArtifacts.toList()) + "\n",
            encoding: 'UTF-8'
        )
        runTask1Tool(
            "aggregate --module-manifest api-test/utils/package_module.yaml --worker-artifacts ${artifactsPath} --parent-run-dir ${parentRunDir}"
        )
    }

    stage('Archive Daily Parent') {
        archiveArtifacts(artifacts: "${parentRunDir}/**", allowEmptyArchive: true, fingerprint: true)
        allure([
            commandline: 'Allure Commandline',
            includeProperties: false,
            jdk: '',
            resultPolicy: 'LEAVE_AS_IS',
            results: [[path: "${parentRunDir}/allure-results"]]
        ])
    }

    def summary = new JsonSlurperClassic().parseText(readFile("${parentRunDir}/summary.json"))
    if (workerFailures || summary.status != 'passed') {
        currentBuild.result = 'FAILURE'
        error('Daily parent completed with Worker, aggregation or test failures after archiving all available results.')
    }
}

return this
