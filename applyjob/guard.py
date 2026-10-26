#!/usr/bin/env python3
"""Claude Code PreToolUse hook: agents may only write where the harness says. Instructions can be forgotten in a
long chat; this cannot. Wired in .claude/settings.json for Write, Edit, MultiEdit and NotebookEdit.

Allowed for every chat:
    workspace/batches/**          application documents (specs, PDFs, audit.json, _apply/)
    workspace/work/**             scratch: one folder per chat
    workspace/inbox/**            files the user drops in for import
Allowed only in these cases:
    workspace/profile/**          only while onboarding (file workspace/.onboarding exists)
    the package code + docs       only when the user unlocked it (file workspace/.allow_code_edits exists)
Never by hand: workspace/ledger.db, workspace/tracker.xlsx (tools write them), anything outside the repo.
Exit code 2 blocks the tool call and tells the agent where the file belongs.
"""
import json, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def home():
    return Path(os.environ.get("APPLYJOB_HOME") or (REPO / "workspace")).expanduser().resolve()


def decide(file_path):
    """-> (allowed: bool, reason: str)"""
    if not file_path: return True, ""
    p = Path(file_path).expanduser().resolve()
    H = home()
    def under(base): return p == base or base in p.parents
    if under(H):
        rel = p.relative_to(H).parts
        top = rel[0] if rel else ""
        if p.name in ("ledger.db", "tracker.xlsx") and len(rel) == 1:
            return False, "the ledger and tracker are written only by `python3 -m applyjob ...` commands"
        if top in ("batches", "work", "inbox"):
            return True, ""
        if top == "profile":
            return (H / ".onboarding").exists(), "profile edits only during onboarding (create workspace/.onboarding when the user asks to change the profile)"
        return False, "only workspace/batches, workspace/work/<chat>, workspace/inbox are writable"
    if under(REPO):
        return (H / ".allow_code_edits").exists(), ("the package code is locked; the user unlocks it with `touch workspace/.allow_code_edits`. "
                                                    "Scratch files go to workspace/work/<your-chat-name>/")
    return False, "outside the applyjob repo: write scratch files to workspace/work/<your-chat-name>/"


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    ti = ev.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("notebook_path") or ""
    ok, why = decide(fp)
    if ok: return 0
    print("BLOCKED by applyjob guard: %s -> %s" % (fp, why), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
