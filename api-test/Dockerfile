FROM aiapitest-jenkins:lts-jdk17-tools AS jenkins-tools

FROM python:3.12-slim

ARG ALLURE_COMMANDLINE_VERSION=2.30.0
ARG AIAPITEST_DEPENDENCY_HASH=unknown
ARG AIAPITEST_BUILD_INPUT_HASH=unknown
ARG AIAPITEST_SOURCE_REVISION=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/opt/java/openjdk \
    ALLURE_COMMANDLINE_HOME=/opt/allure-${ALLURE_COMMANDLINE_VERSION} \
    PATH=/opt/java/openjdk/bin:/opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin:${PATH}

# Jenkins 是本环境 Job 的先决服务，复用其已验证的 JRE 与 Allure，避免 API Runner 在构建时访问外部下载源。
COPY --from=jenkins-tools /opt/allure-${ALLURE_COMMANDLINE_VERSION} /opt/allure-${ALLURE_COMMANDLINE_VERSION}
COPY --from=jenkins-tools /opt/java/openjdk /opt/java/openjdk

WORKDIR /workspace/AiApiTest-DWP

COPY api-test/requirements.txt /tmp/api-test-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/api-test-requirements.txt \
    && python -m pip check \
    && rm -f /tmp/api-test-requirements.txt

COPY . /workspace/AiApiTest-DWP

# COPY 不会保留空目录，显式创建 api-test 运行时报告目录。
RUN mkdir -p /workspace/AiApiTest-DWP/api-test/report

LABEL aiapitest.component="api-runner" \
      aiapitest.dependency-hash="${AIAPITEST_DEPENDENCY_HASH}" \
      aiapitest.build-input-hash="${AIAPITEST_BUILD_INPUT_HASH}" \
      aiapitest.source-revision="${AIAPITEST_SOURCE_REVISION}"

WORKDIR /workspace/AiApiTest-DWP/api-test

CMD ["python", "-m", "pytest", "tests", "-q"]
