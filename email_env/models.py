from typing import Any, Optional

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    email_id: str = Field(description="Stable identifier for this message.")
    subject: str = Field(description="Email subject line.")
    body: str = Field(description="Full message body.")
    sender_name: str = Field(description="Display name of the sender.")
    sender_email: str = Field(description="Sender email address.")
    timestamp: str = Field(description="ISO 8601 timestamp string.")
    thread_history: list[dict[str, Any]] = Field(
        description="Prior messages in the thread: list of {sender, body, timestamp}."
    )


class InboxSummary(BaseModel):
    email_id: str = Field(description="Stable identifier.")
    subject: str = Field(description="Subject line.")
    sender_name: str = Field(description="Display name of the sender.")
    sender_email: str = Field(description="Sender email address.")
    timestamp: str = Field(description="ISO 8601 timestamp string.")
    already_processed: bool = Field(
        description="True if this email has already been triaged in this episode."
    )


class EmailTriageObservation(BaseModel):
    task_type: str = Field(
        description='One of "priority", "full_triage", or "inbox".'
    )
    current_email: Optional[EmailMessage] = Field(
        default=None,
        description="The email currently being triaged (full body); None for inbox before first pick.",
    )
    inbox_summary: Optional[list[InboxSummary]] = Field(
        default=None,
        description="Task 3: list of all inbox rows with metadata; None for single-email tasks.",
    )
    attempt: int = Field(description="Number of steps taken so far in this episode.")
    max_attempts: int = Field(description="Maximum steps allowed for this task type.")
    last_action: Optional[dict[str, Any]] = Field(
        default=None,
        description="Previous action as a dict, if any.",
    )
    last_feedback: Optional[str] = Field(
        default=None,
        description="Natural-language feedback on the last action (for self-correction).",
    )


class EmailTriageAction(BaseModel):
    email_id: Optional[str] = Field(
        default=None,
        description="Task 3: which email to process; ignored for priority and full_triage.",
    )
    priority: str = Field(
        description='One of "urgent", "high", "medium", "low".',
    )
    category: str = Field(
        description=(
            'One of "billing", "technical", "complaint", "inquiry", "internal", "spam".'
        ),
    )
    route_to: str = Field(
        description=(
            'One of "billing_team", "tech_support", "customer_success", '
            '"management", "spam_folder", "hr_team".'
        ),
    )


class EmailTriageReward(BaseModel):
    priority_score: float = Field(description="Partial credit for priority (0.0, 0.15, or 0.30).")
    category_score: float = Field(description="Category match (0.0 or 0.30).")
    route_score: float = Field(description="Route match or consistency (0.0, 0.20, or 0.30).")
    ordering_score: float = Field(
        description="Kendall tau–based ordering bonus for inbox task (0.0–0.20); 0 for other tasks."
    )
    step_penalty: float = Field(description="Penalty for attempts after the first (negative or zero).")
    total: float = Field(description="Scalar reward for this step, clamped to [0.0, 1.0].")
