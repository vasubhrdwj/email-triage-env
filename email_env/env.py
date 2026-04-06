from __future__ import annotations

import random
from typing import Any, Optional

from email_env.emails import EMAILS, Email, TRUE_INBOX_ORDER
from email_env.graders import (
    compute_episode_score,
    compute_reward,
    generate_feedback,
    score_ordering,
)
from email_env.models import (
    EmailMessage,
    EmailTriageAction,
    EmailTriageObservation,
    EmailTriageReward,
    InboxSummary,
)


class EmailTriageEnv:
    TASK_EMAILS: dict[str, list[str]] = {
        "priority": ["email_001", "email_002", "email_003"],
        "full_triage": ["email_004", "email_005", "email_006"],
        "inbox": [
            "email_001",
            "email_002",
            "email_003",
            "email_004",
            "email_005",
            "email_006",
            "email_007",
            "email_008",
        ],
    }

    MAX_ATTEMPTS: dict[str, int] = {
        "priority": 3,
        "full_triage": 5,
        "inbox": 12,
    }

    def __init__(self, rng_seed: int = 42) -> None:
        self._rng_seed = rng_seed
        self.task_type: Optional[str] = None
        self.current_email: Optional[Email] = None
        self.emails_to_process: list[Email] = []
        self.attempt: int = 0
        self.done: bool = False
        self.all_rewards: list[float] = []
        self.agent_processing_order: list[str] = []
        self.processed_email_ids: set[str] = set()
        self.inbox_triage_totals: list[float] = []
        self.episode_composite_score: Optional[float] = None
        self._last_action_dict: Optional[dict[str, Any]] = None
        self.true_order: list[str] = []

    def reset(self, task_type: str = "priority") -> EmailTriageObservation:
        if task_type not in self.TASK_EMAILS:
            raise ValueError(f"Unknown task_type: {task_type}")

        self.task_type = task_type
        self.attempt = 0
        self.done = False
        self.all_rewards = []
        self.agent_processing_order = []
        self.processed_email_ids = set()
        self.inbox_triage_totals = []
        self.episode_composite_score = None
        self._last_action_dict = None

        email_ids = self.TASK_EMAILS[task_type]
        self.emails_to_process = [EMAILS[eid] for eid in email_ids]

        rng = random.Random(self._rng_seed)
        if task_type in ("priority", "full_triage"):
            self.current_email = rng.choice(self.emails_to_process)
        else:
            self.current_email = None

        if task_type == "inbox":
            self.true_order = [eid for eid in TRUE_INBOX_ORDER if eid in email_ids]
        else:
            self.true_order = [
                e.email_id
                for e in sorted(
                    self.emails_to_process,
                    key=lambda e: ["urgent", "high", "medium", "low"].index(e.true_priority),
                )
            ]

        return self._build_observation(feedback=None)

    def step(self, action: EmailTriageAction) -> tuple[EmailTriageObservation, float, bool, dict[str, Any]]:
        self.attempt += 1
        action_dict = action.model_dump()
        info: dict[str, Any] = {}

        if self.task_type == "inbox":
            eid = action.email_id
            if not eid or eid not in EMAILS:
                reward_obj = EmailTriageReward(
                    priority_score=0.0,
                    category_score=0.0,
                    route_score=0.0,
                    ordering_score=0.0,
                    step_penalty=0.0,
                    total=0.0,
                )
                feedback = (
                    "Invalid or missing email_id. Choose an email_id from inbox_summary "
                    "that is not yet processed."
                )
                self._last_action_dict = action_dict
                info["last_action_error"] = feedback
                self._finalize_inbox_error_step(reward_obj, info)
                obs = self._build_observation(feedback=feedback)
                return obs, reward_obj.total, self.done, info

            if eid in self.processed_email_ids:
                reward_obj = EmailTriageReward(
                    priority_score=0.0,
                    category_score=0.0,
                    route_score=0.0,
                    ordering_score=0.0,
                    step_penalty=0.0,
                    total=0.0,
                )
                feedback = (
                    f"That email ({eid}) was already processed. Pick a different "
                    "unprocessed email_id from the inbox summary."
                )
                self._last_action_dict = action_dict
                info["last_action_error"] = feedback
                self._finalize_inbox_error_step(reward_obj, info)
                obs = self._build_observation(feedback=feedback)
                return obs, reward_obj.total, self.done, info

            self.agent_processing_order.append(eid)
            self.processed_email_ids.add(eid)
            email = EMAILS[eid]
            self.current_email = email

            # One triage decision per email; do not apply cross-email step penalties.
            reward_obj = compute_reward(
                action=action,
                true_email=email,
                task_type="full_triage",
                attempt=1,
                include_ordering=False,
            )
            self.inbox_triage_totals.append(reward_obj.total)
            feedback = generate_feedback(action, reward_obj, email, task_type="full_triage")

            self._last_action_dict = action_dict
            self.all_rewards.append(reward_obj.total)

            self.done = (
                len(self.processed_email_ids) == len(self.emails_to_process)
                or self.attempt >= self.MAX_ATTEMPTS["inbox"]
            )

            ordering_sc = score_ordering(self.agent_processing_order, self.true_order)
            if self.done:
                self.episode_composite_score = compute_episode_score(
                    self.inbox_triage_totals, ordering_sc
                )
                info["ordering_score"] = ordering_sc
                info["episode_composite_score"] = self.episode_composite_score
            else:
                self.episode_composite_score = None

            info["reward_breakdown"] = reward_obj.model_dump()
            info["last_action_error"] = None
            obs = self._build_observation(feedback=feedback)
            return obs, reward_obj.total, self.done, info

        # Single-email tasks
        assert self.current_email is not None
        email = self.current_email
        tt = self.task_type or "priority"

        reward_obj = compute_reward(
            action=action,
            true_email=email,
            task_type=tt,
            attempt=self.attempt,
        )
        feedback = generate_feedback(action, reward_obj, email, task_type=tt)

        self._last_action_dict = action_dict
        self.all_rewards.append(reward_obj.total)

        self.done = (reward_obj.total >= 0.90) or (
            self.attempt >= self.MAX_ATTEMPTS[tt]
        )

        info["reward_breakdown"] = reward_obj.model_dump()
        info["last_action_error"] = None
        obs = self._build_observation(feedback=feedback)
        return obs, reward_obj.total, self.done, info

    def close(self) -> None:
        """Release resources (no-op for in-process env; call before [END] per challenge contract)."""

    def _finalize_inbox_error_step(
        self,
        reward_obj: EmailTriageReward,
        info: dict[str, Any],
    ) -> None:
        self.all_rewards.append(reward_obj.total)
        self.done = self.attempt >= self.MAX_ATTEMPTS["inbox"]
        if self.done:
            ordering_sc = score_ordering(self.agent_processing_order, self.true_order)
            self.episode_composite_score = compute_episode_score(
                self.inbox_triage_totals, ordering_sc
            )
            info["ordering_score"] = ordering_sc
            info["episode_composite_score"] = self.episode_composite_score
        info["reward_breakdown"] = reward_obj.model_dump()

    def state(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "attempt": self.attempt,
            "done": self.done,
            "rewards_so_far": self.all_rewards,
            "emails_processed": list(self.processed_email_ids),
            "episode_composite_score": self.episode_composite_score,
        }

    def _build_observation(self, feedback: Optional[str]) -> EmailTriageObservation:
        inbox_summary = None
        if self.task_type == "inbox":
            inbox_summary = [
                InboxSummary(
                    email_id=e.email_id,
                    subject=e.subject,
                    sender_name=e.sender_name,
                    sender_email=e.sender_email,
                    timestamp=e.timestamp,
                    already_processed=e.email_id in self.processed_email_ids,
                )
                for e in self.emails_to_process
            ]

        current = None
        if self.current_email:
            e = self.current_email
            current = EmailMessage(
                email_id=e.email_id,
                subject=e.subject,
                body=e.body,
                sender_name=e.sender_name,
                sender_email=e.sender_email,
                timestamp=e.timestamp,
                thread_history=e.thread_history,
            )

        return EmailTriageObservation(
            task_type=self.task_type or "priority",
            current_email=current,
            inbox_summary=inbox_summary,
            attempt=self.attempt,
            max_attempts=self.MAX_ATTEMPTS[self.task_type or "priority"],
            last_action=self._last_action_dict,
            last_feedback=feedback,
        )
