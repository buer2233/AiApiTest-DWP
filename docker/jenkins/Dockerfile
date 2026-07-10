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
        python-is-python3 \
        python3-pip \
        python3-venv \
        unzip \
    && curl -fsSL https://github.com/allure-framework/allure2/releases/download/${ALLURE_COMMANDLINE_VERSION}/allure-${ALLURE_COMMANDLINE_VERSION}.zip -o /tmp/allure-commandline.zip \
    && unzip /tmp/allure-commandline.zip -d /opt \
    && ln -s /opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin/allure /usr/local/bin/allure \
    && mkdir -p /workspace \
    && chown jenkins:jenkins /workspace \
    && rm -rf /tmp/allure-commandline.zip /var/lib/apt/lists/*

# 预装 api-test 依赖，executor 级 venv 通过 system-site-packages 只读复用；
# requirements 更新时，Pipeline 的缺失检测仍会在当前 executor venv 内补齐差异。
COPY api-test/requirements.txt /tmp/api-test-requirements.txt
RUN python -m pip install \
        --no-cache-dir \
        --break-system-packages \
        -r /tmp/api-test-requirements.txt \
    && rm -f /tmp/api-test-requirements.txt
ENV AIAPITEST_PREINSTALLED_REQUIREMENTS=1

# 预装 Jenkins Allure 插件，使 Pipeline 中的 allure(...) 步骤能在 Jenkins 内展示报告。
RUN jenkins-plugin-cli --plugins allure-jenkins-plugin

COPY jenkins/scripts/configure-allure-commandline.groovy /usr/share/jenkins/ref/init.groovy.d/configure-allure-commandline.groovy

# 把 Allure CLI 放入 PATH，确保 Jenkins Pipeline 可以直接调用 allure 命令。
ENV ALLURE_COMMANDLINE_HOME="/opt/allure-${ALLURE_COMMANDLINE_VERSION}" \
    PATH="/opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin:${PATH}"

# 恢复 Jenkins 官方镜像默认用户，避免运行时以 root 身份启动 Jenkins。
USER jenkins
