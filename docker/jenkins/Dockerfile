# Jenkins 平台控制面工具镜像。
# controller 只负责编排 Docker/Compose 和发布 Allure，不承载业务 pytest 依赖。
FROM jenkins/jenkins:lts-jdk17

USER root

# Allure CLI 版本可在构建时覆盖，默认与部署文档保持一致。
ARG ALLURE_COMMANDLINE_VERSION=2.30.0

# 安装 Docker CLI/Compose 控制面、轻量 Python 编排入口和 Allure CLI。
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        gnupg \
        python3 \
        python-is-python3 \
        unzip \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && . /etc/os-release \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin docker-compose-plugin \
    && curl -fsSL https://github.com/allure-framework/allure2/releases/download/${ALLURE_COMMANDLINE_VERSION}/allure-${ALLURE_COMMANDLINE_VERSION}.zip -o /tmp/allure-commandline.zip \
    && unzip /tmp/allure-commandline.zip -d /opt \
    && ln -s /opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin/allure /usr/local/bin/allure \
    && mkdir -p /workspace \
    && chown jenkins:jenkins /workspace \
    && rm -rf /tmp/allure-commandline.zip /var/lib/apt/lists/*

# 预装 Jenkins Allure 插件，使 Pipeline 中的 allure(...) 步骤能在 Jenkins 内展示报告。
RUN jenkins-plugin-cli --plugins allure-jenkins-plugin

COPY jenkins/scripts/configure-allure-commandline.groovy /usr/share/jenkins/ref/init.groovy.d/configure-allure-commandline.groovy

# 把 Allure CLI 放入 PATH，确保 Jenkins Pipeline 可以直接调用 allure 命令。
ENV ALLURE_COMMANDLINE_HOME="/opt/allure-${ALLURE_COMMANDLINE_VERSION}" \
    PATH="/opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin:${PATH}"

# 恢复 Jenkins 官方镜像默认用户，避免运行时以 root 身份启动 Jenkins。
USER jenkins
