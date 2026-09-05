"""Human-in-the-loop gates. Each stage pauses for review unless --auto is passed."""


class GateKeeper:
    def __init__(self, auto=False):
        self.auto = auto

    def check(self, stage, artifact_paths):
        if self.auto:
            print(f"[gate] {stage}: auto-approved ({len(artifact_paths)} artifact(s))")
            return "auto-approved"
        print(f"\n[gate] Stage '{stage}' produced:")
        for p in artifact_paths:
            print(f"  - {p}")
        answer = input(f"[gate] Approve stage '{stage}' and continue? [y/N] ").strip().lower()
        if answer in ("y", "yes"):
            return "approved-by-human"
        raise SystemExit(f"[gate] Stage '{stage}' rejected by reviewer. Run stopped.")
