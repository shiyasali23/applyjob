"""Where everything lives, and the locks that keep parallel agent chats from colliding.

The workspace (default: <repo>/workspace, override with $APPLYJOB_HOME) is PRIVATE and git-ignored:
    profile/profile.json   the applicant (the only source of personal facts)
    profile/photo.jpg      optional
    ledger.db              every job, every status change, every piece of evidence
    batches/<YYYY-MM-DD>_<label>/<job-folder>/   spec.json, cv.pdf, letter.pdf, audit.json
    work/<chat-name>/      the ONLY place an agent may put scratch files
    .locks/                one lock file per area being worked on
"""
import datetime, json, os, re, time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover  (Windows: locks degrade to best effort)
    fcntl = None

REPO = Path(__file__).resolve().parents[1]


def home():
    return Path(os.environ.get("APPLYJOB_HOME") or (REPO / "workspace")).expanduser().resolve()


def path(*parts):
    return home().joinpath(*parts)


def today():
    return datetime.date.today().isoformat()


def slug(text, n=60):
    s = re.sub(r"[^A-Za-z0-9]+", "_", text or "").strip("_")
    return s[:n] or "job"


def init():
    """Create an empty workspace. Never overwrites anything."""
    for d in ("profile", "batches", "work", ".locks", "inbox"):
        path(d).mkdir(parents=True, exist_ok=True)
    if not path("profile", "profile.json").exists():
        path(".onboarding").write_text("")   # first run: the profile may be written (the guard allows it)
    gi = path(".gitignore")
    if not gi.exists():
        gi.write_text("*\n")          # the workspace is private: never commit it
    return home()


@contextmanager
def file_lock(name):
    """Exclusive OS lock for short critical sections (ledger writes)."""
    path(".locks").mkdir(parents=True, exist_ok=True)
    fh = open(path(".locks", name + ".flock"), "w")
    try:
        if fcntl: fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl: fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


# ------------------------------------------------------------------ area claims (chat-level locks)
STALE_HOURS = 6


def claim(area, owner):
    """Claim an area (e.g. 'batch:2026-10-26_berlin') for one chat. Returns (ok, holder)."""
    p = path(".locks", slug(area) + ".claim")
    p.parent.mkdir(parents=True, exist_ok=True)
    with file_lock("claims"):
        if p.exists():
            held = json.loads(p.read_text())
            age_h = (time.time() - held.get("ts", 0)) / 3600
            if held.get("owner") != owner and age_h < STALE_HOURS:
                return False, held
        p.write_text(json.dumps({"area": area, "owner": owner, "ts": time.time(), "since": datetime.datetime.now().isoformat(timespec="minutes")}))
    return True, {"owner": owner}


def release(area, owner):
    p = path(".locks", slug(area) + ".claim")
    with file_lock("claims"):
        if p.exists() and json.loads(p.read_text()).get("owner") == owner:
            p.unlink()
            return True
    return False


def claims():
    out = []
    for p in sorted(path(".locks").glob("*.claim")) if path(".locks").exists() else []:
        out.append(json.loads(p.read_text()))
    return out
