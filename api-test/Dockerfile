FROM python:3.12-slim

ARG ALLURE_COMMANDLINE_VERSION=2.30.0
ARG AIAPITEST_DEPENDENCY_HASH=unknown
ARG AIAPITEST_BUILD_INPUT_HASH=unknown
ARG AIAPITEST_SOURCE_REVISION=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALLURE_COMMANDLINE_HOME=/opt/allure-${ALLURE_COMMANDLINE_VERSION} \
    PATH=/opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin:${PATH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git openjdk-21-jre-headless unzip \
    && curl -fsSL "https://github.com/allure-framework/allure2/releases/download/${ALLURE_COMMANDLINE_VERSION}/allure-${ALLURE_COMMANDLINE_VERSION}.zip" -o /tmp/allure-commandline.zip \
    && unzip /tmp/allure-commandline.zip -d /opt \
    && rm -rf /tmp/allure-commandline.zip /var/lib/apt/lists/*

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
