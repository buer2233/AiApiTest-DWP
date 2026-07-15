variable "BACKEND_DEPENDENCY_HASH" { default = "unknown" }
variable "BACKEND_BUILD_INPUT_HASH" { default = "unknown" }
variable "FRONTEND_DEPENDENCY_HASH" { default = "unknown" }
variable "FRONTEND_BUILD_INPUT_HASH" { default = "unknown" }
variable "FRONTEND_PLAYWRIGHT_BASE_IMAGE" { default = "mcr.m.daocloud.io/playwright:v1.61.1-noble" }
variable "API_RUNNER_DEPENDENCY_HASH" { default = "unknown" }
variable "API_RUNNER_BUILD_INPUT_HASH" { default = "unknown" }
variable "AIAPITEST_SOURCE_REVISION" { default = "unknown" }

target "backend" {
  context    = "."
  dockerfile = "back-end/Dockerfile"
  tags       = ["aiapitest-backend:local"]
  args = {
    AIAPITEST_DEPENDENCY_HASH = BACKEND_DEPENDENCY_HASH
    AIAPITEST_BUILD_INPUT_HASH = BACKEND_BUILD_INPUT_HASH
    AIAPITEST_SOURCE_REVISION = AIAPITEST_SOURCE_REVISION
  }
}

target "frontend-runtime" {
  context    = "."
  dockerfile = "front-end/Dockerfile"
  target     = "runtime"
  tags       = ["aiapitest-frontend:local"]
  args = {
    AIAPITEST_DEPENDENCY_HASH = FRONTEND_DEPENDENCY_HASH
    AIAPITEST_BUILD_INPUT_HASH = FRONTEND_BUILD_INPUT_HASH
    PLAYWRIGHT_BASE_IMAGE = FRONTEND_PLAYWRIGHT_BASE_IMAGE
    AIAPITEST_SOURCE_REVISION = AIAPITEST_SOURCE_REVISION
  }
}

target "frontend-test" {
  context    = "."
  dockerfile = "front-end/Dockerfile"
  target     = "test"
  tags       = ["aiapitest-frontend-test:local"]
  args = {
    AIAPITEST_DEPENDENCY_HASH = FRONTEND_DEPENDENCY_HASH
    AIAPITEST_BUILD_INPUT_HASH = FRONTEND_BUILD_INPUT_HASH
    PLAYWRIGHT_BASE_IMAGE = FRONTEND_PLAYWRIGHT_BASE_IMAGE
    AIAPITEST_SOURCE_REVISION = AIAPITEST_SOURCE_REVISION
  }
}

group "frontend" {
  targets = ["frontend-runtime", "frontend-test"]
}

target "api-runner" {
  context    = "."
  dockerfile = "api-test/Dockerfile"
  tags       = ["aiapitest-api-runner:local"]
  args = {
    AIAPITEST_DEPENDENCY_HASH = API_RUNNER_DEPENDENCY_HASH
    AIAPITEST_BUILD_INPUT_HASH = API_RUNNER_BUILD_INPUT_HASH
    AIAPITEST_SOURCE_REVISION = AIAPITEST_SOURCE_REVISION
  }
}
