# Stage 7: Jenkins Query and Trigger API

## Scope

Stage 7 adds backend support for Jenkins job/build query, console log query and parameterized build trigger.

Implemented:
- `apps.jenkins_integration` app.
- Jenkins HTTP client using `requests.Session`.
- DRF endpoints under `/api/jenkins/`.
- Build trigger parameter conversion aligned with `jenkins/scripts/api-test-pipeline.groovy`.
- Minimal `JenkinsBuildRecord` model for queued trigger records.

Not included:
- Real Jenkins environment validation. Tests use fake responses.
- Jenkins webhook handling.
- Allure report static serving. That remains Stage 10.

## Configuration

Configure with environment variables or local private settings:

```text
JENKINS_BASE_URL
JENKINS_USERNAME
JENKINS_API_TOKEN
JENKINS_DEFAULT_JOB
```

Do not commit real Jenkins URL, username or API token.

## API

All endpoints require DRF Token authentication.

```text
GET  /api/jenkins/jobs/
GET  /api/jenkins/jobs/{job_name}/builds/
GET  /api/jenkins/jobs/{job_name}/builds/{build_number}/
GET  /api/jenkins/jobs/{job_name}/builds/{build_number}/console/
POST /api/jenkins/jobs/{job_name}/build/
```

## Trigger Request

Backend request:

```json
{
  "case_path": "test_case/test_gbif_case",
  "pytest_node_ids": ["case1", "case2"],
  "retry_mode": "selected",
  "retry_count": 1,
  "clean_allure": true,
  "open_report": false
}
```

Jenkins parameters sent to Pipeline:

```text
CASE_PATH=test_case/test_gbif_case
PYTEST_NODE_IDS=case1
case2
RETRY_MODE=selected
RETRY_COUNT=1
CLEAN_ALLURE=true
OPEN_REPORT=false
```

These match Stage 4 Pipeline parameters.

## Test Results

RED:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest tests/test_jenkins_client.py -v
python -m pytest tests/test_jenkins_api.py -v
```

Result:
- `ModuleNotFoundError: No module named 'apps.jenkins_integration'`

GREEN:

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pytest tests/test_jenkins_client.py tests/test_jenkins_api.py -v
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -v
```

Result:
- Stage 7 focused tests: `12 passed`
- Django check: `System check identified no issues`
- Migration check: `No changes detected`
- Backend regression: `31 passed`

## Notes

- Client tests use fake HTTP responses and do not depend on a real Jenkins service.
- API tests monkeypatch the Jenkins client factory and do not use real Jenkins credentials.
- Job names are URL-escaped before being inserted into Jenkins job URLs.
