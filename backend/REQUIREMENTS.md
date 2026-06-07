# Python dependencies

**Python:** 3.12+ locally; Docker/CI use **3.12** exactly. If you only have another
3.12+ release (e.g. 3.14), use that for the venv — see below.

Each file lists **direct dependencies only** with pinned versions (`==`). Pip resolves
transitive packages at install time — no pip-tools or lock-file step required.

## Files

| File | Install when… |
|------|----------------|
| `requirements.txt` | Running the **API** (`uvicorn`, Docker `backend` service) |
| `requirements-dev.txt` | **Local development** and **CI** (API + pytest + ruff + httpx) |
| `requirements-pipeline.txt` | Running the **Prefect pipeline** (`feature_pipeline`, Docker `pipeline` service) |
| `requirements-ingest.txt` | Running **data ingest scripts** under `scripts/ingest/` |

Extra files include the API stack via `-r requirements.txt`.

## Virtual environment (recommended)

Use a venv so project packages stay isolated from your system Python.

### Windows (PowerShell)

```powershell
cd backend

# 1. Create venv (once) — use any installed 3.12+ interpreter
py -m venv .venv
# Optional: match Docker exactly (install first: py install 3.12)
# py -3.12 -m venv .venv

# 2. Activate (every new terminal)
.\.venv\Scripts\Activate.ps1

# If activation is blocked:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install what you need (pick one or combine)
pip install -r requirements-dev.txt      # API + tests + lint (most developers)
# pip install -r requirements-ingest.txt # add if you run scripts/ingest/
# pip install -r requirements-pipeline.txt # add if you run Prefect flows locally
```

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Deactivate

```bash
deactivate
```

### Which file should I install?

| What you're doing | Command |
|-------------------|---------|
| Run API locally | `pip install -r requirements.txt` (minimal) or `requirements-dev.txt` (typical) |
| Run tests / lint | `pip install -r requirements-dev.txt` |
| Load parquet / OSM scripts | `pip install -r requirements-ingest.txt` |
| Run weekly/historical pipeline | `pip install -r requirements-pipeline.txt` |
| Full local stack | `pip install -r requirements-dev.txt` then ingest/pipeline files as needed |

`requirements-dev.txt` already includes everything in `requirements.txt`.

## Docker

| Service | Image installs |
|---------|----------------|
| `backend` | `requirements.txt` only (lean API image) |
| `pipeline` | `requirements-pipeline.txt` (API + Prefect) |

```bash
docker compose up -d              # API — no Prefect/pandas in image
docker compose --profile pipeline run --rm pipeline   # pipeline image
```

## Updating dependencies

1. Edit the version in the relevant `requirements*.txt` file.
2. Reinstall in your venv: `pip install -r requirements-dev.txt`
3. Run tests: `pytest tests/unit -v`

To discover what is installed after an upgrade:

```bash
pip list
# or, to snapshot everything (optional):
pip freeze > requirements-lock.txt
```

Commit only `requirements*.txt` unless you deliberately want a full `pip freeze` lock file.

## Environment variables

Dependencies do not replace configuration. Set `DATABASE_URL` (and other vars from the root
`.env`) before running the API, scripts, or pipeline. See the project [README](../README.md).
