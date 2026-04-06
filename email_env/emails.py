from dataclasses import dataclass, field
from typing import Any


@dataclass
class Email:
    email_id: str
    subject: str
    body: str
    sender_name: str
    sender_email: str
    timestamp: str
    thread_history: list[dict[str, Any]]
    true_priority: str
    true_category: str
    true_route: str
    task_tags: list[str]
    difficulty_notes: str


EMAIL_001 = Email(
    email_id="email_001",
    subject="PRODUCTION DOWN - all API calls failing",
    sender_name="Ops Alerts",
    sender_email="ops-alert@company.com",
    timestamp="2026-04-02T14:45:00Z",
    thread_history=[],
    body=(
        "Our monitoring detected a 100% failure rate on POST /api/v2/orders starting at 14:32 UTC. "
        "We are seeing HTTP 500 responses across all regions and the error budget is fully exhausted. "
        "Approximately 3,000 active customers are currently unable to place orders. "
        "On-call has paged the platform team; we need an immediate rollback or hotfix. "
        "Please treat this as a Sev-1 incident and join the bridge channel linked in the runbook."
    ),
    true_priority="urgent",
    true_category="technical",
    true_route="tech_support",
    task_tags=["priority", "full_triage", "inbox"],
    difficulty_notes="Easy — subject, sender, and body all scream outage.",
)

EMAIL_002 = Email(
    email_id="email_002",
    subject="Quick question about my account",
    sender_name="Michael Chen",
    sender_email="michael.chen@fortune500corp.com",
    timestamp="2026-04-02T09:12:00Z",
    thread_history=[
        {
            "sender": "support@ourcompany.com",
            "body": "Thanks for reaching out — we will get back to you shortly.",
            "timestamp": "2026-03-15T10:00:00Z",
        }
    ],
    body=(
        "Hi, I've been trying to reach someone for three weeks now without a substantive reply. "
        "Our enterprise contract renews this Friday and we are actively evaluating alternatives "
        "because of a persistent billing discrepancy across our last four invoices. "
        "This message is my final attempt before I escalate to our procurement and legal teams. "
        "I need a named owner and a written plan by EOD tomorrow."
    ),
    true_priority="urgent",
    true_category="complaint",
    true_route="customer_success",
    task_tags=["priority", "full_triage", "inbox"],
    difficulty_notes="Medium — subject sounds casual; body shows escalation and churn risk.",
)

EMAIL_003 = Email(
    email_id="email_003",
    subject="URGENT: Your account will be suspended",
    sender_name="Premium Offers",
    sender_email="noreply@marketing-blasts-xyz.net",
    timestamp="2026-04-01T08:00:00Z",
    thread_history=[],
    body=(
        "Dear Valued Customer, Act now! Your account privileges expire in 24 hours unless you renew. "
        "Click here to claim 50% off our premium membership and unlock exclusive features. "
        "This is a limited-time promotional message; no reply is required. "
        "Unsubscribe link: [link]. If you did not request this, you may ignore this email."
    ),
    true_priority="low",
    true_category="spam",
    true_route="spam_folder",
    task_tags=["priority", "full_triage", "inbox"],
    difficulty_notes="Medium — subject mimics security; body is clearly marketing/spam.",
)

EMAIL_004 = Email(
    email_id="email_004",
    subject="Invoice #INV-2024-8821 discrepancy",
    sender_name="Accounts Payable",
    sender_email="ap@globallogistics.com",
    timestamp="2026-04-02T11:20:00Z",
    thread_history=[],
    body=(
        "Hello, we received invoice #INV-2024-8821 for $24,500 but our purchase order was for $21,200. "
        "Please send a corrected invoice or a credit note for the $3,300 difference before we release payment. "
        "Our AP team has placed the payment on hold until the amounts reconcile. "
        "We need documentation by end of week to avoid delaying the vendor scorecard review."
    ),
    true_priority="high",
    true_category="billing",
    true_route="billing_team",
    task_tags=["full_triage", "inbox"],
    difficulty_notes="Easy — clear billing and finance routing.",
)

EMAIL_005 = Email(
    email_id="email_005",
    subject="Updated remote work policy — action required by Friday",
    sender_name="Sarah Okonkwo",
    sender_email="sarah.okonkwo@ourcompany.com",
    timestamp="2026-04-02T07:30:00Z",
    thread_history=[],
    body=(
        "Hi team, please review and electronically sign the updated remote work policy in the HR portal. "
        "Legal requires all signatures by EOD Friday; this applies to every employee regardless of location. "
        "The policy summary and FAQ are attached to the HR announcement. "
        "If you have questions, reply to this thread or open a ticket with People Ops."
    ),
    true_priority="medium",
    true_category="internal",
    true_route="hr_team",
    task_tags=["full_triage", "inbox"],
    difficulty_notes="Easy — internal HR policy and signature workflow.",
)

EMAIL_006 = Email(
    email_id="email_006",
    subject="Feedback on recent experience",
    sender_name="Priya Sharma",
    sender_email="priya.sharma@startup.io",
    timestamp="2026-04-01T16:05:00Z",
    thread_history=[
        {
            "sender": "priya.sharma@startup.io",
            "body": "Following up — we still have not heard back on the earlier outage thread.",
            "timestamp": "2026-03-30T09:00:00Z",
        }
    ],
    body=(
        "I want to share candid feedback after last week. Your API experienced three separate outages "
        "and my engineering team lost roughly six hours of integration work. We are on the Pro plan and "
        "expect reliability in line with your published commitments. I am not asking for compensation today, "
        "but I need clarity on your SLA remedies and concrete remediation steps so this does not recur. "
        "Please have a customer success manager reach out with a written summary."
    ),
    true_priority="high",
    true_category="complaint",
    true_route="customer_success",
    task_tags=["full_triage", "inbox"],
    difficulty_notes="Hard — framed as feedback; still a dissatisfied customer needing retention.",
)

EMAIL_007 = Email(
    email_id="email_007",
    subject="Do you offer nonprofit discounts?",
    sender_name="Jordan Lee",
    sender_email="volunteer@smallngo.org",
    timestamp="2026-03-28T14:00:00Z",
    thread_history=[],
    body=(
        "Hi, I came across your product and it looks useful for our small volunteer-run nonprofit. "
        "We are registered 501(c)(3) and wondering whether you offer any nonprofit pricing or grants. "
        "There is no deadline on our side — we are early in budgeting for next quarter. "
        "A pointer to any public pricing page would be appreciated."
    ),
    true_priority="low",
    true_category="inquiry",
    true_route="customer_success",
    task_tags=["full_triage", "inbox"],
    difficulty_notes="Easy — low-urgency pre-sales style inquiry.",
)

EMAIL_008 = Email(
    email_id="email_008",
    subject="hey",
    sender_name="James Roberts",
    sender_email="j.roberts@bigenterprisecorp.com",
    timestamp="2026-04-02T13:10:00Z",
    thread_history=[],
    body=(
        "hey can someone sort out our onboarding? we signed the contract 2 weeks ago and nothing's happened. "
        "our board demo is thursday. this is not great. "
        "i need a single owner and a concrete checklist by tomorrow morning. "
        "please escalate if you cannot staff this — we are paying for enterprise and expect white-glove."
    ),
    true_priority="urgent",
    true_category="complaint",
    true_route="customer_success",
    task_tags=["full_triage", "inbox"],
    difficulty_notes="Hard — informal CEO-style tone; urgency is easy to underestimate from surface text.",
)

EMAILS: dict[str, Email] = {
    "email_001": EMAIL_001,
    "email_002": EMAIL_002,
    "email_003": EMAIL_003,
    "email_004": EMAIL_004,
    "email_005": EMAIL_005,
    "email_006": EMAIL_006,
    "email_007": EMAIL_007,
    "email_008": EMAIL_008,
}

# Ground-truth processing order for Task 3 (urgent → lower priority).
TRUE_INBOX_ORDER: list[str] = [
    "email_001",
    "email_008",
    "email_002",
    "email_004",
    "email_006",
    "email_005",
    "email_007",
    "email_003",
]
