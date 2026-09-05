"""Deterministic rule-based 'model' used when no LLM provider is configured.

Every answer is derived from the RFP text embedded in the prompt, so mock runs
are fully repeatable and safe to check into git as sample outputs.
"""
import re

RISK_PATTERNS = [
    ("bank guarantee", "Bank guarantee", "high",
     "A bank guarantee is demanded. Confirm percentage, validity period, and which bank; this ties up credit lines and needs finance sign-off."),
    ("performance bond", "Performance bond", "high",
     "A performance bond is required. Confirm amount, trigger conditions, and release milestones before pricing."),
    ("insurance", "Insurance obligation", "medium",
     "Insurance cover is required (professional indemnity / third party). Confirm required coverage amounts and certificate deadlines."),
    ("liquidated damages", "Liquidated damages / penalties", "high",
     "Liquidated damages or penalty clauses present. Cap exposure in the contract review and price the risk into the delivery plan."),
    ("penalt", "Penalty clause", "high",
     "Penalty language detected. Review caps, grace periods, and cure rights."),
    ("arbitration", "Arbitration / dispute venue", "medium",
     "Disputes go to arbitration. Confirm seat, rules (e.g. DIAC), and language; affects legal review cost."),
    ("arabic", "Arabic language requirement", "medium",
     "Arabic-language deliverables or resources are required. Confirm scope: UI, reports, training material, or on-site Arabic-speaking consultants."),
    ("free of charge|free licen[sc]e|licen[sc]es? (?:at no cost|free)", "Free licences requested", "medium",
     "The RFP asks for licences at no cost. Clarify count, duration, and which SKUs before committing commercials."),
    ("warranty", "Warranty obligation", "low",
     "Warranty period required post go-live. Confirm duration and SLA expectations."),
    ("indemn", "Indemnity clause", "medium",
     "Indemnification language present. Route to legal before submission."),
]

CLARIFICATION_PATTERNS = [
    ("bank guarantee", "What percentage of contract value is required for the bank guarantee, and what validity period and issuing-bank criteria apply?"),
    ("performance bond", "Is a performance bond required in addition to the bank guarantee? If so, what amount and release conditions?"),
    ("insurance", "Which insurance policies are mandatory (professional indemnity, third-party liability, workers' compensation), and at what coverage values?"),
    ("arbitration", "Which arbitration seat and rules govern disputes, and in which language will proceedings be conducted?"),
    ("arabic", "What is the exact scope of the Arabic requirement - user interface, printed reports, training material, or Arabic-speaking on-site resources?"),
    ("free of charge|free licen[sc]e", "How many free licences are requested, for which products/SKUs, and for what duration?"),
    ("data migration", "What data volumes and source systems are in scope for migration, and who owns data cleansing?"),
    ("integration", "Which third-party systems must the solution integrate with, and are APIs/documentation available?"),
    ("go-live", "Is the stated go-live date fixed, and what are the consequences of a phased go-live?"),
    ("payment terms", "What payment milestones apply, and are they tied to acceptance certificates?"),
]

GAP_LIBRARY = [
    ("arabic", "Arabic enablement", "Standard D365 BC supports Arabic UI and RTL, but Arabic report layouts and Arabic-speaking delivery resources are not part of our default bench - needs staffing plan."),
    ("integration", "Third-party integrations", "RFP implies integrations that are not yet specified; effort cannot be sized until endpoints and volumes are confirmed."),
    ("data migration", "Data migration", "Migration scope is undefined in the RFP; our standard template assumes one legacy source - likely a gap."),
    ("training", "Training & adoption", "Training requirements are stated generically; confirm whether train-the-trainer or end-user delivery is expected."),
    ("support", "Post-go-live support", "Support window and SLA expectations need confirmation against our standard managed-service tiers."),
]


def _rfp_text(prompt):
    marker = "RFP TEXT:"
    idx = prompt.find(marker)
    return prompt[idx + len(marker):] if idx >= 0 else prompt


def _find(pattern, text):
    return re.search(pattern, text, re.IGNORECASE)


def answer(system, prompt):
    task = "unknown"
    m = re.search(r"TASK:\s*(\w+)", system)
    if m:
        task = m.group(1)
    text = _rfp_text(prompt)
    handler = {
        "exec_summary": exec_summary,
        "gap_analysis": gap_analysis,
        "clarification_log": clarification_log,
        "risk_flags": risk_flags,
        "compliance_matrix": compliance_matrix,
        "proposal_skeleton": proposal_skeleton,
    }.get(task, lambda t: f"[mock] no handler for task {task}")
    return handler(text)


def _title(text):
    for line in text.splitlines():
        line = line.strip().strip("#").strip()
        if line.startswith("===") or not line:
            continue
        if len(line) > 8:
            return line
    return "Untitled RFP"


def _buyer(text):
    m = re.search(r"(?:issued by|buyer|client|company)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"([A-Z][\w& ]+(?:LLC|L\.L\.C|FZ|FZE|PJSC|PSC|Ltd|Limited|Inc|GmbH))", text)
    return m.group(1).strip() if m else "the issuing organisation"


def exec_summary(text):
    title = _title(text)
    buyer = _buyer(text)
    deadline = re.search(r"(?:submission|submitted|closing|deadline)[^\n]*?(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    deadline = deadline.group(1) if deadline else "not stated"
    hooks = [label for pat, label, _, _ in RISK_PATTERNS if _find(pat, text)]
    return (
        f"# Executive Summary\n\n"
        f"**RFP:** {title}\n\n"
        f"**Issued by:** {buyer}\n\n"
        f"**Submission deadline:** {deadline}\n\n"
        f"**Opportunity:** Implementation of Microsoft Dynamics 365 Business Central covering "
        f"finance, procurement, inventory, and sales operations, with data migration, integrations, "
        f"training, and post-go-live support.\n\n"
        f"**Notable contractual hooks detected:** {', '.join(dict.fromkeys(hooks)) if hooks else 'none detected'}.\n\n"
        f"**Recommendation:** Proceed to bid, subject to clarification of the flagged contractual "
        f"obligations and confirmation of integration and migration scope.\n"
    )


def risk_flags(text):
    rows = []
    seen = set()
    for pat, label, severity, note in RISK_PATTERNS:
        if pat in seen:
            continue
        if _find(pat, text):
            seen.add(pat)
            rows.append(f"| {label} | {severity} | {note} |")
    if not rows:
        rows.append("| None detected | - | No standard risk triggers found in the text. |")
    return ("# Risk Flags\n\n| Risk | Severity | Why it matters |\n|---|---|---|\n" + "\n".join(rows) + "\n")


def clarification_log(text):
    items = []
    for pat, question in CLARIFICATION_PATTERNS:
        if _find(pat, text):
            items.append(question)
    if not items:
        items.append("Confirm the evaluation criteria and weighting used to score proposals.")
    body = "\n".join(f"| CQ-{i+1:02d} | {q} | Open |" for i, q in enumerate(items))
    return ("# Clarification Question Log\n\n| ID | Question | Status |\n|---|---|---|\n" + body + "\n")


def gap_analysis(text):
    rows = []
    for pat, area, gap in GAP_LIBRARY:
        if _find(pat, text):
            rows.append(f"| {area} | {gap} |")
    if not rows:
        rows.append("| General | No specific gaps detected against our standard D365 BC delivery template. |")
    return ("# Gap Analysis\n\nGaps between the RFP's stated expectations and our standard delivery template.\n\n"
            "| Area | Gap / action needed |\n|---|---|\n" + "\n".join(rows) + "\n")


def compliance_matrix(text):
    reqs = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if len(line) > 25 and re.search(r"\b(shall|must|required to|is required)\b", line, re.IGNORECASE):
            reqs.append(re.sub(r"\s+", " ", line))
    if not reqs:
        reqs = ["The bidder shall submit a complete technical and commercial proposal."]
    rows = []
    for i, r in enumerate(reqs[:40]):
        r = r.replace("|", "/")
        rows.append(f"| CM-{i+1:03d} | {r} | To confirm | Presales |")
    return ("# Compliance Matrix\n\n| ID | Requirement | Response | Owner |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")


def proposal_skeleton(text):
    title = _title(text)
    buyer = _buyer(text)
    return (
        f"# Proposal Skeleton\n\n"
        f"**Response to:** {title} - {buyer}\n\n"
        f"1. Cover letter and executive summary\n"
        f"2. Understanding of requirements\n"
        f"3. Proposed solution architecture (Dynamics 365 Business Central)\n"
        f"4. Implementation methodology and phased plan\n"
        f"5. Data migration approach\n"
        f"6. Integration approach\n"
        f"7. Training and change management\n"
        f"8. Support and managed services\n"
        f"9. Project governance, team, and CVs\n"
        f"10. Commercials (implementation + licensing)\n"
        f"11. Compliance matrix response\n"
        f"12. Assumptions, exclusions, and dependencies\n"
        f"13. Appendices (case studies, certifications)\n"
    )
