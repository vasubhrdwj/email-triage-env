"""Manual grader checks (run: python tests/test_graders.py from email-triage-env)."""

from email_env.emails import EMAILS
from email_env.graders import (
    compute_episode_score,
    compute_reward,
    score_ordering,
    score_priority,
)
from email_env.models import EmailTriageAction


def test_perfect_triage_step1() -> None:
    em = EMAILS["email_004"]
    act = EmailTriageAction(
        priority=em.true_priority,
        category=em.true_category,
        route_to=em.true_route,
    )
    r = compute_reward(act, em, "full_triage", attempt=1)
    assert abs(r.total - 0.9) < 1e-6, r.total


def test_priority_off_by_one() -> None:
    em = EMAILS["email_004"]  # high
    act = EmailTriageAction(
        priority="medium",
        category=em.true_category,
        route_to=em.true_route,
    )
    r = compute_reward(act, em, "full_triage", attempt=1)
    # 0.15 + 0.30 + 0.30 = 0.75
    assert abs(r.total - 0.75) < 1e-6, r.total


def test_wrong_category_consistent_route() -> None:
    em = EMAILS["email_004"]  # billing / billing_team
    act = EmailTriageAction(
        priority=em.true_priority,
        category="technical",
        route_to="tech_support",
    )
    r = compute_reward(act, em, "full_triage", attempt=1)
    assert r.route_score == 0.20
    assert r.category_score == 0.0


def test_step2_penalty() -> None:
    em = EMAILS["email_004"]
    act = EmailTriageAction(
        priority=em.true_priority,
        category=em.true_category,
        route_to=em.true_route,
    )
    r1 = compute_reward(act, em, "full_triage", attempt=1)
    r2 = compute_reward(act, em, "full_triage", attempt=2)
    assert r2.step_penalty < r1.step_penalty
    assert r2.total < r1.total


def test_task3_ordering_bonus() -> None:
    true_order = ["a", "b", "c", "d", "e", "f", "g", "h"]
    agent_order = list(true_order)
    s = score_ordering(agent_order, true_order)
    assert s == 0.20
    base = [0.9] * 8
    ep = compute_episode_score(base, s)
    assert 0.0 < ep < 1.0


def test_priority_only_normalized() -> None:
    em = EMAILS["email_001"]
    act = EmailTriageAction(
        priority=em.true_priority,
        category="spam",
        route_to="spam_folder",
    )
    r = compute_reward(act, em, "priority", attempt=1)
    assert 0.0 < r.total < 1.0


if __name__ == "__main__":
    test_perfect_triage_step1()
    test_priority_off_by_one()
    test_wrong_category_consistent_route()
    test_step2_penalty()
    test_task3_ordering_bonus()
    test_priority_only_normalized()
    print("All grader tests passed.")
