from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from email_env.env import EmailTriageEnv
from email_env.models import EmailTriageAction

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
    return {"status": "ok"}
