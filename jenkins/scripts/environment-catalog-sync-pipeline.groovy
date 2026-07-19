// 环境目录同步 Pipeline。Git 和内部回调只使用 Jenkins Credentials，不暴露到 Groovy 源码或日志。

import groovy.json.JsonSlurperClassic

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
    return bat(returnStdout: true, script: windowsCommand).trim()
}

def runCatalogTool(String arguments) {
    runCommand(
        "python3 jenkins/scripts/environment_catalog_sync_cli.py ${arguments}",
        "python jenkins\\scripts\\environment_catalog_sync_cli.py ${arguments}"
    )
}

def requireCleanFastForwardBase(String branchName) {
    def worktreeState = readCommand('git status --porcelain --untracked-files=all', 'git status --porcelain --untracked-files=all')
    if (worktreeState) {
        error('Environment catalog SCM checkout is not clean.')
    }
    runCommand('git fetch --prune origin', 'git fetch --prune origin')
    runCommand(
        "git merge-base --is-ancestor HEAD origin/${branchName}",
        "git merge-base --is-ancestor HEAD origin/${branchName}"
    )
}

def callbackAfterSuccessfulPush(String resultPath) {
    withCredentials([string(credentialsId: env.JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID, variable: 'CATALOG_SERVICE_TOKEN')]) {
        runCommand(
            '''curl --fail --silent --show-error --request POST --header "Authorization: Bearer $CATALOG_SERVICE_TOKEN" --header "Content-Type: application/json" --data-binary @"$CATALOG_RESULT_PATH" "$CATALOG_CALLBACK_URL"''',
            'curl.exe --fail --silent --show-error --request POST --header "Authorization: Bearer %CATALOG_SERVICE_TOKEN%" --header "Content-Type: application/json" --data-binary @"%CATALOG_RESULT_PATH%" "%CATALOG_CALLBACK_URL%"'
        )
    }
}

def call() {
    properties([
        disableConcurrentBuilds(),
        parameters([
            choice(name: 'SYNC_DIRECTION', choices: ['mysql_to_yaml', 'yaml_to_mysql'].join('\n'), description: 'Catalog sync direction'),
            string(name: 'SYNC_REQUEST_ID', defaultValue: '', description: 'Immutable backend sync attempt identifier'),
            string(name: 'EXPECTED_YAML_BLOB_SHA', defaultValue: '', description: 'Expected package_environment.yaml Git blob SHA'),
            string(name: 'CATALOG_EXPORT_URL', defaultValue: '', description: 'Private backend export endpoint'),
            string(name: 'CATALOG_CALLBACK_URL', defaultValue: '', description: 'Private backend callback endpoint')
        ])
    ])

    if (!params.SYNC_REQUEST_ID?.trim() || !params.EXPECTED_YAML_BLOB_SHA?.trim()) {
        error('SYNC_REQUEST_ID and EXPECTED_YAML_BLOB_SHA are required.')
    }
    if (!params.CATALOG_CALLBACK_URL?.trim()) {
        error('CATALOG_CALLBACK_URL is required.')
    }
    if (params.SYNC_DIRECTION == 'mysql_to_yaml' && !params.CATALOG_EXPORT_URL?.trim()) {
        error('CATALOG_EXPORT_URL is required for mysql_to_yaml.')
    }
    if (!env.JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID?.trim()) {
        error('JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID is required.')
    }

    def branchName = env.JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH ?: 'main'
    def controlDir = "catalog-sync/${params.SYNC_REQUEST_ID}"
    def exportPath = "${controlDir}/catalog-export.json"
    def resultPath = "${controlDir}/catalog-result.json"
    def yamlPath = 'api-test/utils/package_environment.yaml'

    stage('Verify Isolated SCM') {
        requireCleanFastForwardBase(branchName)
    }

    if (params.SYNC_DIRECTION == 'mysql_to_yaml') {
        stage('Read Frozen Catalog Export') {
            withCredentials([string(credentialsId: env.JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID, variable: 'CATALOG_SERVICE_TOKEN')]) {
                runCommand(
                    "mkdir -p ${controlDir} && curl --fail --silent --show-error --header \"Authorization: Bearer \$CATALOG_SERVICE_TOKEN\" \"\$CATALOG_EXPORT_URL\" --output ${exportPath}",
                    "if not exist ${controlDir} mkdir ${controlDir} && curl.exe --fail --silent --show-error --header \"Authorization: Bearer %CATALOG_SERVICE_TOKEN%\" \"%CATALOG_EXPORT_URL%\" --output ${exportPath}"
                )
            }
        }
        stage('Validate and Write Catalog') {
            runCatalogTool(
                "export --catalog-json ${exportPath} --yaml-path ${yamlPath} --expected-blob-sha ${params.EXPECTED_YAML_BLOB_SHA} --result-path ${resultPath}"
            )
            runCommand('git diff --check', 'git diff --check')
        }
        stage('Commit and Fast Forward Push') {
            runCommand('git add api-test/utils/package_environment.yaml', 'git add api-test/utils/package_environment.yaml')
            def hasChanges = readCommand('git diff --cached --quiet || echo changed', 'git diff --cached --quiet || echo changed')
            if (hasChanges == 'changed') {
                runCommand(
                    "git -c user.name=AiApiTest-DWP -c user.email=jenkins@localhost commit -m \"chore: sync test environments ${params.SYNC_REQUEST_ID}\"",
                    "git -c user.name=AiApiTest-DWP -c user.email=jenkins@localhost commit -m \"chore: sync test environments ${params.SYNC_REQUEST_ID}\""
                )
            }
            runCommand(
                "git push origin HEAD:${branchName}",
                "git push origin HEAD:${branchName}"
            )
        }
        stage('Callback After Push') {
            withEnv(["CATALOG_RESULT_PATH=${resultPath}"]) {
                callbackAfterSuccessfulPush(resultPath)
            }
        }
    } else {
        stage('Validate YAML Import') {
            if (isUnix()) {
                sh "mkdir -p ${controlDir}"
            } else {
                bat "if not exist ${controlDir} mkdir ${controlDir}"
            }
            runCatalogTool(
                "import --yaml-path ${yamlPath} --expected-blob-sha ${params.EXPECTED_YAML_BLOB_SHA} --result-path ${resultPath}"
            )
        }
        stage('Callback Imported Catalog') {
            withEnv(["CATALOG_RESULT_PATH=${resultPath}"]) {
                callbackAfterSuccessfulPush(resultPath)
            }
        }
    }
}

return this
