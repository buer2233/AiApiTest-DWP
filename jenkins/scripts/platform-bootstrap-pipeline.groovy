// Stage13 统一平台环境启动 Pipeline 主体。
// 所有环境判断和命令构造均委托给 platform_bootstrap Python 核心。

def runCliStatus(String command, int timeoutMinutes) {
    def exitCode = 1
    timeout(time: timeoutMinutes, unit: 'MINUTES') {
        if (isUnix()) {
            exitCode = sh(
                script: "cd \"\$PLATFORM_BOOTSTRAP_SOURCE_WORKSPACE\" && python3 jenkins/scripts/platform_bootstrap_cli.py ${command}",
                returnStatus: true
            )
        } else {
            exitCode = bat(
                script: "cd /d \"%PLATFORM_BOOTSTRAP_SOURCE_WORKSPACE%\" && python jenkins\\scripts\\platform_bootstrap_cli.py ${command}",
                returnStatus: true
            )
        }
    }
    return exitCode
}

def runCli(String command, int timeoutMinutes) {
    def exitCode = runCliStatus(command, timeoutMinutes)
    if (exitCode != 0) {
        error("Platform bootstrap stage '${command}' failed with exit code ${exitCode}; inspect archived evidence, resolve the cause, then rebuild.")
    }
}

def call() {
    def buildId = env.BUILD_TAG ?: "jenkins-${env.BUILD_NUMBER}"
    def sourceWorkspace = env.PLATFORM_BOOTSTRAP_SOURCE_WORKSPACE ?: pwd()
    def evidenceDir = "runtime/platform-bootstrap/${buildId}"
    def primaryFailure = null
    def summaryFailure = null
    def archiveFailure = null

    withEnv([
        "PLATFORM_BOOTSTRAP_SOURCE_WORKSPACE=${sourceWorkspace}",
        "PLATFORM_BOOTSTRAP_WORKSPACE=${sourceWorkspace}",
        "PLATFORM_BOOTSTRAP_EVIDENCE_DIR=${pwd()}/${evidenceDir}",
        "PLATFORM_BOOTSTRAP_BUILD_ID=${buildId}",
        "PLATFORM_BOOTSTRAP_BUILD_URL=${env.BUILD_URL ?: ''}",
        "PLATFORM_BOOTSTRAP_BUILD_ALL=${params.build_all}",
        "PLATFORM_BOOTSTRAP_RUN_FULL_TESTS=${params.run_full_tests}",
        "PLATFORM_BOOTSTRAP_SOURCE_REVISION=${env.GIT_COMMIT ?: 'unknown'}"
    ]) {
        try {
            stage('Bootstrap Preflight') {
                runCli('preflight', 5)
            }
            stage('Dependency Assurance') {
                runCli('assure-dependencies', 180)
            }
            stage('Schema & Initial Data') {
                runCli('schema-initialization', 15)
            }
            stage('Deploy') {
                runCli('deploy', 20)
            }
            stage('Health') {
                runCli('health', 10)
            }
            stage('Tests') {
                runCli('test', params.run_full_tests ? 180 : 15)
            }
        } catch (Throwable failure) {
            primaryFailure = failure
            currentBuild.result = 'FAILURE'
        } finally {
            stage('Archive & Summary') {
                try {
                    def summaryExitCode = runCliStatus('summary', 5)
                    if (summaryExitCode != 0) {
                        echo "WARNING: platform bootstrap summary returned exit code ${summaryExitCode}; preserving the primary stage result and archiving available evidence."
                        if (primaryFailure == null) {
                            summaryFailure = new RuntimeException("Platform bootstrap summary failed with exit code ${summaryExitCode}")
                            currentBuild.result = 'FAILURE'
                        }
                    }
                } catch (Throwable summaryProblem) {
                    summaryFailure = summaryProblem
                    currentBuild.result = 'FAILURE'
                    echo 'WARNING: platform bootstrap summary step failed; continuing with archive and Allure finalization.'
                }

                try {
                    archiveArtifacts(
                        artifacts: "${evidenceDir}/**",
                        allowEmptyArchive: true,
                        fingerprint: true
                    )
                } catch (Throwable archiveProblem) {
                    archiveFailure = archiveProblem
                    currentBuild.result = 'FAILURE'
                    echo "WARNING: platform bootstrap evidence archive failed: ${archiveProblem.getMessage()}"
                }

                try {
                    allure([
                        commandline: 'Allure Commandline',
                        includeProperties: false,
                        jdk: '',
                        resultPolicy: 'LEAVE_AS_IS',
                        results: [[path: "${evidenceDir}/allure-results"]]
                    ])
                } catch (Throwable publishFailure) {
                    echo "WARNING: Allure publish failed; archived evidence remains authoritative: ${publishFailure.getMessage()}"
                }
            }
        }
    }

    if (primaryFailure != null) {
        throw primaryFailure
    }
    if (summaryFailure != null) {
        throw summaryFailure
    }
    if (archiveFailure != null) {
        throw archiveFailure
    }
    currentBuild.description = "Platform bootstrap ${params.build_all ? 'full' : 'incremental'} / ${params.run_full_tests ? 'full tests' : 'smoke'}"
}

return this
