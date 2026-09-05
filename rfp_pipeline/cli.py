"""CLI entry point.

Usage:
    python -m rfp_pipeline run --input demo_rfp/ --output outputs/ [--auto] [--provider mock]
"""
import argparse
import os
import shutil
from datetime import datetime, timezone

from .audit import AuditTrail
from .gates import GateKeeper
from .ingest import ingest_folder
from .providers import get_provider
from .stages import stage_analyst, stage_compliance, stage_proposal


def run(args):
    provider = get_provider(args.provider)
    print(f"[pipeline] provider: {provider.label}")

    docs = ingest_folder(args.input)
    print(f"[pipeline] ingested {len(docs)} document(s): {', '.join(docs)}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(args.output, f"run-{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    # snapshot inputs into the run folder for a self-contained audit trail
    input_paths = []
    for name in docs:
        src = os.path.join(args.input, name)
        dst = os.path.join(run_dir, f"input_{name}")
        shutil.copyfile(src, dst)
        input_paths.append(dst)

    rfp_text = "\n\n".join(f"=== {name} ===\n{text}" for name, text in docs.items())
    audit = AuditTrail(run_dir)
    gates = GateKeeper(auto=args.auto)

    out = stage_analyst(provider, rfp_text, run_dir)
    decision = gates.check("analyst", out)
    audit.record("analyst", input_paths, out, provider.label, decision)

    out = stage_compliance(provider, rfp_text, run_dir)
    decision = gates.check("compliance", out)
    audit.record("compliance", input_paths, out, provider.label, decision)

    out = stage_proposal(provider, rfp_text, run_dir)
    decision = gates.check("proposal", out)
    audit.record("proposal", input_paths, out, provider.label, decision)

    print(f"\n[pipeline] done. Artifacts in {run_dir}")
    print(f"[pipeline] audit manifest: {audit.path}")


def main():
    parser = argparse.ArgumentParser(prog="rfp_pipeline", description="Multi-stage RFP response pipeline (prototype)")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="Run the pipeline over a folder of RFP documents")
    run_p.add_argument("--input", required=True, help="Folder containing the RFP (PDF/DOCX/TXT/MD)")
    run_p.add_argument("--output", default="outputs", help="Where run folders are written")
    run_p.add_argument("--auto", action="store_true", help="Auto-approve all human-in-the-loop gates")
    run_p.add_argument("--provider", default=None, help="LLM provider: openai|azure|anthropic|ollama|mock (default: env LLM_PROVIDER or mock)")
    run_p.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
