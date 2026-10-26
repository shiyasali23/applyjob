"""Applying: queue -> parallel fill agents -> ONE approval line for the user -> submit approved only -> evidence.

The user approves by pasting back the line from `approve_line()` (it names every job). Only jobs named in that
paste become APPROVED; a submit agent may click Submit ONLY on an APPROVED job (`applyjob approved <batch>`).
"""
import json, math, re
from pathlib import Path
from . import ledger, sources, workspace

FILLABLE = ("AUDITED", "READY", "NEEDS_USER", "EXPIRED", "APPROVED")


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
                  "apply_email": spec.get("apply_email", ""), "approved": ledger.is_approved(db, j["id"])})
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


def _short(company):
    return re.sub(r"\s+(GmbH|AG|SE|KG|UG|Inc\.?|Ltd\.?|LLC|& Co\.?|mbH)\b.*$", "", company or "").strip()


def approve_line(db, batch, before_filling=False):
    """ONE paste-back line. before_filling=True names every open job of the batch (approve once, then the agents
    fill AND submit in parallel); False names only READY jobs (the old fill-first flow)."""
    js = ledger.jobs(db, FILLABLE if before_filling else "READY", batch)
    js = [j for j in js if not ledger.is_approved(db, j["id"])]
    return "submit " + ", ".join("%d %s" % (j["id"], _short(j["company"])) for j in js) if js else ""


def parse_approval(text):
    """'submit 12 Acme, 15 Beta GmbH' -> [(12, 'Acme'), (15, 'Beta GmbH')]. Ids are required: names alone are ambiguous."""
    body = re.sub(r"^\s*(submit|approve|send)\b", "", text.strip(), flags=re.I)
    out = []
    for part in [p.strip() for p in body.split(",") if p.strip()]:
        m = re.match(r"(\d+)\b\s*(.*)$", part)
        if m: out.append((int(m.group(1)), m.group(2).strip()))
    return out


def approve(db, batch, text, actor="user"):
    """Store his approval. A job must be open in this batch, and the name next to its id must match (no guessing)."""
    items = parse_approval(text)
    if not items: raise SystemExit("no job ids found; paste the line from `applyjob approve-line`")
    done, refused = [], []
    for i, name in items:
        j = db.execute("SELECT * FROM jobs WHERE id=?", (i,)).fetchone()
        if not j or j["batch"] != batch or j["status"] not in FILLABLE + ("READY",):
            refused.append("%d (%s)" % (i, j["status"] if j else "unknown")); continue
        if name and not _short(j["company"]).lower().startswith(name.lower()[:5]):
            refused.append("%d (name '%s' is not %s)" % (i, name, j["company"])); continue
        ledger.add_approval(db, i, text)
        if j["status"] == "READY":
            ledger.set_status(db, i, "APPROVED", "approved by the user: " + text[:200], actor=actor)
        done.append(i)
    return done, refused


def approved(db, batch):
    """Approved and not yet sent: the only jobs a submit/apply agent may submit."""
    return [dict(j) for j in ledger.jobs(db, batch=batch) if ledger.is_approved(db, j["id"]) and j["status"] not in ledger.SENT]
