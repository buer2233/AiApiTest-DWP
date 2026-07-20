// 环境目录同步 Pipeline。Git 和内部回调只使用 Jenkins Credentials，不暴露到 Groovy 源码或日志。

import groovy.json.JsonSlurperClassic
import groovy.json.JsonOutput

def runCommand(String unixCommand, String windowsCommand) {
    if (isUnix()) {
        sh unixCommand
    } else {
        bat windowsCommand
    }
}

def readCommand(String unixCommand, String windowsCommand) {
    if (isUnix()) {
        return sh(returnStdout: true, script: unixCommand).trim()
    }
    return bat(returnStdout: true, script: "@${windowsCommand}").trim()
}

def runCatalogTool(String arguments) {
    runCommand(
        "python3 jenkins/scripts/environment_catalog_sync_cli.py ${arguments}",
        "python jenkins\\scripts\\environment_catalog_sync_cli.py ${arguments}"
    )
}

def withCatalogPushCredentials(Closure operation) {
    def pushCredentialsId = env.JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID?.trim()
    if (!pushCredentialsId) {
        error('JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID is required.')
    }
    // 独立的最小权限凭据只包裹需要远端认证的 fetch/push，不写入 Git 配置或控制台。
    withCredentials([usernamePassword(
        credentialsId: pushCredentialsId,
        usernameVariable: 'CATALOG_GIT_PUSH_USERNAME',
        passwordVariable: 'CATALOG_GIT_PUSH_PASSWORD'
    )]) {
        if (isUnix()) {
            withEnv([
                'GIT_TERMINAL_PROMPT=0',
                'GIT_ASKPASS=jenkins/scripts/environment-catalog-git-askpass.sh'
            ]) {
                operation()
            }
        } else {
            withEnv([
                'GIT_TERMINAL_PROMPT=0',
                'GIT_ASKPASS=jenkins\\scripts\\environment-catalog-git-askpass.bat'
            ]) {
                operation()
            }
        }
    }
}

def requireCleanFastForwardBase(String branchName) {
    def worktreeState = readCommand('git status --porcelain --untracked-files=all', 'git status --porcelain --untracked-files=all')
    if (worktreeState) {
        error('Environment catalog SCM checkout is not clean.')
    }
    withCatalogPushCredentials {
        runCommand('git fetch --quiet --prune origin', 'git fetch --quiet --prune origin')
    }
    runCommand(
        "git merge-base --is-ancestor origin/${branchName} HEAD",
        "git merge-base --is-ancestor origin/${branchName} HEAD"
    )
}

def callbackAfterSuccessfulPush(String resultPath, String callbackEndpoint) {
    withCredentials([string(credentialsId: env.JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID, variable: 'CATALOG_SERVICE_TOKEN')]) {
        withEnv([
            "CATALOG_RESULT_PATH=${resultPath}",
            "CATALOG_CALLBACK_ENDPOINT=${callbackEndpoint}"
        ]) {
            runCommand(
                '''curl --fail --silent --show-error --request POST --header "Authorization: Bearer $CATALOG_SERVICE_TOKEN" --header "Content-Type: application/json" --data-binary @"$CATALOG_RESULT_PATH" "$CATALOG_CALLBACK_ENDPOINT"''',
                'curl.exe --fail --silent --show-error --request POST --header "Authorization: Bearer %CATALOG_SERVICE_TOKEN%" --header "Content-Type: application/json" --data-binary @"%CATALOG_RESULT_PATH%" "%CATALOG_CALLBACK_ENDPOINT%"'
            )
        }
    }
}

def recordPushedCommitSha(String resultPath) {
    def commitSha = readCommand('git rev-parse HEAD', 'git rev-parse HEAD')
    if (!(commitSha ==~ /^[0-9a-f]{40}$/)) {
        error('Pushed Git HEAD must be exactly 40 lowercase hexadecimal characters.')
    }
    def resultPayload = new JsonSlurperClassic().parseText(readFile(file: resultPath))
    if (!(resultPayload instanceof Map)) {
        error('Environment catalog result payload must be a JSON object.')
    }
    if (resultPayload.direction != 'mysql_to_yaml') {
        error('Only mysql_to_yaml result payloads may contain commit_sha.')
    }
    resultPayload.commit_sha = commitSha
    writeFile(
        file: resultPath,
        text: JsonOutput.prettyPrint(JsonOutput.toJson(resultPayload)) + '\n'
    )
}

def call() {
    properties([
        disableConcurrentBuilds(),
        parameters([
            choice(name: 'SYNC_DIRECTION', choices: ['mysql_to_yaml', 'yaml_to_mysql'].join('\n'), description: 'Catalog sync direction'),
            string(name: 'SYNC_REQUEST_ID', defaultValue: '', description: 'Immutable backend sync attempt identifier'),
            string(name: 'EXPECTED_YAML_BLOB_SHA', defaultValue: '', description: 'Expected package_environment.yaml Git blob SHA')
        ])
    ])

    def syncDirection = params.SYNC_DIRECTION ?: ''
    if (!(syncDirection in ['mysql_to_yaml', 'yaml_to_mysql'])) {
        error('SYNC_DIRECTION must be mysql_to_yaml or yaml_to_mysql.')
    }
    def syncRequestId = params.SYNC_REQUEST_ID ?: ''
    if (!(syncRequestId ==~ /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/)) {
        error('SYNC_REQUEST_ID must be a safe opaque identifier.')
    }
    def expectedYamlBlobSha = params.EXPECTED_YAML_BLOB_SHA ?: ''
    if (!(expectedYamlBlobSha ==~ /^[0-9a-f]{40}$/)) {
        error('EXPECTED_YAML_BLOB_SHA must be exactly 40 lowercase hexadecimal characters.')
    }
    if (!env.JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID?.trim()) {
        error('JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID is required.')
    }
    def catalogServiceBaseUrl = env.JENKINS_ENVIRONMENT_CATALOG_SERVICE_BASE_URL?.trim()
    if (!catalogServiceBaseUrl) {
        error('JENKINS_ENVIRONMENT_CATALOG_SERVICE_BASE_URL is required.')
    }
    catalogServiceBaseUrl = catalogServiceBaseUrl.replaceFirst('/+$', '')
    // 内部 API 路径不可由请求方传入，避免服务令牌随外部 URL 请求泄露。
    def catalogExportEndpoint = "${catalogServiceBaseUrl}/api/v1/internal/environment-catalog-sync-attempts/${syncRequestId}/export/"
    def catalogCallbackEndpoint = "${catalogServiceBaseUrl}/api/v1/internal/environment-catalog-sync-attempts/${syncRequestId}/callback/"

    def branchName = env.JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH ?: 'main'
    def controlDir = "catalog-sync/${syncRequestId}"
    def exportPath = "${controlDir}/catalog-export.json"
    def resultPath = "${controlDir}/catalog-result.json"
    def yamlPath = 'api-test/utils/package_environment.yaml'

    stage('Verify Isolated SCM') {
        requireCleanFastForwardBase(branchName)
    }

    if (syncDirection == 'mysql_to_yaml') {
        stage('Read Frozen Catalog Export') {
            withCredentials([string(credentialsId: env.JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID, variable: 'CATALOG_SERVICE_TOKEN')]) {
                withEnv(["CATALOG_EXPORT_ENDPOINT=${catalogExportEndpoint}"]) {
                    runCommand(
                        "mkdir -p ${controlDir} && curl --fail --silent --show-error --header \"Authorization: Bearer \$CATALOG_SERVICE_TOKEN\" \"\$CATALOG_EXPORT_ENDPOINT\" --output ${exportPath}",
                        "if not exist ${controlDir} mkdir ${controlDir} && curl.exe --fail --silent --show-error --header \"Authorization: Bearer %CATALOG_SERVICE_TOKEN%\" \"%CATALOG_EXPORT_ENDPOINT%\" --output ${exportPath}"
                    )
                }
            }
        }
        stage('Validate and Write Catalog') {
            runCatalogTool(
                "export --catalog-json ${exportPath} --yaml-path ${yamlPath} --expected-blob-sha ${expectedYamlBlobSha} --result-path ${resultPath}"
            )
            runCommand('git diff --check', 'git diff --check')
        }
        stage('Commit and Fast Forward Push') {
            runCommand('git add api-test/utils/package_environment.yaml', 'git add api-test/utils/package_environment.yaml')
            def hasChanges = readCommand('git diff --cached --quiet || echo changed', 'git diff --cached --quiet || echo changed')
            if (hasChanges == 'changed') {
                runCommand(
                    "git -c user.name=AiApiTest-DWP -c user.email=jenkins@localhost commit -m \"chore: sync test environments ${syncRequestId}\"",
                    "git -c user.name=AiApiTest-DWP -c user.email=jenkins@localhost commit -m \"chore: sync test environments ${syncRequestId}\""
                )
            }
            withCatalogPushCredentials {
                runCommand(
                    "git push --quiet origin HEAD:${branchName}",
                    "git push --quiet origin HEAD:${branchName}"
                )
            }
        }
        stage('Callback After Push') {
            recordPushedCommitSha(resultPath)
            callbackAfterSuccessfulPush(resultPath, catalogCallbackEndpoint)
        }
    } else {
        stage('Validate YAML Import') {
            if (isUnix()) {
                sh "mkdir -p ${controlDir}"
            } else {
                bat "if not exist ${controlDir} mkdir ${controlDir}"
            }
            runCatalogTool(
                "import --yaml-path ${yamlPath} --expected-blob-sha ${expectedYamlBlobSha} --result-path ${resultPath}"
            )
        }
        stage('Callback Imported Catalog') {
            callbackAfterSuccessfulPush(resultPath, catalogCallbackEndpoint)
        }
    }
}

return this
