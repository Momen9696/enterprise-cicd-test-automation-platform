# Setup

## Requirements

- Python 3.12 or newer. The implementation was exercised on Python 3.13.2.
- Node.js 22 for the dashboard. Node 23 also works for the local Vite build.
- Optional: Docker with Compose, for the container layout. The Dockerfiles and Compose file are validated even when the Docker CLI is absent.

## API

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The first start creates `data/platform.db` and, when the database has no projects, inserts the labeled demo seed. Interactive docs are at http://127.0.0.1:8000/docs.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Dashboard

```bash
cd frontend
npm install
npm run dev
```

The UI is at http://127.0.0.1:5173. Leave the API key field as `local-operator-key` unless you changed `PLATFORM_API_KEY`. Use `local-viewer-key` to confirm write operations return 403.

## Playwright browsers

The default install does not download Chromium. The Playwright adapter still runs the approved scenarios and records an error result when the browser or the Python package is missing. To execute the portal fixture in a real browser:

```bash
python -m pip install -r backend/requirements-playwright.txt
python -m playwright install chromium
```

## Docker Compose

```bash
docker compose up --build
```

The API listens on port 8000 and the dashboard on port 8080. SQLite is stored in the `platform-data` volume at `/app/data/platform.db`. The backend process runs as `appuser`. The image includes Pytest and Robot Framework. It does not include Playwright browsers.

If `docker` is not on your PATH, run `python scripts/validate_docker.py`. That checks the Dockerfiles and Compose structure and reports that the CLI is unavailable.

## Tests

```bash
source .venv/bin/activate
pytest --junitxml=reports/junit-backend.xml
cd frontend && npm test && npm run lint && npm run build
```

Backend tests use a temporary SQLite file and the inline executor, so a local run finishes inside the request. They execute the real checkout Pytest suite, the intentional failure suite, and the Robot Framework smoke case.
