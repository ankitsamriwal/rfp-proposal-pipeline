# RFP Proposal Pipeline (Prototype)

A multi-stage Python CLI that ingests an RFP document and produces the core artifacts of a presales response: executive summary, gap analysis, clarification-question log, contractual risk flags, a compliance matrix (CSV + Markdown), and a proposal skeleton DOCX - with a per-stage audit manifest and human-in-the-loop gates between stages.

**This is a prototype / learning exercise, not a production system.**

## What it does

Drop an RFP (PDF, DOCX, TXT, or MD) into a folder and run the pipeline. Three stages, each gated for human review:

1. **Analyst** - executive summary, gap analysis against a standard D365 Business Central delivery template, clarification-question log, and risk flags (bank guarantees, performance bonds, insurance, penalties / liquidated damages, arbitration, Arabic requirements, free licences, warranties, indemnities).
2. **Compliance** - extracts every mandatory ("shall" / "must" / "required") requirement into a compliance matrix, written as both CSV and Markdown.
3. **Proposal** - generates a proposal skeleton as a DOCX, ready for the proposal team to flesh out.

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
rfp_pipeline/       pipeline package (ingest, providers, stages, gates, audit)
scripts/            demo RFP generator
demo_rfp/           synthetic demo RFP (DOCX)
outputs/            sample run artifacts (mock provider)
```
