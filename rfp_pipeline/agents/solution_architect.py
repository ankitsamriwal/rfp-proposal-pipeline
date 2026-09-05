"""Agent 2: Proposal drafter / solution architect.

Drafts the solution outline and proposal skeleton from the analyst's
artifacts (gap analysis drives the solution shape), not from raw RFP text.
"""
from .base import Agent, AgentResult, RunContext
from ..stages import _run_stage, _write


class SolutionArchitectAgent(Agent):
    name = "solution_architect"
    description = "Drafts the solution outline and proposal skeleton from the analyst's findings."

    def run(self, ctx: RunContext) -> AgentResult:
        gaps = open(ctx.artifacts["02_gap_analysis.md"], encoding="utf-8").read()
        prompt = (
            "Using this gap analysis of the RFP, draft a solution outline "
            "(proposed scope, delivery approach, key workstreams) in markdown.\n\n"
            f"GAP ANALYSIS:\n{gaps}"
        )
        from ..stages import SYSTEM
        outline = ctx.provider.complete(
            "TASK: solution_outline\nYou are a solution architect. Draft the solution outline for this bid in markdown.",
            prompt,
        )
        outputs = [_write(ctx.run_dir, "06_solution_outline.md", outline)]
        # Proposal skeleton still reads the raw RFP (structure mirrors the RFP's own sectioning)
        from ..stages import stage_proposal
        outputs.extend(stage_proposal(ctx.provider, ctx.rfp_text, ctx.run_dir, out_name="07_proposal_skeleton"))
        return AgentResult(self.name, outputs, "Solution outline and proposal skeleton drafted.", [])
