# RFP Proposal Pipeline (Prototype)

A multi-stage Python CLI that ingests an RFP document and produces the core artifacts of a presales response: executive summary, gap analysis, clarification-question log, contractual risk flags, a compliance matrix (CSV + Markdown), and a proposal skeleton DOCX - with a per-stage audit manifest and human-in-the-loop gates between stages.

**This is a prototype / learning exercise, not a production system.**

## v2: five-agent architecture

The pipeline is now an orchestrated team of five single-responsibility agents, each gated for human review:

1. **Analyst** - reads the RFP end to end: executive summary, gap analysis, clarification log, risk flags, compliance matrix.
2. **Solution architect (proposal drafter)** - drafts the solution outline and proposal skeleton from the analyst's findings.
3. **Licensing & BOQ specialist** - licence counts and bill of quantities from the RFP scope.
4. **Commercial manager** - prices the BOQ against the **local-only rate list** (`rfp_pipeline/rates/rate_list.json`). This agent has no LLM provider at all: rate data is never combined with RFP content in any external call - pricing is local arithmetic over local files.
5. **Master reviewer** - cross-checks every artifact for coverage and consistency, then issues a PASS / ISSUES FOUND verdict.

Orchestration (`rfp_pipeline/orchestrator.py`): `analyst -> gate -> (solution architect, licensing & BOQ) -> gate -> commercial manager -> gate -> master reviewer -> gate`. Every agent's outputs, every concern it raises, and every gate decision land in `audit_manifest.json`.

Run the v1 three-stage flow with `python -m rfp_pipeline run --legacy ...`.

## What it does

Drop an RFP (PDF, DOCX, TXT, or MD) into a folder and run the pipeline. Five agents in four gated phases (see above) produce: executive summary, gap analysis, clarification log, risk flags, compliance matrix (CSV + Markdown), solution outline, proposal skeleton (DOCX), licence & BOQ estimate, a locally priced commercial offer, and a master review verdict.

Every stage appends to `audit_manifest.json` in the run folder: input/output file hashes, provider used, timestamp, and the gate decision.

## Quick start (no API keys needed)

```bash
pip install -r requirements.txt
python -m rfp_pipeline run --input demo_rfp/ --output outputs/ --auto
```

This runs against the included synthetic demo RFP (`demo_rfp/gulf_crescent_trading_llc_rfp.docx` - a fictional UAE trading company implementing Dynamics 365 Business Central, deliberately seeded with bank-guarantee, insurance, Arabic, and arbitration hooks) using the deterministic **mock provider**. Checked-in example results live in `outputs/sample-run-mock/`.

Regenerate the demo RFP with `python scripts/make_demo_rfp.py`.

## Human-in-the-loop gates

Without `--auto`, the pipeline pauses after each stage, lists the artifacts it produced, and waits for approval before continuing. A rejection stops the run. Gate decisions are recorded in the audit manifest either way.

## Mock vs real LLM providers

The provider is selected with `LLM_PROVIDER` (or `--provider`):

| Provider | Env vars required | Notes |
|---|---|---|
| `mock` (default) | none | Deterministic rule-based extraction. Offline, repeatable, free. |
| `openai` | `OPENAI_API_KEY` (+ optional `OPENAI_MODEL`) | |
| `azure` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI |
| `anthropic` | `ANTHROPIC_API_KEY` (+ optional `ANTHROPIC_MODEL`) | |
| `ollama` | optional `OLLAMA_HOST`, `OLLAMA_MODEL` | Local open-weight models |

With a real provider configured, the same stages run but the analysis is model-generated instead of rule-based.

## Data governance (read before using real RFPs)

- **The master rate list stays local.** Pricing data must never be sent to an external API; commercial pricing is deliberately out of scope for this pipeline.
- **Employer data-policy approval is required before any real customer RFP content touches an external API** (OpenAI, Azure OpenAI, Anthropic). Until then, use `mock` or a locally hosted `ollama` model for anything real.
- The demo RFP is fully synthetic; no real customer data is included in this repository.

## Layout

```
rfp_pipeline/       pipeline package (ingest, providers, agents/, orchestrator, gates, audit)
rfp_pipeline/rates/ local rate list - never leaves the machine
scripts/            demo RFP generator
demo_rfp/           synthetic demo RFP (DOCX)
outputs/            sample run artifacts (mock provider)
```
