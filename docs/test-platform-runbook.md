# Test Platform Runbook

## Purpose

This runbook records how to run the first version of the CICD AI automation test platform locally. It covers the pytest executor, Jenkins Pipeline, DRF backend, Vue 3 frontend, Allure report access and failure retry operations.

The project remains a generic test platform. Do not place real passwords, tokens, cookies, Jenkins API tokens or production URLs in this document.

## Prerequisites

- Python 3.12 or compatible local Python.
- Node.js and npm for the Vue 3 frontend.
- Allure CLI if HTML report generation is required locally.
- Docker Compose if using the provided MySQL and Jenkins services.
- Local MySQL available on the port configured by `MYSQL_PORT`.

Docker service details are maintained in [docker/DEPLOYMENT.md](../docker/DEPLOYMENT.md).

## Start MySQL and Jenkins

Windows PowerShell:

```powershell
.\scripts\deploy-docker.ps1
```

Git Bash or Linux/macOS:

```bash
bash scripts/deploy-docker.sh
```

Default service URLs:

```text
Jenkins: http://localhost:8080
MySQL:   127.0.0.1:3307
```

The local `.env` file is private and must not be committed.

## Run api-test

Install dependencies:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\api-test
python -m pip install -r requirements.txt
```

Run the demo module and clean old Allure results:

```powershell
python runpytest.py --case-path test_case/test_gbif_case --clean
```

Run the shared CI runner used by Jenkins and DRF:

```powershell
python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id local-smoke --clean
```

Runtime output:

```text
api-test/runtime/ci-runs/<run_id>/
├── summary.json
├── failed_nodeids.json
├── console.log
├── allure-results/
└── allure-report/
```

## Start the Backend

Install dependencies:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pip install -r requirements.txt
```

Set local MySQL environment variables. Keep passwords private:

```powershell
$env:MYSQL_DATABASE="ai_api_test_platform"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="<local mysql password>"
$env:MYSQL_PORT="3307"
```

The backend serves Allure HTML reports only from `ALLURE_REPORTS_ROOT`. By default this is:

```text
D:\AI\Hermes\dev\AiApiTest-DWP\api-test\runtime\ci-runs
```

Override when needed:

```powershell
$env:ALLURE_REPORTS_ROOT="D:\AI\Hermes\dev\AiApiTest-DWP\api-test\runtime\ci-runs"
```

Run migrations and start DRF:

```powershell
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/api/docs/
```

## Start the Frontend

Install dependencies:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm install
```

Start Vite:

```powershell
npm run dev -- --port 5173
```

Open:

```text
http://127.0.0.1:5173/platform
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Jenkins Pipeline

Create a Jenkins Pipeline job that uses:

```text
jenkins/Jenkinsfile
```

Main parameters:

```text
CASE_PATH=test_case/test_gbif_case
PYTEST_NODE_IDS=
RETRY_MODE=none|selected|all-failed|module
RETRY_COUNT=0
CLEAN_ALLURE=true
OPEN_REPORT=false
```

The Groovy Pipeline delegates pytest execution to:

```text
api-test/tools/ci_runner.py
```

This keeps retry logic centralized in `api-test`.

## View Allure Reports

The backend report metadata endpoint is:

```http
GET /api/test-runs/{id}/report/
```

Successful response:

```json
{
  "report_url": "/reports/<run_id>/",
  "run_id": "<run_id>"
}
```

The backend returns `404` when:

- `report_path` is empty.
- `report_path/index.html` does not exist.
- `report_path` is outside `ALLURE_REPORTS_ROOT`.

The static report entry is:

```text
http://127.0.0.1:8000/reports/<run_id>/
```

The frontend opens this URL from the module table and failure dialog Allure report actions.

## Failure Retry

Retry selected failure cases:

```http
POST /api/test-runs/{id}/retry-selected/
```

Retry all failed cases:

```http
POST /api/test-runs/{id}/retry-all-failed/
```

Retry a whole module:

```http
POST /api/test-runs/{id}/retry-module/
```

All retry APIs call the shared `api-test` runner adapter and store a new `TestRun` record.

## Verification Commands

Backend:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest -v
```

Frontend:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm test
npm run build
```

API test core:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\api-test
python -m pytest tests -v
```

Jenkins static checks:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\jenkins
python -m pytest tests -v
```

## Known Limits

- Jenkins validation in automated tests uses fake HTTP/session objects. Real Jenkins credentials and URLs must be configured locally.
- Allure trend analytics are not implemented in the first version.
- Frontend Jenkins build detail currently opens a placeholder route. Backend Jenkins APIs exist for later detail-page integration.
- Full browser E2E against a live backend and live Jenkins is still a deployment-level validation task.
