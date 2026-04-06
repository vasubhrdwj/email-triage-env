from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from email_env.env import EmailTriageEnv
from email_env.models import EmailTriageAction, EmailTriageObservation

app = FastAPI(title="Email Triage Environment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

env = EmailTriageEnv()


@app.post("/reset")
def reset(task_type: str = Query("priority", description="priority | full_triage | inbox")):
    obs = env.reset(task_type)
    return obs.model_dump()


@app.post("/step")
def step(action: EmailTriageAction):
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": reward,
        "done": done,
        "info": info,
    }


@app.get("/state")
def state():
    return env.state()


@app.get("/health")
def health():
    # OpenEnv validator expects "healthy" specifically.
    return {"status": "healthy"}


@app.get("/metadata")
def metadata():
    return {
        "name": "email-triage-env",
        "description": "RL-style email triage environment with reset/step/state API.",
        "version": "1.0.0",
    }


@app.get("/schema")
def schema():
    return {
        "action": EmailTriageAction.model_json_schema(),
        "observation": EmailTriageObservation.model_json_schema(),
        "state": {
            "type": "object",
            "properties": {
                "task_type": {"type": ["string", "null"]},
                "attempt": {"type": "integer"},
                "done": {"type": "boolean"},
                "rewards_so_far": {"type": "array", "items": {"type": "number"}},
                "emails_processed": {"type": "array", "items": {"type": "string"}},
                "episode_composite_score": {"type": ["number", "null"]},
            },
            "required": [
                "task_type",
                "attempt",
                "done",
                "rewards_so_far",
                "emails_processed",
                "episode_composite_score",
            ],
            "additionalProperties": True,
        },
    }


@app.post("/mcp")
async def mcp(request: Request):
    # Minimal JSON-RPC compliant response so endpoint is reachable by validators.
    payload: dict[str, Any] = await request.json()
    req_id = payload.get("id")
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": "MCP methods are not implemented for this environment.",
        },
    }
