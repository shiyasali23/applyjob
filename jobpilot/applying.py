"""Applying: queue -> parallel fill agents -> ONE approval line for the user -> submit approved only -> evidence.

The user approves by pasting back the line from `approve_line()` (it names every job). Only jobs named in that
paste become APPROVED; a submit agent may click Submit ONLY on an APPROVED job (`jobpilot approved <batch>`).
"""
import json, math, re
from pathlib import Path
from . import ledger, sources, workspace

FILLABLE = ("AUDITED", "READY", "NEEDS_USER", "EXPIRED")


def batch_dir(label):
    p = workspace.path("batches", label)
    if not p.is_dir(): raise SystemExit("no batch %s (have: %s)" % (label, ", ".join(sorted(x.name for x in workspace.path("batches").iterdir()))))
    return p


def queue(db, batch, groups=0, per_agent=8):
    """Open, audited jobs -> batches/<b>/_apply/queue.json (+ group_k.json, one per fill agent)."""
    B = batch_dir(batch); out = B / "_apply"; out.mkdir(exist_ok=True)
    q = []
    for j in ledger.jobs(db, FILLABLE, batch):
        D = B / j["folder"]
        spec = json.loads((D / "spec.json").read_text()) if (D / "spec.json").exists() else {}
        plat = sources.platform(j["url"])
        q.append({"id": j["id"], "company": j["company"], "title": j["title"], "url": j["url"], "platform": plat,
                  "needs_account": plat in sources.NEEDS_ACCOUNT, "status": j["status"], "last_note": j["note"],
                  "cv": str(D / "cv.pdf"), "letter": str(D / "letter.pdf"),
                  "asks_salary": bool(spec.get("asks_salary")), "asks_start": bool(spec.get("asks_start")),
                  "apply_email": spec.get("apply_email", "")})
    (out / "queue.json").write_text(json.dumps(q, ensure_ascii=False, indent=1))
    for old in out.glob("group_*.json"): old.unlink()
    n = groups or max(1, math.ceil(len(q) / per_agent))
    size = math.ceil(len(q) / n) if q else 0
    files = []
    for k in range(n):
        part = q[k * size:(k + 1) * size]
        if part:
            f = out / ("group_%02d.json" % (k + 1)); f.write_text(json.dumps(part, ensure_ascii=False, indent=1)); files.append(f)
    return q, files


def approve_line(db, batch):
    ready = ledger.jobs(db, "READY", batch)
    return "submit " + ", ".join("%d %s" % (j["id"], j["company"]) for j in ready) if ready else ""


def parse_approval(text):
    """'submit 12 Acme, 15 Beta GmbH' -> [12, 15]. Ids are required: names alone are ambiguous."""
    body = re.sub(r"^\s*(submit|approve|send)\b", "", text.strip(), flags=re.I)
    return [int(m.group(1)) for m in re.finditer(r"(?:^|,)\s*(\d+)\b", body)]


def approve(db, batch, text, actor="user"):
    ids = parse_approval(text)
    if not ids: raise SystemExit("no job ids found; paste the line from `jobpilot approve-line`")
    done, refused = [], []
    for i in ids:
        j = db.execute("SELECT * FROM jobs WHERE id=?", (i,)).fetchone()
        if not j or j["batch"] != batch or j["status"] != "READY":
            refused.append("%d (%s)" % (i, j["status"] if j else "unknown")); continue
        ledger.set_status(db, i, "APPROVED", "approved by the user: " + text[:200], actor=actor); done.append(i)
    return done, refused


def approved(db, batch):
    return [dict(j) for j in ledger.jobs(db, "APPROVED", batch)]
