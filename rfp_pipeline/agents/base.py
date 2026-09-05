"""Agent protocol for the v2 multi-agent pipeline.

Each agent is a small, single-responsibility unit that reads the shared
RunContext (RFP text + prior agents' artifacts) and writes its own
artifacts into the run folder. Agents never call each other directly -
the orchestrator sequences them and enforces the human gates.
"""
from dataclasses import dataclass, field


@dataclass
class RunContext:
    rfp_text: str
    run_dir: str
    provider: object          # LLM provider (mock or real) - NEVER given to the commercial agent for pricing
    artifacts: dict = field(default_factory=dict)   # name -> path, accumulated across agents


@dataclass
class AgentResult:
    agent: str
    outputs: list             # artifact paths written
    summary: str              # one-paragraph human-readable summary for the gate prompt
    concerns: list = field(default_factory=list)  # issues the agent wants the human/reviewer to see


class Agent:
    name = "agent"
    description = ""

    def run(self, ctx: RunContext) -> AgentResult:
        raise NotImplementedError
