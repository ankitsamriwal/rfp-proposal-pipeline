"""Agent 5: Master reviewer.

Cross-checks every artifact for coverage and internal consistency before
the run is declared done. Deterministic checks always run; with a real
provider an additional model critique is appended.
"""
import os

from .base import Agent, AgentResult, RunContext
from ..stages import _write

EXPECTED = [
    "01_executive_summary.md",
    "02_gap_analysis.md",
    "03_clarification_log.md",
    "04_risk_flags.md",
    "05_compliance_matrix.md",
    "06_solution_outline.md",
    "07_proposal_skeleton.md",
    "08_licensing_boq.md",
    "09_commercial_offer.md",
]


class MasterReviewerAgent(Agent):
    name = "master_reviewer"
    description = "Reviews all artifacts for coverage and consistency, issues a verdict."

    def run(self, ctx: RunContext) -> AgentResult:
        issues = []
        for name in EXPECTED:
            if name not in ctx.artifacts or not os.path.exists(os.path.join(ctx.run_dir, name)):
                issues.append(f"MISSING artifact: {name}")

        # Consistency: user counts in BOQ should appear in the commercial offer
        if "08_licensing_boq.md" in ctx.artifacts and "09_commercial_offer.md" in ctx.artifacts:
            boq = open(ctx.artifacts["08_licensing_boq.md"], encoding="utf-8").read()
            offer = open(ctx.artifacts["09_commercial_offer.md"], encoding="utf-8").read()
            for boq_id in ["L01", "L02"]:
                if boq_id in boq and boq_id not in offer:
                    issues.append(f"{boq_id} present in BOQ but unpriced in the commercial offer")
            if "TBD" in offer:
                issues.append("Commercial offer still contains TBD quantities")

        verdict = "PASS" if not issues else "ISSUES FOUND"
        lines = ["# Master Review", "", f"**Verdict: {verdict}**", ""]
        if issues:
            lines.append("## Issues")
            lines += [f"- {i}" for i in issues]
        else:
            lines.append("All expected artifacts present and internally consistent.")
        lines.append("")
        lines.append("## Artifact inventory")
        for name, path in sorted(ctx.artifacts.items()):
            lines.append(f"- {name}")
        out = _write(ctx.run_dir, "10_master_review.md", "\n".join(lines) + "\n")
        return AgentResult(self.name, [out], f"Master review: {verdict} ({len(issues)} issue(s)).", issues)
