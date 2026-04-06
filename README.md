---
title: Email Triage Env
emoji: 📚
colorFrom: green
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# Email Triage (OpenEnv)

LLM agents triage a fixed inbox: **priority**, **category**, **route**, and (task `inbox`) **processing order**. Logic lives under `email_env/`; HTTP API is `email_env.server` behind `server/app.py`.

---

## Quick start (what you run day to day)

```bash
cd email-triage-env
uv sync
```

**Run the API (default port 7860, matches `openenv.yaml` and Hugging Face Spaces):**

```bash
uv run server
# same as: uvicorn server.app:app --host 0.0.0.0 --port 7860
```

**Try it:**

```bash
curl -s -X POST "http://localhost:7860/reset?task_type=priority" | jq .
curl -s -X POST "http://localhost:7860/step" \
  -H "Content-Type: application/json" \
  -d '{"priority":"urgent","category":"technical","route_to":"tech_support","email_id":null}' | jq .
curl -s http://localhost:7860/health
```

**Validate with OpenEnv CLI:**

```bash
uv run openenv validate
# optional: openenv validate --url http://localhost:7860
```

**Run inference (needs `HF_TOKEN` / `API_KEY` and a chat-completions API):**

```bash
export HF_TOKEN=...
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
uv run python inference.py
```

**Grader smoke tests:**

```bash
PYTHONPATH=. uv run python tests/test_graders.py
```

---

## Docker (same layout as OpenEnv template)

**Port:** The app listens on **7860** (matches `openenv.yaml`, `README` front matter `app_port`, HF Spaces). Older docs that used **8000** are wrong for this repo unless you change the port in **`server/Dockerfile`**, **`server/app.py`**, and **`openenv.yaml`** together.

**Daemon must be running:** If you see `failed to connect to the docker API at unix:///var/run/docker.sock`, open **Docker Desktop** (macOS) and wait until it says Docker is running, then retry. The `legacy builder` / BuildKit message is a warning; fixing the daemon is what unblocks `docker build`.

**6 — Docker from this folder** (build context = current directory):

```bash
cd /path/to/email-triage-env
docker build -t email-triage-env:latest -f server/Dockerfile .
docker run --rm -p 7860:7860 email-triage-env:latest
```

Then open `http://localhost:7860/health` (or use the `curl` examples in Quick start with port **7860**).

**7 — Integrate into an OpenEnv monorepo** (copy the env to e.g. `envs/email_triage_env`, then from **that repo’s root**):

```bash
docker build -t email-triage-env:latest -f envs/email_triage_env/server/Dockerfile envs/email_triage_env
docker run --rm -p 7860:7860 email-triage-env:latest
```

Adjust `envs/email_triage_env` to the path where you placed this project.

---

## Layout

| Path | Role |
| --- | --- |
| `email_env/env.py` | `EmailTriageEnv`: reset / step / state / close |
| `email_env/server.py` | FastAPI: `/reset`, `/step`, `/state`, `/health` |
| `server/app.py` | Uvicorn entry (`server` script in `pyproject.toml`) |
| `server/Dockerfile` | Production image (`uv sync`, port 7860) |
| `inference.py` | Challenge-style stdout logging + LLM loop |
| `openenv.yaml` | `app: server.app:app`, `port: 7860` |
| `pyproject.toml` + `uv.lock` | Dependencies (`uv sync`) |

---

## Tasks

| `task_type` | Meaning |
| --- | --- |
| `priority` | One email; priority score only (normalized). |
| `full_triage` | One email; priority + category + route. |
| `inbox` | Eight emails; triage + ordering score in `state["episode_composite_score"]`. |

Reward details: see `email_env/graders.py`.

---

## Baseline scores (fill after runs)

| Task | Model | Score | Notes |
| --- | --- | --- | --- |
| priority | Qwen/Qwen2.5-72B-Instruct | 1.00 | 1 step; success=true |
| full_triage | Qwen/Qwen2.5-72B-Instruct | 0.90 | 1 step; success=true |
| inbox | Qwen/Qwen2.5-72B-Instruct | 0.6732 | 8 steps; success=true |
