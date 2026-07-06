// Jenkins 工具链镜像初始化脚本。
// 用途：将镜像内已安装的 Allure CLI 注册为 Jenkins Allure 插件可使用的全局工具。

import hudson.tools.ToolProperty
import jenkins.model.Jenkins
import org.allurereport.jenkins.tools.AllureCommandlineInstallation

def jenkins = Jenkins.get()
def descriptor = jenkins.getDescriptorByType(AllureCommandlineInstallation.DescriptorImpl)
def allureHome = System.getenv('ALLURE_COMMANDLINE_HOME') ?: '/opt/allure-2.30.0'
def allureBinary = new File(allureHome, 'bin/allure')
def toolName = 'Allure Commandline'

if (descriptor == null) {
    println '[AiApiTest-DWP] Allure Commandline descriptor not found; skip tool configuration.'
    return
}

if (!allureBinary.isFile()) {
    println "[AiApiTest-DWP] Allure CLI not found at ${allureBinary}; skip tool configuration."
    return
}

def retainedInstallations = descriptor.installations.findAll { it.name != toolName }
def configuredInstallation = new AllureCommandlineInstallation(
    toolName,
    allureHome,
    [] as List<ToolProperty<?>>
)
descriptor.setInstallations((retainedInstallations + configuredInstallation) as AllureCommandlineInstallation[])
descriptor.save()
jenkins.save()
println "[AiApiTest-DWP] Configured Jenkins Allure Commandline: ${toolName} -> ${allureHome}"
