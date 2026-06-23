# Stage 6: Test Runs and Failure Cases API

## Scope

Stage 6 adds the DRF backend API for test runs, failure cases, retry actions and report entry metadata.

Implemented:
- `TestRun` model for run metadata, retry mode, paths, summary and trigger user.
- `FailureCase` model for failed pytest node ids and retry status.
- Allure result parser for failed/broken result JSON files.
- Backend runner adapter that calls `api-test/tools/ci_runner.py` instead of rebuilding pytest command rules in DRF.
- REST endpoints under `/api/test-runs/`.

Not included:
- Real Jenkins build query or trigger API. That belongs to Stage 7.
- Frontend pages. That belongs to Stages 8 and 9.
- Serving static Allure HTML files. Stage 6 only returns the first report entry metadata.

## Models

### TestRun

Fields:
- `run_id`
- `case_path`
- `node_ids`
- `retry_mode`: `none`, `selected`, `all-failed`, `module`
- `retry_count`
- `status`: `pending`, `running`, `passed`, `failed`, `error`
- `triggered_by`
- `trigger_source`: `api`, `jenkins`, `manual`
- `parent_run`
- `report_path`
- `allure_results_path`
- `console_log_path`
- `started_at`
- `finished_at`
- `summary`

### FailureCase

Fields:
- `test_run`
- `node_id`
- `case_name`
- `module_path`
- `description`
- `error_type`
- `assertion_message`
- `status`
- `retry_status`
- `last_retry_run`

## API

Authentication uses DRF Token, same as Stage 5.

```text
GET  /api/test-runs/
POST /api/test-runs/
GET  /api/test-runs/{id}/
GET  /api/test-runs/{id}/failures/
POST /api/test-runs/{id}/retry-selected/
POST /api/test-runs/{id}/retry-all-failed/
POST /api/test-runs/{id}/retry-module/
GET  /api/test-runs/{id}/report/
```

### Create Test Run

```json
{
  "case_path": "test_case/test_gbif_case",
  "node_ids": [],
  "retry_mode": "none",
  "retry_count": 0
}
```

Returns `201 Created` with the stored `TestRun` record and `failure_count`.

### Retry Selected

```json
{
  "failure_ids": [1, 2],
  "retry_count": 1
}
```

The backend resolves node ids from the selected `FailureCase` records and calls the shared API test runner adapter with `retry_mode=selected`.

### Retry All Failed

```json
{
  "retry_count": 1
}
```

The backend uses all failed node ids attached to the original test run.

### Retry Module

```json
{
  "module_path": "test_case/test_gbif_case",
  "retry_count": 1
}
```

The backend calls the shared API test runner adapter with `retry_mode=module` and the module path as `case_path`.

### Report Entry

When a test run has `report_path`, the first version returns:

```json
{
  "report_url": "/reports/<run_id>/",
  "run_id": "<run_id>"
}
```

The response does not expose the server absolute path. Static report serving is deferred to Stage 10.

## Allure Parsing

Parser input:

```text
api-test/runtime/ci-runs/<run_id>/allure-results/*.json
```

Parser output:
- `node_id`
- `case_name`
- `module_path`
- `description`
- `error_type`
- `assertion_message`
- `status`

If Allure result files are unavailable, Stage 6 falls back to `summary.failed_nodeids`.

## Test Results

RED:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest tests/test_allure_results_parser.py -v
python -m pytest tests/test_test_runs_api.py -v
```

Result:
- `ModuleNotFoundError: No module named 'apps.test_runs'`

GREEN:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest tests/test_allure_results_parser.py tests/test_test_runs_api.py -v
python manage.py check
python -m pytest -v
```

Result:
- Stage 6 focused tests: `9 passed`
- Django check: `System check identified no issues`
- Backend regression: `19 passed`

## Issues

- MySQL rejected a unique constraint on `(test_run, node_id)` because `node_id` is intentionally long enough for pytest node ids. The constraint was removed.
- The first failed migration attempt left partial tables in the reused MySQL test database. Re-running with `--create-db` rebuilt the test database cleanly.
