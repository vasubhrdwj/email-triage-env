"""
Email Triage Inference Script

Challenge STDOUT contract (see hackathon inference spec):
- One [START] per episode, one [STEP] per env.step(), one [END] after env.close(),
  with [END] always emitted (even on exception).
- reward / rewards / score use 2 decimal places; done and success are lowercase.
- error is last_action_error from the environment step info, or null.

Uses OpenAI-compatible client with API_BASE_URL, MODEL_NAME, HF_TOKEN (or API_KEY).
Optional: LOCAL_IMAGE_NAME / IMAGE_NAME when using remote Docker env clients (not used here).
"""

import json
import os
from typing import Any, List, Optional

from openai import OpenAI

from email_env.env import EmailTriageEnv
from email_env.models import EmailTriageAction

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
# Defaults only for API_BASE_URL and MODEL_NAME (per challenge).
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
# Documented for participants using from_docker_image(); unused by in-process EmailTriageEnv.
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
IMAGE_NAME = os.getenv("IMAGE_NAME")

BENCHMARK = "email-triage-env"

TASKS = [
    {"name": "priority", "max_steps": 3, "success_threshold": 0.60},
    {"name": "full_triage", "max_steps": 5, "success_threshold": 0.60},
    {"name": "inbox", "max_steps": 12, "success_threshold": 0.50},
]

TEMPERATURE = 0.1

SYSTEM_PROMPT = """
You are an expert email triage specialist. You will be given email content and must classify it.

You must respond with ONLY a valid JSON object. No explanation, no markdown, just JSON.

Required fields:
- "priority": one of ["urgent", "high", "medium", "low"]
- "category": one of ["billing", "technical", "complaint", "inquiry", "internal", "spam"]
- "route_to": one of ["billing_team", "tech_support", "customer_success", "management", "spam_folder", "hr_team"]
- "email_id": the email_id string (required for inbox task, use null for other tasks)

Priority guide:
- urgent: requires immediate action (system down, high-value customer threatening churn, legal risk)
- high: important, same-day response needed
- medium: normal business, next-day response ok
- low: informational, no action or action this week

Category guide:
- billing: payments, invoices, refunds, subscription issues
- technical: bugs, outages, API issues, access problems
- complaint: dissatisfied customer, escalation, threatening to leave or escalate
- inquiry: questions, pre-sales, information requests
- internal: from colleagues or internal systems
- spam: marketing, cold outreach, automated junk
"""


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def _format_step_error(error: Optional[str]) -> str:
    """Single-line value for the error= field; null when no env-reported error."""
    if error is None:
        return "null"
    return error.replace("\n", " ").replace("\r", " ")


def log_step(
    step: int,
    action: Any,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    if isinstance(action, dict):
        action_str = json.dumps(action, ensure_ascii=False).replace("\n", " ")
    else:
        action_str = str(action).replace("\n", " ")
    err_out = _format_step_error(error)
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action_str} reward={reward:.2f} "
        f"done={done_val} error={err_out}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


def get_agent_action(client: OpenAI, obs_dict: dict, history: list) -> dict:
    """Call LLM and return parsed action dict."""
    task_type = obs_dict["task_type"]
    current = obs_dict.get("current_email")
    inbox = obs_dict.get("inbox_summary")
    feedback = obs_dict.get("last_feedback")

    if task_type == "inbox":
        unprocessed = [e for e in (inbox or []) if not e["already_processed"]]
        user_content = f"""
Inbox overview (unprocessed emails):
{json.dumps(unprocessed, indent=2)}

Select one email to process. Read its email_id from the list above.
You must pick the MOST URGENT unprocessed email first.

Your last feedback: {feedback or 'None (first step)'}
History: {chr(10).join(history[-3:])}

Return JSON with: email_id, priority, category, route_to
"""
    else:
        user_content = f"""
Email to triage:
Subject: {current['subject']}
From: {current['sender_name']} <{current['sender_email']}>
Time: {current['timestamp']}
Body:
{current['body']}

Thread history: {json.dumps(current['thread_history']) if current['thread_history'] else 'None'}

Your last feedback: {feedback or 'None (first attempt)'}

Return JSON with: priority, category, route_to (email_id can be null)
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=TEMPERATURE,
            max_tokens=200,
        )
        text = (completion.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"[DEBUG] Model call failed: {e}", flush=True)
        return {
            "priority": "medium",
            "category": "inquiry",
            "route_to": "customer_success",
            "email_id": None,
        }


def run_task(client: OpenAI, env: EmailTriageEnv, task_cfg: dict) -> float:
    task_name = task_cfg["name"]
    max_steps = task_cfg["max_steps"]
    threshold = task_cfg["success_threshold"]

    rewards: List[float] = []
    steps_taken = 0
    success = False
    score = 0.0

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = env.reset(task_name)
        obs_dict = obs.model_dump()
        history: list = []

        for step in range(1, max_steps + 1):
            action_dict = get_agent_action(client, obs_dict, history)

            action = EmailTriageAction(
                email_id=action_dict.get("email_id"),
                priority=action_dict.get("priority", "medium"),
                category=action_dict.get("category", "inquiry"),
                route_to=action_dict.get("route_to", "customer_success"),
            )

            obs, reward, done, info = env.step(action)
            obs_dict = obs.model_dump()

            rewards.append(reward)
            steps_taken = step
            last_err: Optional[str] = info.get("last_action_error")
            if isinstance(last_err, str):
                step_error: Optional[str] = last_err
            else:
                step_error = None

            log_step(
                step=step,
                action=action.model_dump(),
                reward=reward,
                done=done,
                error=step_error,
            )

            history.append(f"Step {step}: {action.model_dump()} -> reward={reward:.2f}")

            if done:
                break

        if task_name == "inbox":
            composite = env.state().get("episode_composite_score")
            if composite is not None:
                score = float(composite)
            else:
                score = sum(rewards) / len(rewards) if rewards else 0.0
        else:
            score = sum(rewards) / len(rewards) if rewards else 0.0

        score = min(max(score, 0.0), 1.0)
        success = score >= threshold
        return score

    except Exception as exc:
        print(f"[DEBUG] Task episode failed: {exc}", flush=True)
        success = False
        score = 0.0
        return 0.0

    finally:
        try:
            env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error (container cleanup): {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = EmailTriageEnv()

    all_scores = {}
    for task_cfg in TASKS:
        score = run_task(client, env, task_cfg)
        all_scores[task_cfg["name"]] = score

    print(f"\n[SUMMARY] {json.dumps(all_scores)}", flush=True)


if __name__ == "__main__":
    main()
