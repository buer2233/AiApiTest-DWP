# Stage13 Daily Full Module Design

## Status

Approved by the owner on 2026-07-19. The executable requirement is `project-info/demand/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-需求说明.md`.

## Chosen Design

`AiApiTest-DWP-Daily-Full-Module` is the only scheduled Daily parent Job. At `02:00`, or on manual Jenkins build, it validates the module and environment YAML files, then starts one unscheduled Daily Worker build per module. The `daily-worker` throttle category permits ten Worker Jobs globally; module retry and failed retry have independent categories of ten each. The parent waits for all Workers, aggregates their summaries and Allure results, then publishes the only Daily Allure report.

The platform stores only the Daily parent `JenkinsTask` and parent `TestRun`. Module records inside the aggregate update existing snapshots, case results, and history without creating child tasks.

`api-test/utils/package_environment.yaml` is the execution-time environment catalog. Its stable top-level key maps to `TestEnvironment.env_key`; values contain `base_url`, `url_name`, and `url_desc`. An empty `TARGET_BASE_URL` resolves to the current private default. A supplied URL must pass existing base URL validation and exactly match an active catalog environment before any Worker runs.

The environment page remains `/environments`. Administrators can manage environment records and request a YAML import; members stay read-only. MySQL CRUD first creates an immutable catalog synchronization attempt. A dedicated, serial Jenkins configuration Job uses an isolated SCM checkout, checks the expected YAML Git blob SHA, generates canonical YAML, commits, and fast-forward pushes the configured trunk. It never writes the local mounted development workspace. Conflicts reject the write; the administrator must import YAML or resubmit the platform change.

## Alternatives Considered

1. Parent Pipeline branches with an in-Pipeline throttle: rejected because overflow would not provide the required top-level Jenkins Queue behavior.
2. Lockable resource slots: rejected because resource waits are not the required Job Queue semantics.
3. Jenkins querying MySQL to validate environments: rejected because Jenkins must not access the platform database. A versioned YAML catalog supports preflight validation and reproducibility.

## Delivery Order

1. Requirement-driven test cases and UI range mapping.
2. TDD contracts for YAML parsing, aggregation, parent-task data model, and catalog synchronization.
3. Jenkins, api-test, backend, and frontend implementation by non-overlapping ownership.
4. Independent code review, Jenkins environment-job validation, regression evidence, acceptance package, then the approved legacy Job cleanup.
