"""Web UI for the RFP proposal pipeline.

Wraps the five-agent orchestrator in a small FastAPI app: upload an RFP,
watch the agents run, approve/reject at each human gate in the browser,
read or download every artifact.

Governance notes (unchanged from the CLI):
- Default provider is the deterministic mock; real providers need env keys.
- The commercial manager agent never receives an LLM provider, so the
  local rate list can never leave this process in an LLM call.
"""
import os
import threading
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from .audit import AuditTrail
from .ingest import extract_text
from .orchestrator import run_pipeline
from .providers import get_provider

RUNS_DIR = os.environ.get("RUNS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs"))
os.makedirs(RUNS_DIR, exist_ok=True)

app = FastAPI(title="RFP Proposal Pipeline")

RUNS = {}
RUNS_LOCK = threading.Lock()


class UiGate:
    """GateKeeper-compatible gate that blocks the pipeline thread until a
    decision arrives from the browser."""

    def __init__(self, run):
        self.run = run

    def check(self, phase, artifact_paths):
        with RUNS_LOCK:
            self.run["gate_pending"] = phase
            self.run["phase"] = phase
            names = [os.path.basename(p) for p in artifact_paths]
            self.run["gate_artifacts"] = names
            self.run["artifacts"] = sorted(set(self.run["artifacts"]) | set(names))
            self.run["gate_event"].clear()  # disarm before waiting - a stale set event would auto-reject
        self.run["gate_event"].wait()
        decision = self.run["gate_decision"]
        with RUNS_LOCK:
            self.run["gate_pending"] = None
            self.run["gate_decision"] = None
        if decision == "approve":
            return "approved-via-web"
        raise SystemExit(f"[gate] Phase '{phase}' rejected via web UI. Run stopped.")


def _execute(run_id, input_paths, docs):
    run = RUNS[run_id]
    run_dir = run["run_dir"]
    try:
        provider = get_provider(os.environ.get("LLM_PROVIDER") or "mock")
        with RUNS_LOCK:
            run["provider"] = provider.label
        rfp_text = "\n\n".join(f"=== {name} ===\n{text}" for name, text in docs.items())
        audit = AuditTrail(run_dir)
        artifacts = run_pipeline(provider, rfp_text, run_dir, input_paths, audit, UiGate(run))
        with RUNS_LOCK:
            run["artifacts"] = sorted(artifacts.keys())
            run["status"] = "done"
    except SystemExit as exc:
        with RUNS_LOCK:
            run["status"] = "rejected"
            run["error"] = str(exc)
    except Exception as exc:  # surface, don't swallow
        with RUNS_LOCK:
            run["status"] = "error"
            run["error"] = f"{type(exc).__name__}: {exc}"


@app.post("/api/runs")
async def create_run(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in (".pdf", ".docx", ".txt", ".md"):
        raise HTTPException(400, "Unsupported file type - upload PDF, DOCX, TXT or MD")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run_dir = os.path.join(RUNS_DIR, f"run-{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    safe_name = os.path.basename(file.filename or "rfp")
    input_path = os.path.join(run_dir, f"input_{safe_name}")
    with open(input_path, "wb") as f:
        f.write(await file.read())

    try:
        text = extract_text(input_path)
    except Exception as exc:
        raise HTTPException(422, f"Could not extract text: {exc}")

    run = {
        "id": run_id,
        "run_dir": run_dir,
        "filename": safe_name,
        "status": "running",
        "phase": "queued",
        "provider": None,
        "gate_pending": None,
        "gate_decision": None,
        "gate_artifacts": [],
        "gate_event": threading.Event(),
        "artifacts": [],
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with RUNS_LOCK:
        RUNS[run_id] = run
    threading.Thread(target=_execute, args=(run_id, [input_path], {safe_name: text}), daemon=True).start()
    return {"run_id": run_id}


def _public(run):
    return {k: run[k] for k in ("id", "filename", "status", "phase", "provider", "gate_pending", "gate_artifacts", "artifacts", "error", "created_at")}


@app.get("/api/runs")
def list_runs():
    with RUNS_LOCK:
        return {"runs": [_public(r) for r in sorted(RUNS.values(), key=lambda r: r["created_at"], reverse=True)]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return _public(run)


class GateDecision(BaseModel):
    decision: str


@app.post("/api/runs/{run_id}/gate")
def decide_gate(run_id: str, body: GateDecision):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if not run["gate_pending"]:
        raise HTTPException(409, "no gate is waiting")
    if body.decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be approve or reject")
    run["gate_decision"] = body.decision
    run["gate_event"].set()
    return {"ok": True, "decision": body.decision, "phase": run["gate_pending"]}


@app.get("/api/runs/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str, download: bool = False):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    safe = os.path.basename(name)
    path = os.path.join(run["run_dir"], safe)
    if not os.path.exists(path):
        raise HTTPException(404, "artifact not found")
    if download or safe.endswith(".docx") or safe.endswith(".json"):
        return FileResponse(path, filename=safe)
    with open(path, encoding="utf-8", errors="replace") as f:
        return {"name": safe, "content": f.read()}


STATIC = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()
