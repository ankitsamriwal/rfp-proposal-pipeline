"""Agent 4: Commercial manager.

Prices the BOQ against the LOCAL rate list (rfp_pipeline/rates/rate_list.json).

Hard rule: this agent receives no LLM provider. The rate list is the
company's commercial crown jewels and must never leave the machine, so
everything here is local arithmetic over local files. See README's data
governance section.
"""
import json
import os
import re

from .base import Agent, AgentResult, RunContext
from ..stages import _write

RATES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rates", "rate_list.json")


def _boq_rows(boq_md: str):
    rows = []
    for line in boq_md.splitlines():
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and re.match(r"^[LFS]\d{2}$", cells[0]):
                rows.append(cells)
    return rows


class CommercialManagerAgent(Agent):
    name = "commercial_manager"
    description = "Prices the BOQ against the local rate list. No LLM, no network - local arithmetic only."

    def run(self, ctx: RunContext) -> AgentResult:
        with open(RATES_PATH, encoding="utf-8") as f:
            rates = json.load(f)

        boq_md = open(ctx.artifacts["08_licensing_boq.md"], encoding="utf-8").read()
        rows = _boq_rows(boq_md)
        defaults = rates["default_service_days"]
        months = rates["subscription_months"]

        out_lines = [
            "# Commercial Offer (prototype pricing)",
            "",
            f"Priced from the local rate list, {rates['currency']}. Subscriptions shown over {months} months.",
            "",
            "| BOQ ID | Item | Unit | Qty | Unit rate | Total |",
            "|---|---|---|---|---|---|",
        ]
        grand = 0
        unresolved = []
        for boq_id, item, unit, qty in rows:
            rate_entry = rates["licences"].get(boq_id) or rates["services"].get(boq_id)
            if rate_entry is None:
                unresolved.append(boq_id)
                continue
            if boq_id.startswith("L"):
                q = int(qty)
                total = q * rate_entry["rate"] * months
                qty_show = f"{q} x {months}m"
            else:
                q = defaults.get(boq_id, 0)
                total = q * rate_entry["rate"]
                qty_show = str(q)
            grand += total
            out_lines.append(f"| {boq_id} | {rate_entry['name']} | {rate_entry['unit']} | {qty_show} | {rate_entry['rate']:,} | {total:,} |")

        out_lines += [
            "",
            f"**Indicative total: {rates['currency']} {grand:,}**",
            "",
            "_Prototype pricing from a sample rate list; not a customer-ready offer._",
        ]
        out = _write(ctx.run_dir, "09_commercial_offer.md", "\n".join(out_lines) + "\n")
        concerns = [f"No rate found for {', '.join(unresolved)} - left unpriced"] if unresolved else []
        return AgentResult(self.name, [out], f"Commercial offer priced locally: {rates['currency']} {grand:,} indicative total.", concerns)
