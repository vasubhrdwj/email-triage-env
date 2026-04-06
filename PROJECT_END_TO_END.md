# Email Triage Env: End-to-End Explanation

This document explains the `email-triage-env` project from start to finish in simple language, while still covering the important technical details.

## 1) What this project is

`email-triage-env` is a small reinforcement-learning style evaluation environment for email triage agents.

The agent is asked to read email data and output a structured decision:

- `priority`: how urgent the email is
- `category`: what kind of email it is
- `route_to`: which team should handle it
- `email_id`: which email to process next (only needed for inbox task)

The environment scores each action, returns feedback, and ends after either:

- enough correct work is done, or
- the max step limit is reached.

This lets you benchmark an LLM agent on realistic customer/support-style triage.

## 2) High-level architecture

There are five core layers:

1. **Static data layer** (`email_env/emails.py`)
   - Defines 8 realistic emails with ground truth labels.
2. **Schema layer** (`email_env/models.py`)
   - Pydantic models for observation, action, and reward.
3. **Environment logic** (`email_env/env.py`)
   - Implements `reset()`, `step()`, `state()`, and episode handling.
4. **Scoring/feedback logic** (`email_env/graders.py`)
   - Computes reward and textual coaching feedback.
5. **Interfaces**
   - HTTP API (`email_env/server.py`, `server/app.py`)
   - Inference runner (`inference.py`) for challenge-style logging.

In short:

**Data + labels -> environment step -> grader scores -> observation + reward -> agent retries/continues**

## 3) The task modes

The same environment supports 3 tasks:

### A) `priority`

- Single email
- Agent only needs priority correctness
- Reward normalized so correct priority can reach `1.0` before penalties
- Max attempts: `3`

### B) `full_triage`

- Single email
- Agent predicts `priority + category + route_to`
- Max attempts: `5`

### C) `inbox`

- Multi-email episode over 8 emails
- At each step, agent first chooses `email_id` to process, then triages it
- Final quality includes:
  - per-email triage correctness, plus
  - ordering quality (did the agent process emails in near-correct urgency order?)
- Max attempts: `12`

## 4) What data the environment uses

`email_env/emails.py` defines:

- `Email` dataclass
- `EMAILS` dictionary (`email_001` to `email_008`)
- `TRUE_INBOX_ORDER` for ideal processing sequence in inbox task

Each email contains:

- content fields (subject/body/sender/timestamp/thread history)
- labels (`true_priority`, `true_category`, `true_route`)
- metadata (`task_tags`, `difficulty_notes`)

This is the source of truth for grading.

## 5) How an episode works (core runtime flow)

The central class is `EmailTriageEnv`.

## 5.1 `reset(task_type)`

When reset is called:

1. Environment validates `task_type`.
2. Internal counters and histories are cleared:
   - `attempt`, `done`, rewards list, processed IDs, etc.
3. It loads task-specific emails from `TASK_EMAILS`.
4. For single-email tasks, it picks one deterministic random email (seeded RNG).
5. For inbox task, `current_email` starts as `None`; agent must choose via `email_id`.
6. It prepares `true_order`:
   - for inbox: uses predefined `TRUE_INBOX_ORDER`
   - for single-email tasks: sorts by priority level
7. Returns an initial `EmailTriageObservation`.

## 5.2 `step(action)`

`step` does different checks depending on task:

### Single-email tasks (`priority`, `full_triage`)

1. Increase attempt count.
2. Score action via `compute_reward(...)`.
3. Generate natural-language feedback.
4. Mark done if:
   - score is very high (`>= 0.90`), or
   - attempt limit reached.
5. Return `(observation, reward, done, info)`.

### Inbox task (`inbox`)

1. Increase attempt count.
2. Validate `email_id`:
   - missing/unknown -> zero reward + error feedback
   - already processed -> zero reward + error feedback
3. If valid:
   - mark this email processed
   - score triage fields using `full_triage` logic (without ordering bonus per step)
   - append triage total to inbox totals
4. Determine done when all emails processed or max attempts hit.
5. On done:
   - compute ordering score from actual processing sequence
   - compute episode composite score (`mean triage + ordering bonus`)
6. Return `(observation, reward, done, info)`.

Important behavior:

- Inbox ordering bonus is applied once at episode end, not repeatedly each step.
- Environment always puts reward details in `info["reward_breakdown"]`.
- Error-style steps (bad `email_id`) expose `info["last_action_error"]`.

## 6) Reward system in plain English

All reward logic is in `email_env/graders.py`.

## 6.1 Priority score

- Exact match: `0.30`
- Off by one level (e.g., high vs medium): `0.15`
- Otherwise: `0.0`

Priority levels are ordered as:
`urgent > high > medium > low`.

## 6.2 Category score

- Exact match: `0.30`
- Otherwise: `0.0`

## 6.3 Route score

- Exact true route: `0.30`
- If route is not true route but still acceptable for predicted category: `0.20`
- Otherwise: `0.0`

This allows partial credit for internally consistent but not ideal routing.

## 6.4 Step penalty

Penalty per late attempt:

- attempt 1: `0.00`
- attempt 2: `-0.05`
- attempt 3: `-0.10`
- etc.

This encourages solving quickly.

## 6.5 Total reward behavior

- For `full_triage`: total is sum of component scores + penalty, clamped to `[0, 1]`.
- For `priority`: priority score is normalized so exact match becomes `1.0` before penalty.
- For `inbox` episodes: final composite score is:
  - mean(per-email triage totals) + ordering score
  - capped at `1.0`.

## 6.6 Ordering score math

Ordering uses Kendall's tau correlation between:

- agent's processing order
- true urgency order

Then rescales to `[0.0, 0.20]`.

So perfect ordering contributes an extra `0.20` episode bonus.

## 7) Observation, action, and info contracts

All contracts are typed in `email_env/models.py`.

## 7.1 Observation (`EmailTriageObservation`)

Contains:

- `task_type`
- `current_email` (full message for current item; can be `None` initially in inbox)
- `inbox_summary` (for inbox task: compact list with processed flags)
- `attempt`, `max_attempts`
- `last_action`
- `last_feedback`

## 7.2 Action (`EmailTriageAction`)

Agent sends:

- `email_id` (required in practice for inbox)
- `priority`
- `category`
- `route_to`

## 7.3 Info dictionary from step

May contain:

- `reward_breakdown` (all component scores)
- `last_action_error` (validation errors, else `None`)
- `ordering_score` and `episode_composite_score` (on inbox completion)

## 8) HTTP API layer

`email_env/server.py` exposes a shared singleton environment via FastAPI.

Endpoints:

- `POST /reset?task_type=priority|full_triage|inbox`
- `POST /step` with JSON action body
- `GET /state` for compact internal state
- `GET /health` returns `{"status":"ok"}`

`server/app.py` is the runner entrypoint (`uv run server`) and starts Uvicorn on port `7860`.

`openenv.yaml` points OpenEnv runtime to `server.app:app` and the same port.

## 9) Inference script flow (`inference.py`)

`inference.py` is a reference "agent loop" that uses an OpenAI-compatible chat completions API.

It does:

1. Build client from env vars (`HF_TOKEN`/`API_KEY`, `API_BASE_URL`, `MODEL_NAME`).
2. Iterate over task configs (`priority`, `full_triage`, `inbox`).
3. For each task:
   - `env.reset(task)`
   - ask model for JSON action from observation
   - call `env.step(...)`
   - log one `[STEP]` line with reward/done/error
   - stop on done or max steps
4. On end, call `env.close()` and always print `[END]`.

The logs are formatted for challenge/benchmark ingestion.

## 10) Docker/runtime packaging

`server/Dockerfile` builds an OpenEnv-style image:

- installs dependencies with `uv sync`
- copies project and `.venv`
- exposes port `7860`
- healthchecks `/health`
- starts `uvicorn server.app:app --port 7860`

This matches local docs and `openenv.yaml`.

## 11) Testing and validation

`tests/test_graders.py` contains deterministic checks for:

- perfect scoring
- off-by-one priority partial credit
- route partial credit via category consistency
- step penalty effect
- ordering bonus behavior
- priority-only normalization to `1.0`

You can run:

```bash
PYTHONPATH=. uv run python tests/test_graders.py
```

## 12) End-to-end example (mental model)

Imagine `inbox` task:

1. Reset returns inbox summary of 8 emails.
2. Agent picks `email_001` with triage labels.
3. Env grades triage, returns reward + feedback.
4. Agent repeats with next unprocessed email.
5. If agent tries duplicate email ID, env returns zero reward with clear error.
6. After all 8 are processed (or attempts exhausted), env computes ordering bonus and episode composite score.
7. Episode ends; benchmark can compare score against threshold.

That is the complete closed loop: **observe -> act -> score -> feedback -> iterate -> episode score**.

## 13) Design choices worth knowing

- **Determinism for reproducibility:** seeded email selection in single-email tasks.
- **Partial-credit grading:** avoids brittle all-or-nothing scoring.
- **Actionable feedback:** `last_feedback` helps iterative self-correction.
- **Separation of concerns:** data, grading, env state, API, and inference are cleanly separated.
- **Challenge-compatible logs:** script output is machine-parseable (`[START]/[STEP]/[END]`).

## 14) If you want to extend this project

Common safe extension points:

- add more labeled emails in `emails.py`
- add task type + max attempts in `env.py`
- tune scoring weights in `graders.py`
- enforce stricter schema validation in `models.py`
- run multiple isolated env instances instead of singleton API env (for concurrent clients)

If you change label spaces (new categories/routes/priorities), update:

- `SYSTEM_PROMPT` in `inference.py`
- reward/category-route map in `graders.py`
- action field expectations in clients/tests.
