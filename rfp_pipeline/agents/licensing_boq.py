"""Agent 3: Licensing & BOQ specialist.

Builds the licence count estimate and bill of quantities from the RFP
scope. In mock mode this is deterministic: it scans for user-count and
module signals in the RFP text. With a real provider the same artifact
shape is produced from the model's reading.
"""
import re

from .base import Agent, AgentResult, RunContext
from ..stages import _write

# Standard BC licence mix assumptions used by the mock estimator
DEFAULT_MIX = {"full_users_ratio": 0.3, "device_users": 0}


def _estimate_users(rfp_text: str):
    """Find explicit user counts in the RFP, else fall back to a stated-default estimate."""
    counts = [int(m) for m in re.findall(r"(\d+)\s+(?:named\s+)?users", rfp_text, flags=re.I)]
    total = max(counts) if counts else 25
    full = max(1, round(total * DEFAULT_MIX["full_users_ratio"]))
    team = total - full
    return total, full, team


def _detect_modules(rfp_text: str):
    modules = []
    for name, needles in [
        ("Finance", ["general ledger", "accounts payable", "accounts receivable", "finance"]),
        ("Supply Chain", ["inventory", "purchase", "warehouse", "procurement"]),
        ("Sales", ["sales order", "crm", "quotation"]),
        ("Manufacturing", ["production order", "bom", "manufacturing"]),
        ("Projects", ["job costing", "project accounting"]),
    ]:
        if any(n in rfp_text.lower() for n in needles):
            modules.append(name)
    return modules or ["Finance"]


class LicensingBoqAgent(Agent):
    name = "licensing_boq"
    description = "Estimates licence counts and builds the bill of quantities from the RFP scope."

    def run(self, ctx: RunContext) -> AgentResult:
        total, full, team = _estimate_users(ctx.rfp_text)
        modules = _detect_modules(ctx.rfp_text)

        lines = [
            "# Licence & BOQ Estimate",
            "",
            "## Licences (Dynamics 365 Business Central)",
            "",
            "| Licence type | Quantity | Basis |",
            "|---|---|---|",
            f"| Full users | {full} | ~30% of {total} named users in RFP |",
            f"| Team members | {team} | Remainder of named users |",
            "",
            "## Bill of quantities (effort & subscriptions)",
            "",
            "| BOQ ID | Item | Unit | Qty |",
            "|---|---|---|---|",
            f"| L01 | BC full-user subscription | user/month | {full} |",
            f"| L02 | BC team-member subscription | user/month | {team} |",
        ]
        n = 1
        for mod in modules:
            lines.append(f"| F{n:02d} | {mod} functional consulting | day | TBD by commercial |")
            n += 1
        lines += [
            f"| S01 | Implementation project management | day | TBD by commercial |",
            f"| S02 | Data migration & cutover | day | TBD by commercial |",
            "",
            "Quantities marked TBD are set by the commercial manager against the local rate list.",
        ]
        out = _write(ctx.run_dir, "08_licensing_boq.md", "\n".join(lines) + "\n")
        return AgentResult(
            self.name,
            [out],
            f"Licence & BOQ estimate: {full} full + {team} team users, modules: {', '.join(modules)}.",
            [],
        )
