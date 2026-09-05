"""Agent 1: Analyst. Exec summary, gap analysis, clarification log, risk flags.

Ports v1's stage_analyst; the only agent that reads the raw RFP end to end.
Downstream agents work from its artifacts, not the raw document.
"""
from .base import Agent, AgentResult, RunContext
from ..stages import _run_stage, _write, stage_compliance


class AnalystAgent(Agent):
    name = "analyst"
    description = "Reads the RFP end to end: executive summary, gap analysis, clarification log, risk flags."

    def run(self, ctx: RunContext) -> AgentResult:
        outputs = []
        outputs.append(_write(ctx.run_dir, "01_executive_summary.md", _run_stage(ctx.provider, "exec_summary", ctx.rfp_text)))
        outputs.append(_write(ctx.run_dir, "02_gap_analysis.md", _run_stage(ctx.provider, "gap_analysis", ctx.rfp_text)))
        outputs.append(_write(ctx.run_dir, "03_clarification_log.md", _run_stage(ctx.provider, "clarification_log", ctx.rfp_text)))
        outputs.append(_write(ctx.run_dir, "04_risk_flags.md", _run_stage(ctx.provider, "risk_flags", ctx.rfp_text)))
        outputs.extend(stage_compliance(ctx.provider, ctx.rfp_text, ctx.run_dir, out_name="05_compliance_matrix"))
        concerns = []
        risk_md = open(outputs[3], encoding="utf-8").read()
        high = sum(1 for line in risk_md.splitlines() if "high" in line.lower())
        if high:
            concerns.append(f"{high} high-severity contractual risk(s) flagged - see 04_risk_flags.md")
        return AgentResult(self.name, outputs, "Analyst pass complete: summary, gaps, clarification log, risk flags, compliance matrix.", concerns)
