"""Per-stage audit manifest: every stage records inputs, outputs, provider, and gate decision."""
import hashlib
import json
import os
from datetime import datetime, timezone


class AuditTrail:
    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.path = os.path.join(run_dir, "audit_manifest.json")
        self.entries = []

    def record(self, stage, inputs, outputs, provider, gate_decision, notes=""):
        entry = {
            "stage": stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "inputs": [{"file": p, "sha256": _hash_file(p)} for p in inputs],
            "outputs": [{"file": p, "sha256": _hash_file(p)} for p in outputs],
            "gate": gate_decision,
            "notes": notes,
        }
        self.entries.append(entry)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"stages": self.entries}, f, indent=2)
        return entry


def _hash_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
