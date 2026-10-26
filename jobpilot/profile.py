"""The applicant profile: the ONLY source of facts about the person.

Agents learn the person from this file (playbooks/00_onboarding.md fills it by interview, never by guessing).
Every later stage reads it; audits reject any claim that is not backed by it.
"""
import json, re
from . import workspace

from . import checklist as C


SKIP_VALUES = {"-", "none", "n/a", "skip"}


def _normalise(node, path, declined):
    """'-' / ['-'] mean "the user declined": store as empty, remember the key, so no stage ever uses '-' as a value."""
    for k, v in list(node.items()):
        key = path + k
        if isinstance(v, dict) and not k.startswith("_"):
            _normalise(v, key + ".", declined)
        elif isinstance(v, str) and v.strip().lower() in ("-", "skip"):
            node[k] = ""; declined.append(key)
        elif isinstance(v, list) and v and all(isinstance(x, str) and x.strip().lower() in SKIP_VALUES for x in v):
            node[k] = []; declined.append(key)


def load(p=None):
    p = p or workspace.path("profile", "profile.json")
    from pathlib import Path
    prof = json.loads(Path(p).read_text(encoding="utf-8"))
    declined = []
    _normalise(prof, "", declined)
    prof["_declined"] = sorted(set(declined) | set(prof.get("_declined") or []))
    return prof


def structure(prof):
    """Shape problems the checklist cannot see (bad experience entries, wrong types)."""
    errs = []
    ids = set()
    for i, e in enumerate(prof.get("experience") or []):
        for k in ("id", "title", "company", "start", "bullets", "stack"):
            if k not in e: errs.append("experience[%d].%s missing" % (i, k))
        if e.get("id") in ids: errs.append("experience id duplicated: %s" % e.get("id"))
        ids.add(e.get("id"))
    if prof.get("skills") and not isinstance(prof["skills"], dict): errs.append("skills must be {group: [skill, ...]}")
    for l in prof.get("languages") or []:
        if not (isinstance(l, dict) and l.get("name") and l.get("level")): errs.append("languages: each needs name + level")
    return errs


def check(prof, levels=("core",)):
    """[] = everything the given levels need is set and well-formed."""
    return structure(prof) + ["missing: %s (%s)" % (q, k) for k, q, lv, kind in C.missing(prof, levels)]


def interview_questions(prof, levels=("core", "apply", "optional")):
    return C.questions(prof, levels)


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def vocabulary(prof):
    """Every tool/skill the profile knows about (lowercase), for claim checks."""
    v = set()
    for items in prof.get("skills", {}).values():
        v.update(norm(x) for x in items)
    for e in prof.get("experience", []):
        v.update(norm(x) for x in e.get("stack", []))
    v.update(norm(x) for x in prof.get("never_claim", []))
    return {x for x in v if x}


def known_skills(prof):
    v = set()
    for items in prof.get("skills", {}).values():
        v.update(norm(x) for x in items)
    for e in prof.get("experience", []):
        v.update(norm(x) for x in e.get("stack", []))
    return v


def experience(prof, eid):
    return next((e for e in prof.get("experience", []) if e.get("id") == eid), None)


def full_name(prof):
    p = prof["person"]
    return "%s %s" % (p["first_name"], p["last_name"])
