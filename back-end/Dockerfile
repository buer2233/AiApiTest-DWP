FROM python:3.12-slim

ARG AIAPITEST_DEPENDENCY_HASH=unknown
ARG AIAPITEST_BUILD_INPUT_HASH=unknown
ARG AIAPITEST_SOURCE_REVISION=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.local

WORKDIR /workspace/AiApiTest-DWP/back-end

COPY back-end/requirements.txt /tmp/back-end-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/back-end-requirements.txt \
    && python -m pip check \
    && rm -f /tmp/back-end-requirements.txt

COPY back-end/ /workspace/AiApiTest-DWP/back-end/
# 后端模块筛选默认读取此非敏感元数据，镜像内必须具备同一相对路径。
COPY api-test/utils/package_module.yaml /workspace/AiApiTest-DWP/api-test/utils/package_module.yaml
COPY docker/healthchecks/worker_heartbeat_healthcheck.py /usr/local/bin/worker_heartbeat_healthcheck.py

LABEL aiapitest.component="backend" \
      aiapitest.dependency-hash="${AIAPITEST_DEPENDENCY_HASH}" \
      aiapitest.build-input-hash="${AIAPITEST_BUILD_INPUT_HASH}" \
      aiapitest.source-revision="${AIAPITEST_SOURCE_REVISION}"

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
