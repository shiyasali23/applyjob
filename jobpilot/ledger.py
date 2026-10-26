"""The ledger: one SQLite file with every job and every event. It is the single truth.

Reports, trackers and "applied?" columns are generated FROM it, never edited by hand.
Writes take an OS lock, so several agent chats can run at once without losing rows.
A job only becomes SUBMITTED/EMAILED with evidence (a confirmation page quote or a confirmation mail).
"""
import datetime, json, re, sqlite3
from urllib.parse import urlparse
from . import workspace

# status -> stage it belongs to (order = pipeline order)
STATUSES = [
    "FOUND",                                   # search / import
    "GOOD", "CHECK", "REMOVED",                # triage
    "DRAFTED", "AUDIT_FAIL", "AUDITED",        # tailor + audit
    "READY", "NEEDS_USER", "LOGIN", "EXPIRED", "EMAIL_ONLY", "CLOSED", "SKIP",   # form filling
    "APPROVED",                                # the user named it for submission
    "SUBMITTED", "EMAILED",                    # sent (evidence required)
    "REPLIED", "INTERVIEW", "REJECTED", "OFFER",
]
SENT = {"SUBMITTED", "EMAILED"}
TERMINAL = SENT | {"REMOVED", "CLOSED", "SKIP", "REJECTED", "INTERVIEW", "OFFER", "REPLIED"}
NOTE_REQUIRED = {"REMOVED", "NEEDS_USER", "LOGIN", "EMAIL_ONLY", "CLOSED", "SKIP", "AUDIT_FAIL", "CHECK"}
# platforms whose on-page "applied" badge has proven NOT to mean sent: require a confirmation mail
MAIL_ONLY_EVIDENCE = ("join.com", "arbeitnow.com")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY, key TEXT UNIQUE, company TEXT, title TEXT, url TEXT, location TEXT,
  source TEXT, description TEXT DEFAULT '', status TEXT, note TEXT DEFAULT '', batch TEXT DEFAULT '',
  folder TEXT DEFAULT '', created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, job_id INTEGER, ts TEXT, status TEXT, note TEXT, evidence TEXT, actor TEXT);
CREATE INDEX IF NOT EXISTS ev_job ON events(job_id);
"""


def connect(p=None):
    if p is None: workspace.init()          # first run: create the workspace instead of crashing
    db = sqlite3.connect(str(p or workspace.path("ledger.db")), timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\((m|w|d|f|x|all genders?|gn)[/|,\s\w*]*\)", " ", s)       # (m/w/d), (f/m/x) ...
    s = re.sub(r"\b(gmbh|ag|se|kg|co|inc|ltd|llc|bv|nv|ug|haftungsbeschr\w*|& co\.?)\b", " ", s)
    return re.sub(r"[^a-z0-9äöüß]+", " ", s).strip()


def job_key(company, title):
    return "%s|%s" % (norm(company), norm(title))


def url_key(url):
    u = urlparse((url or "").strip())
    return (u.netloc.lower().replace("www.", "") + u.path.rstrip("/")).lower()


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def find(db, company=None, title=None, url=None):
    """Existing job by (company, title) or by URL: the duplicate / already-applied check."""
    if company and title:
        r = db.execute("SELECT * FROM jobs WHERE key=?", (job_key(company, title),)).fetchone()
        if r: return r
    if url:
        k = url_key(url)
        for r in db.execute("SELECT * FROM jobs WHERE url != ''"):
            if url_key(r["url"]) == k: return r
    return None


def add(db, company, title, url="", location="", source="", description=""):
    """Insert a FOUND job unless it already exists. Returns (job_id, created?)."""
    with workspace.file_lock("ledger"):
        old = find(db, company, title, url)
        if old: return old["id"], False
        t = now()
        cur = db.execute("INSERT INTO jobs(key,company,title,url,location,source,description,status,created,updated) "
                         "VALUES(?,?,?,?,?,?,?,?,?,?)", (job_key(company, title), company, title, url, location, source,
                                                         description[:20000], "FOUND", t, t))
        db.execute("INSERT INTO events(job_id,ts,status,note,evidence,actor) VALUES(?,?,?,?,?,?)",
                   (cur.lastrowid, t, "FOUND", source, "", "import"))
        db.commit()
        return cur.lastrowid, True


class EvidenceError(ValueError):
    pass


def check_evidence(status, evidence, url=""):
    if status not in SENT: return
    ev = (evidence or "").strip()
    if not re.match(r"^(page|mail):\s*\S", ev, re.I):
        raise EvidenceError("%s needs evidence starting with 'page: <quoted confirmation text>' or 'mail: <confirmation subject>'" % status)
    if status == "SUBMITTED" and any(h in (url or "") for h in MAIL_ONLY_EVIDENCE) and "mail:" not in ev.lower():
        raise EvidenceError("this platform's on-page badge is not proof: quote the confirmation e-mail ('mail: ...')")
    if re.search(r"\b(badge|clicked|should be|probably|seems)\b", ev, re.I) and "mail:" not in ev.lower():
        raise EvidenceError("evidence must be a confirmation you saw, not an assumption or a badge")


def set_status(db, job_id, status, note="", evidence="", actor="agent", **fields):
    status = status.upper()
    if status not in STATUSES: raise ValueError("unknown status %s (one of %s)" % (status, " ".join(STATUSES)))
    with workspace.file_lock("ledger"):
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job: raise KeyError("no job %s" % job_id)
        if status in NOTE_REQUIRED and not (note or "").strip():
            raise ValueError("%s needs a note (what exactly / why)" % status)
        check_evidence(status, evidence, job["url"])
        if job["status"] in SENT and status not in {"REPLIED", "INTERVIEW", "REJECTED", "OFFER"} | SENT:
            raise ValueError("job %s was already %s; it cannot go back to %s" % (job_id, job["status"], status))
        t = now()
        sets = ["status=?", "note=?", "updated=?"]; vals = [status, note, t]
        for k, v in fields.items():
            if k in ("batch", "folder", "url", "location", "description"):
                sets.append("%s=?" % k); vals.append(v)
        db.execute("UPDATE jobs SET %s WHERE id=?" % ",".join(sets), vals + [job_id])
        db.execute("INSERT INTO events(job_id,ts,status,note,evidence,actor) VALUES(?,?,?,?,?,?)",
                   (job_id, t, status, note, evidence, actor))
        db.commit()


def edit(db, job_id, actor="agent", **fields):
    """Correct company / title / url / location of a job (e.g. LinkedIn link -> the employer's own apply page)."""
    allowed = {k: v for k, v in fields.items() if k in ("company", "title", "url", "location") and v}
    if not allowed: return
    with workspace.file_lock("ledger"):
        j = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        new = dict(j); new.update(allowed)
        sets = ["%s=?" % k for k in allowed] + ["key=?", "updated=?"]
        db.execute("UPDATE jobs SET %s WHERE id=?" % ",".join(sets), list(allowed.values()) + [job_key(new["company"], new["title"]), now(), job_id])
        db.execute("INSERT INTO events(job_id,ts,status,note,evidence,actor) VALUES(?,?,?,?,?,?)",
                   (job_id, now(), j["status"], "edited: " + json.dumps(allowed, ensure_ascii=False), "", actor))
        db.commit()


def sent_event(db, job_id):
    return db.execute("SELECT * FROM events WHERE job_id=? AND status IN ('SUBMITTED','EMAILED') ORDER BY id DESC LIMIT 1",
                      (job_id,)).fetchone()


def jobs(db, status=None, batch=None):
    q, a = "SELECT * FROM jobs WHERE 1=1", []
    if status:
        st = [status] if isinstance(status, str) else list(status)
        q += " AND status IN (%s)" % ",".join("?" * len(st)); a += st
    if batch: q += " AND batch=?"; a.append(batch)
    return db.execute(q + " ORDER BY id", a).fetchall()


def resolve(db, ref):
    """Job by id, folder name, or a unique part of company/title."""
    if str(ref).isdigit():
        r = db.execute("SELECT * FROM jobs WHERE id=?", (int(ref),)).fetchone()
        if r: return r
    r = db.execute("SELECT * FROM jobs WHERE folder=?", (ref,)).fetchone()
    if r: return r
    k = str(ref).lower()
    hits = [r for r in db.execute("SELECT * FROM jobs") if k in (r["company"] + " " + r["title"]).lower()]
    if len(hits) == 1: return hits[0]
    raise KeyError(("ambiguous '%s': %s" % (ref, "; ".join("%d %s" % (h["id"], h["company"]) for h in hits[:8])))
                   if hits else "no job matches '%s'" % ref)


def counts(db, batch=None):
    q, a = "SELECT status, COUNT(*) n FROM jobs", []
    if batch: q += " WHERE batch=?"; a.append(batch)
    return {r["status"]: r["n"] for r in db.execute(q + " GROUP BY status", a)}


def export_rows(db):
    """Rows for the tracker spreadsheet (generated, never edited by hand)."""
    out = []
    for j in jobs(db):
        s = sent_event(db, j["id"])
        out.append({"id": j["id"], "company": j["company"], "title": j["title"], "location": j["location"],
                    "status": j["status"], "note": j["note"], "sent": ("%s %s" % ("Portal" if s["status"] == "SUBMITTED" else "E-Mail", s["ts"][:10])) if s else "",
                    "evidence": s["evidence"] if s else "", "batch": j["batch"], "folder": j["folder"], "url": j["url"],
                    "source": j["source"], "updated": j["updated"][:10]})
    return out
