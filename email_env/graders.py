from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from scipy.stats import kendalltau

from email_env.models import EmailTriageAction, EmailTriageReward

if TYPE_CHECKING:
    from email_env.emails import Email

PRIORITY_ORDER = ["urgent", "high", "medium", "low"]
STRICT_EPSILON = 1e-4

CATEGORY_ROUTE_MAP: dict[str, list[str]] = {
    "billing": ["billing_team"],
    "technical": ["tech_support"],
    "complaint": ["customer_success", "management"],
    "inquiry": ["customer_success", "tech_support"],
    "internal": ["hr_team", "management"],
    "spam": ["spam_folder"],
}


def score_priority(predicted: str, true: str) -> float:
    if predicted == true:
        return 0.30
    try:
        pred_idx = PRIORITY_ORDER.index(predicted)
        true_idx = PRIORITY_ORDER.index(true)
    except ValueError:
        return 0.0
    distance = abs(pred_idx - true_idx)
    if distance == 1:
        return 0.15
    return 0.0


def score_category(predicted: str, true: str) -> float:
    return 0.30 if predicted == true else 0.0


def score_route(predicted_route: str, true_route: str, predicted_category: str) -> float:
    if predicted_route == true_route:
        return 0.30
    acceptable = CATEGORY_ROUTE_MAP.get(predicted_category, [])
    if predicted_route in acceptable:
        return 0.20
    return 0.0


def score_ordering(agent_order: list[str], true_order: list[str]) -> float:
    """
    Kendall's tau between agent processing order and ground-truth priority order.
    Returns 0.0-0.20.
    """
    if len(agent_order) != len(true_order):
        return 0.0
    true_ranks = {eid: i for i, eid in enumerate(true_order)}
    try:
        agent_ranks = [true_ranks[eid] for eid in agent_order]
    except KeyError:
        return 0.0
    true_ranks_arr = list(range(len(true_order)))
    tau, _ = kendalltau(agent_ranks, true_ranks_arr)
    if tau is None or tau != tau:  # NaN guard
        return 0.0
    normalized = (tau + 1) / 2
    return round(normalized * 0.20, 4)


def _apply_step_penalty(attempt: int) -> float:
    return -0.05 * max(0, attempt - 1)


def _strict_unit_interval(value: float) -> float:
    """
    Keep values strictly inside (0, 1) to satisfy submission checks.
    """
    return max(STRICT_EPSILON, min(1.0 - STRICT_EPSILON, value))


def compute_reward(
    action: EmailTriageAction,
    true_email: Email,
    task_type: str,
    attempt: int,
    agent_order: Optional[list[str]] = None,
    true_order: Optional[list[str]] = None,
    include_ordering: bool = False,
) -> EmailTriageReward:
    """
    include_ordering: True only when computing the final inbox step reward that should carry ordering.
    For per-step inbox triage, pass include_ordering=False so ordering is applied once at episode end.
    """
    step_penalty = _apply_step_penalty(attempt)

    if task_type == "priority":
        priority_score = score_priority(action.priority, true_email.true_priority)
        category_score = 0.0
        route_score = 0.0
        ordering_score = 0.0
        # Normalize so exact priority => 1.0 before penalty (spec: Task 1 scores ~0.9–1.0 when correct).
        base_total = priority_score / 0.30 if priority_score > 0 else 0.0
    else:
        priority_score = score_priority(action.priority, true_email.true_priority)
        category_score = score_category(action.category, true_email.true_category)
        route_score = score_route(
            action.route_to, true_email.true_route, action.category
        )
        ordering_score = 0.0
        if task_type == "inbox" and include_ordering and agent_order and true_order:
            ordering_score = score_ordering(agent_order, true_order)
        base_total = priority_score + category_score + route_score + ordering_score

    total = round(_strict_unit_interval(base_total + step_penalty), 4)

    return EmailTriageReward(
        priority_score=priority_score,
        category_score=category_score,
        route_score=route_score,
        ordering_score=ordering_score,
        step_penalty=step_penalty,
        total=total,
    )


def compute_episode_score(per_email_totals: list[float], ordering_score: float) -> float:
    """Task 3: mean triage totals plus ordering bonus (ordering applied once)."""
    if not per_email_totals:
        return float(STRICT_EPSILON)
    base = float(sum(per_email_totals)) / len(per_email_totals)
    return float(_strict_unit_interval(base + float(ordering_score)))


def generate_feedback(
    action: EmailTriageAction,
    reward: EmailTriageReward,
    true_email: Email,
    task_type: str,
) -> str:
    parts: list[str] = []

    if task_type == "priority":
        if reward.priority_score == 0.30:
            parts.append("Priority: correct.")
        elif reward.priority_score == 0.15:
            parts.append(
                f"Priority: close but off by one level. You said '{action.priority}', "
                f"expected '{true_email.true_priority}'."
            )
        else:
            parts.append(
                f"Priority: incorrect. You said '{action.priority}', "
                f"expected '{true_email.true_priority}'."
            )
        return " ".join(parts)

    if reward.priority_score == 0.30:
        parts.append("Priority: correct.")
    elif reward.priority_score == 0.15:
        parts.append(
            f"Priority: close but off by one level. You said '{action.priority}', "
            f"expected '{true_email.true_priority}'."
        )
    else:
        parts.append(
            f"Priority: incorrect. You said '{action.priority}', "
            f"expected '{true_email.true_priority}'."
        )

    if reward.category_score == 0.30:
        parts.append("Category: correct.")
    else:
        parts.append(
            f"Category: incorrect. You said '{action.category}', "
            f"expected '{true_email.true_category}'."
        )

    if reward.route_score == 0.30:
        parts.append("Route: correct.")
    elif reward.route_score == 0.20:
        parts.append(
            f"Route: acceptable for your category but not the ideal route. "
            f"Expected '{true_email.true_route}'."
        )
    else:
        parts.append(
            f"Route: incorrect. You said '{action.route_to}', "
            f"expected '{true_email.true_route}'."
        )

    return " ".join(parts)
