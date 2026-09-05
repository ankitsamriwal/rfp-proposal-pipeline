"""v2 orchestrator: sequences the five agents behind human gates and audits everything.

Flow: analyst -> gate -> (solution_architect, licensing_boq) -> gate
      -> commercial_manager -> gate -> master_reviewer -> gate.

The commercial agent is constructed WITHOUT the LLM provider by design:
pricing arithmetic runs locally against the rate list and no RFP content
is combined with rate data in any external call.
"""
from .agents.base import RunContext
from .agents.analyst import AnalystAgent
from .agents.solution_architect import SolutionArchitectAgent
from .agents.licensing_boq import LicensingBoqAgent
from .agents.commercial import CommercialManagerAgent
from .agents.reviewer import MasterReviewerAgent

PHASES = [
    ("analysis", [AnalystAgent()]),
    ("solution", [SolutionArchitectAgent(), LicensingBoqAgent()]),
    ("commercial", [CommercialManagerAgent()]),
    ("review", [MasterReviewerAgent()]),
]


def run_pipeline(provider, rfp_text, run_dir, input_paths, audit, gates):
    ctx = RunContext(rfp_text=rfp_text, run_dir=run_dir, provider=provider)

    for phase_name, agents in PHASES:
        phase_outputs = []
        concerns = []
        for agent in agents:
            print(f"[orchestrator] phase '{phase_name}': running {agent.name} - {agent.description}")
            result = agent.run(ctx)
            for path in result.outputs:
                ctx.artifacts[path.split("/")[-1]] = path
            phase_outputs.extend(result.outputs)
            concerns.extend(result.concerns)
            print(f"[orchestrator] {agent.name}: {result.summary}")
        for c in concerns:
            print(f"[orchestrator] concern: {c}")
        decision = gates.check(phase_name, phase_outputs)
        audit.record(phase_name, input_paths, phase_outputs, provider.label, decision)

    return ctx.artifacts
