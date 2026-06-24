# Final Integration Report

## Scope

Stage 10 completes the first-version delivery path for the CICD AI automation test platform.

Implemented in this stage:

- Backend validates Allure HTML report availability before returning a report URL.
- Backend serves static Allure HTML under `/reports/<run_id>/`.
- Backend restricts served reports to `ALLURE_REPORTS_ROOT`.
- Frontend module table report action is covered by a behavior test and opens the backend-controlled report URL.
- Final runbook is available at [test-platform-runbook.md](test-platform-runbook.md).

Not implemented in this stage:

- Custom Allure data visualization in the platform UI.
- Jenkins build detail page in Vue.
- Live Jenkins credential validation in automated tests.
- Full deployment E2E against real Jenkins and browser sessions.

## Report Access Design

The DRF report metadata endpoint remains:

```http
GET /api/test-runs/{id}/report/
```

The endpoint returns:

```json
{
  "report_url": "/reports/<run_id>/",
  "run_id": "<run_id>"
}
```

The endpoint returns `404` when the report is not safely available.

Static report routes:

```text
GET /reports/<run_id>/
GET /reports/<run_id>/<path>
```

Security constraints:

- `report_path/index.html` must exist.
- `report_path` must be inside `ALLURE_REPORTS_ROOT`.
- API responses do not expose local absolute filesystem paths.

Default report root:

```text
api-test/runtime/ci-runs
```

## TDD Record

### Backend RED

Command:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest tests/test_test_runs_api.py -v
```

Expected failures:

- Report endpoint returned a URL even when `index.html` was missing.
- `/reports/<run_id>/` route returned `404` because static report serving did not exist.
- Unsafe `report_path` outside the configured root was accepted.

### Backend GREEN

Command:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest tests/test_test_runs_api.py -v
```

Result:

```text
10 passed
```

### Frontend RED

Command:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm test -- module-pass-rate.spec.ts
```

Expected failure:

```text
Cannot call trigger on an empty DOMWrapper.
```

Reason: the module table Allure report action did not expose a stable user-facing test target.

### Frontend GREEN

Command:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm test -- module-pass-rate.spec.ts
```

Result:

```text
4 tests passed
```

## Final Verification

Backend:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest -v
```

Result:

```text
34 passed
```

Frontend:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm test
npm run build
```

Result:

```text
npm test -> 4 files passed, 13 tests passed
npm run build -> built successfully
```

Build notes:

- Existing `@vueuse/core` pure annotation warning remains.
- Existing large chunk warning remains.

api-test:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\api-test
python -m pytest tests -v
```

Result:

```text
26 passed
```

Jenkins static checks:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\jenkins
python -m pytest tests -v
```

Result:

```text
15 passed
```

## Integration Status

| Area | Status | Notes |
|------|--------|-------|
| api-test runner | Passed | Shared CI runner and node id retry tests passed |
| Jenkins Pipeline static checks | Passed | Parameters, stages, artifact preservation and report generation checks passed |
| DRF backend | Passed | Report URL and static report serving are covered |
| Vue frontend | Passed | Module table and failure dialog report actions are covered |
| Allure static report entry | Passed | `/reports/<run_id>/` serves `index.html` from configured root |
| Real Jenkins execution | Manual validation required | Automated tests avoid real Jenkins credentials |

## Known Issues and Follow-up

- `.idea/workspace.xml` is local IDE state and is not tracked by git. The api-test local regression reads it when present; this session restored the local `api-test/runpytest.py` configuration to satisfy the existing local test.
- Backend settings currently default MySQL to `MYSQL_PORT=3307`, while older planning text mentions `localhost:3306`. Docker deployment uses host port `3307`; future documentation cleanup should align all references around Docker defaults or an explicit local override.
- The frontend Jenkins task entry is still a placeholder URL. A dedicated Jenkins build detail page can be added after real Jenkins job metadata is available.
- Allure trend analytics and report parsing beyond failure summaries remain out of first-version scope.
