ARG PLAYWRIGHT_BASE_IMAGE=mcr.m.daocloud.io/playwright:v1.61.1-noble
FROM ${PLAYWRIGHT_BASE_IMAGE} AS dependencies

WORKDIR /workspace/AiApiTest-DWP/front-end

COPY front-end/package.json front-end/package-lock.json ./
RUN npm ci && npm cache clean --force

COPY front-end/ ./

FROM dependencies AS build

RUN npm run build

FROM dependencies AS test

ARG AIAPITEST_DEPENDENCY_HASH=unknown
ARG AIAPITEST_BUILD_INPUT_HASH=unknown
ARG AIAPITEST_SOURCE_REVISION=unknown

LABEL aiapitest.component="frontend-test" \
      aiapitest.dependency-hash="${AIAPITEST_DEPENDENCY_HASH}" \
      aiapitest.build-input-hash="${AIAPITEST_BUILD_INPUT_HASH}" \
      aiapitest.source-revision="${AIAPITEST_SOURCE_REVISION}"

CMD ["npm", "run", "test:unit"]

FROM nginx:1.27-alpine AS runtime

ARG AIAPITEST_DEPENDENCY_HASH=unknown
ARG AIAPITEST_BUILD_INPUT_HASH=unknown
ARG AIAPITEST_SOURCE_REVISION=unknown

COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/AiApiTest-DWP/front-end/dist /usr/share/nginx/html

LABEL aiapitest.component="frontend" \
      aiapitest.dependency-hash="${AIAPITEST_DEPENDENCY_HASH}" \
      aiapitest.build-input-hash="${AIAPITEST_BUILD_INPUT_HASH}" \
      aiapitest.source-revision="${AIAPITEST_SOURCE_REVISION}"

EXPOSE 80
