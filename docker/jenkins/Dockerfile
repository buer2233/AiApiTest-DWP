# 可选 Jenkins 工具链镜像。
# 默认 docker-compose.yml 使用官方 Jenkins 镜像；只有需要 Jenkins 容器内直接执行
# api-test、生成 Allure 报告时，才通过 docker-compose.jenkins-tools.yml 构建本镜像。
FROM jenkins/jenkins:lts-jdk17

USER root

# Allure CLI 版本可在构建时覆盖，默认与部署文档保持一致。
ARG ALLURE_COMMANDLINE_VERSION=2.30.0

# 安装 Pipeline 运行所需工具链：Python 虚拟环境、git、curl/unzip 和 Allure CLI。
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-pip \
        python3-venv \
        unzip \
    && curl -fsSL https://github.com/allure-framework/allure2/releases/download/${ALLURE_COMMANDLINE_VERSION}/allure-${ALLURE_COMMANDLINE_VERSION}.zip -o /tmp/allure-commandline.zip \
    && unzip /tmp/allure-commandline.zip -d /opt \
    && ln -s /opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin/allure /usr/local/bin/allure \
    && rm -rf /tmp/allure-commandline.zip /var/lib/apt/lists/*

# 把 Allure CLI 放入 PATH，确保 Jenkins Pipeline 可以直接调用 allure 命令。
ENV PATH="/opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin:${PATH}"

# 恢复 Jenkins 官方镜像默认用户，避免运行时以 root 身份启动 Jenkins。
USER jenkins
