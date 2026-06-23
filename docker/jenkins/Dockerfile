FROM jenkins/jenkins:lts-jdk17

USER root

ARG ALLURE_COMMANDLINE_VERSION=2.30.0

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

ENV PATH="/opt/allure-${ALLURE_COMMANDLINE_VERSION}/bin:${PATH}"

USER jenkins
