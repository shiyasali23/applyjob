"""Triage: GOOD / CHECK / REMOVED for one job, from the profile's preferences. Deterministic and explainable.

The agent then READS every CHECK advert and decides (playbooks/20_triage.md). The code never silently drops a
borderline job: anything uncertain is CHECK with the reason, not REMOVED.
"""
import re

CONTRACT_WORDS = {
    "internship": r"\b(intern(ship)?|praktik\w*|praktikant\w*)\b",
    "working-student": r"\b(werkstudent\w*|working student|studentische)\b",
    "part-time": r"\b(teilzeit|part[- ]time|minijob)\b",
    "thesis": r"\b(abschlussarbeit|masterarbeit|bachelorarbeit|thesis)\b",
    "apprenticeship": r"\b(ausbildung|azubi|apprentice\w*|duales studium)\b",
    "freelance": r"\b(freelanc\w*|freiberuf\w*)\b",
}
YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|jahre?n?)\b[^.]{0,40}(experience|erfahrung|berufserfahrung)", re.I)
GERMAN_REQ = re.compile(r"(deutsch\w*\W{0,3}(mind(\.|estens)?\s*|ab\s*)?(b1|b2|c1|c2)\b|deutsch\w*[^.]{0,40}(fließend|verhandlungssicher|sehr gut|c1|c2|muttersprach)|(fließend|verhandlungssicher|sehr gute?)[^.]{0,30}deutsch|fluent german|german[^.]{0,20}(c1|c2|fluent|native))", re.I)


FILLER = {"and", "und", "the", "of", "for", "für", "&", "/", "-", "m", "w", "d", "f", "x"}


def role_in_title(role, title):
    """Every word of the target role appears in the title (whole words; "KI" matches "KI-Engineer").
    "Data Analyst" matches "Junior Data Analyst (m/w/d)", not "Data Engineer"."""
    words = [w for w in re.findall(r"[a-zäöüß0-9+#]+", role.lower()) if w not in FILLER]
    t = title.lower()
    return bool(words) and all(re.search(r"(?<![a-zäöüß])" + re.escape(w) + r"(?![a-zäöüß])", t) for w in words)


def wb(word):
    return re.compile(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", re.I)


APPLY_MAIL = re.compile(r"(bewerb\w*|lebenslauf|unterlagen|application|apply|cv|resume|mail)[^.@]{0,80}?([\w.+-]+@[\w-]+\.[\w.-]+\w)|"
                        r"([\w.+-]+@[\w-]+\.[\w.-]+\w)[^.]{0,40}(bewerb\w*|lebenslauf|application|cv)", re.I)


def apply_email(text):
    """The address an advert asks applications to be sent to, if it asks for e-mail applications."""
    m = APPLY_MAIL.search(text or "")
    return (m.group(2) or m.group(3)) if m else ""


def judge(job, prof, advert_status="UNKNOWN", text=""):
    """-> (verdict, [reasons]).  job: dict with title, company, url."""
    pref = prof.get("preferences", {})
    title = job.get("title") or ""
    reasons = []
    if advert_status == "CLOSED":
        return "CLOSED", ["advert closed"]
    for w in pref.get("exclude_title_words", []):
        compound = len(w) >= 5 and re.search(r"[A-Za-zÄÖÜäöüß]+" + re.escape(w.lower()) + r"\b", title.lower())   # Projektmanager
        if wb(w).search(title) or compound:
            return "REMOVED", ["title has excluded word '%s'" % w]
    allowed = {c.lower() for c in pref.get("contract", ["full-time"])}
    for kind, rx in CONTRACT_WORDS.items():
        if kind not in allowed and re.search(rx, title, re.I):
            return "REMOVED", ["contract type '%s' not wanted" % kind]
    for rx in pref.get("blockers", []):                       # e.g. "security clearance", "PhD required"
        m = re.search(rx, text, re.I)
        if m: reasons.append("blocker: '%s'" % m.group(0)[:60])
    roles = [r.lower() for r in pref.get("target_roles", [])]
    hay = (title + " " + text[:3000]).lower()
    if roles and not any(role_in_title(r, title) for r in roles):
        reasons.append("title matches no target role")
    mx = pref.get("max_years_required")
    if mx:
        for m in YEARS_RE.finditer(text):
            if int(m.group(1)) > int(mx): reasons.append("asks %s+ years" % m.group(1)); break
    places = [l.lower() for l in pref.get("locations", []) if l.lower() != "remote"]
    remote_ok = any(l.lower() == "remote" for l in pref.get("locations", [])) or "remote" in [m.lower() for m in pref.get("work_mode", [])]
    loc = (job.get("location") or "").lower()
    is_remote = bool(re.search(r"\b(remote|homeoffice|home office|100 ?% mobil)\b", loc + " " + hay[:3000]))
    if places and loc and not pref.get("relocation") and not any(l in loc or loc in l for l in places) and not (remote_ok and is_remote):
        reasons.append("location '%s' not in preferences" % job.get("location"))
    if advert_status != "LIVE":
        reasons.append("advert could not be read (%s): check by hand" % advert_status)
    info = []
    m = GERMAN_REQ.search(text)
    if m: info.append("asks German: '%s'" % " ".join(m.group(0).split())[:40])
    mail = apply_email(text)
    if mail: info.append("apply by e-mail: %s" % mail)
    return ("CHECK" if reasons else "GOOD"), reasons + info
