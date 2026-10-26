"""Atomic audit of one application: every finding is one problem, at one place, with evidence and a fix.

    finding = {"id": "A07", "severity": "BLOCKER|MAJOR|MINOR", "where": "letter.p2", "rule": "...",
               "evidence": "...", "fix": "..."}

BLOCKER = would be false or broken (fabricated fact, wrong company, unreadable PDF). Never send.
MAJOR   = costs the interview (missing advert skill, title not in headline, letter too long). Fix before sending.
MINOR   = polish. Fix when cheap.
A job is AUDITED only with zero BLOCKER and zero MAJOR findings. The agent loops: audit -> fix spec -> render -> audit.
"""
import re
from pathlib import Path
from . import profile as P, vocab
from .tailor import TODO, has_todo

DEFAULT_BANNED = ["passionate", "leidenschaft", "synergy", "synergie", "innovativ", "spannend", "nahtlos", "seamless",
                  "hiermit bewerbe", "i am writing to", "darüber hinaus", "moreover", "furthermore", "cutting-edge",
                  "rockstar", "ninja", "guru", "hardworking", "team player", "results-driven", "dynamic", "leverage"]
NEGATIVE = ["leider", "unfortunately", "noch nicht", "not yet", "habe ich nicht", "i have not", "i haven't", "only a2",
            "nur a2", "no experience", "keine erfahrung", "although i lack", "obwohl ich"]


class Audit:
    def __init__(self):
        self.f = []

    def add(self, sev, where, rule, evidence, fix):
        self.f.append({"id": "A%02d" % (len(self.f) + 1), "severity": sev, "where": where, "rule": rule,
                       "evidence": str(evidence)[:300], "fix": fix})


def words(t):
    return re.findall(r"[\wÄÖÜäöüß'-]+", t or "")


def sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", (t or "").strip()) if s]


def numbers(t):
    """Numbers without separators, so "1.2 TB" (en) == "1,2 TB" (de) and "186,956" == "186.956"."""
    return {re.sub(r"[.,]", "", n) for n in re.findall(r"\d+(?:[.,]\d+)*", t or "")}


def clean_title(t):
    return re.sub(r"\s*\((m|w|d|f|x|all genders?|gn)[^)]*\)\s*", " ", t or "", flags=re.I).strip()


def check_text(a, where, text, prof, banned):
    low = (text or "").lower()
    for w in banned:
        if w in low: a.add("MAJOR", where, "no buzzwords", w, "rewrite without '%s'" % w)
    for w in NEGATIVE:
        if w in low: a.add("MAJOR", where, "nothing negative or hedging", w, "state what you can do; drop '%s'" % w)
    for w in prof.get("never_mention", []):
        if w.lower() in low: a.add("BLOCKER", where, "never mention (profile.never_mention)", w, "remove it")
    for w in prof.get("never_claim", []):
        if vocab.rx(w).search(text or ""): a.add("BLOCKER", where, "never claim (profile.never_claim)", w, "remove it")
    if "—" in (text or "") or " – " in (text or ""):
        a.add("MINOR", where, "no em/en dashes in prose", "—", "use a comma or a full stop")


def audit_spec(spec, prof):
    a = Audit()
    w = prof.get("writing", {})
    banned = [b.lower() for b in DEFAULT_BANNED + w.get("banned_phrases", [])]
    if has_todo(spec):
        a.add("BLOCKER", "spec", "no TODO left", "TODO present", "write every TODO field")
    # headline
    t = clean_title(spec.get("title"))
    if t and spec.get("headline") and P.norm(t) not in P.norm(spec["headline"]) and P.norm(spec["headline"]) not in P.norm(t):
        a.add("MAJOR", "cv.headline", "headline = the posting title (ATS match)", spec["headline"], "use '%s'" % t)
    # summary
    s = spec.get("summary", "")
    if s != TODO:
        n = len(words(s))
        lo, hi = w.get("summary_words", [35, 95])
        if not lo <= n <= hi: a.add("MAJOR", "cv.summary", "summary %d-%d words" % (lo, hi), "%d words" % n, "shorten or lengthen")
        check_text(a, "cv.summary", s, prof, banned)
        bad = numbers(s) - set().union(*[numbers(" ".join(e["bullets"]) + " " + str(e.get("start", "")) + " " + str(e.get("end", "")))
                                         for e in prof["experience"]] or [set()]) - numbers(prof.get("summary", "")) - numbers(" ".join(prof.get("facts", [])))
        if bad: a.add("BLOCKER", "cv.summary", "every number must exist in the profile", sorted(bad), "use the profile's numbers only")
    # experience bullets: claims and numbers
    known_ids = {e["id"] for e in prof["experience"]}
    for x in spec.get("experience", []):
        src = P.experience(prof, x.get("id"))
        if not src:
            a.add("BLOCKER", "cv.experience", "experience id must exist in the profile", x.get("id"), "use a profile experience id"); continue
        stack = {P.norm(k) for k in src.get("stack", [])}
        src_nums = numbers(" ".join(src["bullets"]))
        for i, b in enumerate(x.get("bullets", [])):
            where = "cv.%s.b%d" % (x["id"], i + 1)
            for term in vocab.find_terms(b, extra=list(P.vocabulary(prof))):
                if P.norm(term) not in stack and P.norm(term) not in vocab.CONCEPTS:
                    a.add("BLOCKER", where, "a bullet names only tools that THIS role used (its stack)", term,
                          "remove '%s' from this bullet (it can stay in the skills rows)" % term)
            extra = numbers(b) - src_nums
            if extra: a.add("BLOCKER", where, "bullet numbers must come from this role's profile bullets", sorted(extra), "use the profile numbers")
            check_text(a, where, b, prof, banned)
        if len(x.get("bullets", [])) > len(src["bullets"]) + 1:
            a.add("MINOR", "cv.%s" % x["id"], "do not pad a role", "%d bullets" % len(x["bullets"]), "merge or drop bullets")
    missing_roles = known_ids - {x.get("id") for x in spec.get("experience", [])}
    if missing_roles and not w.get("allow_dropping_roles"):
        a.add("MAJOR", "cv.experience", "keep every role (no gaps)", sorted(missing_roles), "put the role back")
    # skills
    seen = {}
    known = P.known_skills(prof)
    learnable = prof.get("preferences", {}).get("include_learnable_advert_skills")
    for g, items in spec.get("skills", {}).items():
        for it in items:
            k = P.norm(it)
            if k in seen: a.add("MINOR", "cv.skills.%s" % g, "a skill appears once", it, "drop it from '%s' or '%s'" % (g, seen[k]))
            seen[k] = g
            if k not in known and not learnable:
                a.add("MAJOR", "cv.skills.%s" % g, "skills only from the profile (learnable skills are off)", it, "remove it or add it to the profile")
        check_text(a, "cv.skills.%s" % g, ", ".join(items), prof, [])
    cv_text = " ".join([spec.get("headline", ""), s] + [", ".join(v) for v in spec.get("skills", {}).values()]
                       + [b for x in spec.get("experience", []) for b in x.get("bullets", [])])
    for term in spec.get("terms", []):
        if not vocab.rx(term).search(cv_text):
            a.add("MAJOR", "cv", "every advert term in `terms` appears on the CV", term, "add '%s' to a skills row" % term)
    want_soft = w.get("soft_skills", 3)
    if want_soft and len(spec.get("soft_skills", [])) != want_soft:
        a.add("MINOR", "cv.soft_skills", "%d soft skills from the advert's values" % want_soft, len(spec.get("soft_skills", [])), "write them")
    # letter
    L = spec.get("letter", {})
    body = " ".join(L.get("paragraphs", []))
    if body and TODO not in body:
        n = len(words(body)); lo, hi = w.get("letter_words", [110, 170])
        if not lo <= n <= hi: a.add("MAJOR", "letter", "letter body %d-%d words" % (lo, hi), "%d words" % n, "cut or add")
        mx = w.get("max_sentence_words", 24)
        for i, p in enumerate(L.get("paragraphs", [])):
            for snt in sentences(p):
                if len(words(snt)) > mx:
                    a.add("MINOR", "letter.p%d" % (i + 1), "sentences <= %d words" % mx, snt[:80] + "...", "split it")
            check_text(a, "letter.p%d" % (i + 1), p, prof, banned)
        req = w.get("letter_required_sentence")
        if req and req not in body:
            a.add("MAJOR", "letter", "the profile's required sentence is in the letter", req[:60] + "...", "add it verbatim")
        comp = re.sub(r"\b(gmbh|ag|se|kg|inc|ltd|llc|co)\b\.?", "", spec.get("company", ""), flags=re.I).strip(" ,&")
        if comp and comp.split()[0].lower() not in body.lower():
            a.add("MAJOR", "letter", "the letter names the company", comp, "mention %s in paragraph 1" % comp)
        allnums = set().union(*[numbers(" ".join(e["bullets"])) for e in prof["experience"]]) | numbers(" ".join(prof.get("facts", [])))
        sal = str(prof.get("preferences", {}).get("salary_expectation", ""))
        bad = numbers(body) - allnums - numbers(sal) - numbers(spec.get("title", ""))
        if bad: a.add("BLOCKER", "letter", "every number must exist in the profile", sorted(bad), "use profile numbers only")
        if sal and any(x in body for x in numbers(sal)) and not spec.get("asks_salary"):
            a.add("MAJOR", "letter", "salary only when the advert asks", sal, "remove the salary sentence")
        if spec.get("asks_salary") and sal and not any(x in body for x in numbers(sal)):
            a.add("MAJOR", "letter", "the advert asks for salary: give it", spec["asks_salary"][:80], "add '%s'" % sal)
        mirror = {P.norm(m) for m in spec.get("mirror", [])}
        advert = (spec.get("_advert") or "").lower()
        for m in spec.get("mirror", []):
            if m.lower() not in advert:
                a.add("MAJOR", "spec.mirror", "mirror words are the employer's own words (they appear in the advert)", m, "remove it from mirror")
        for term in vocab.find_terms(body, extra=list(P.vocabulary(prof))):
            if P.norm(term) in mirror and term.lower() in advert:
                continue                                      # the employer's product/team name, not a claim
            if P.norm(term) not in known and P.norm(term) not in vocab.CONCEPTS:
                a.add("BLOCKER", "letter", "the letter claims only skills from the profile", term, "remove '%s' from the letter" % term)
    to0 = (L.get("to") or [""])[0]
    if spec.get("company") and to0 and P.norm(spec["company"].split()[0]) not in P.norm(to0):
        a.add("BLOCKER", "letter.to", "the letter is addressed to the right company", to0, "first line of letter.to = %s" % spec["company"])
    if L.get("subject") and L["subject"] != TODO and P.norm(t) not in P.norm(L["subject"]):
        a.add("MAJOR", "letter.subject", "subject names the exact posting title", L["subject"], "use '... %s'" % t)
    if L.get("salutation") in (None, "", TODO):
        a.add("BLOCKER", "letter.salutation", "salutation is written", L.get("salutation"), "write it (named contact if the advert has one)")
    return a.f


def audit_pdfs(folder, spec, prof):
    import fitz
    a = Audit(); folder = Path(folder)
    mx = prof.get("preferences", {}).get("cv_max_pages", 2)
    for name, pages_max in (("cv.pdf", mx), ("letter.pdf", 1)):
        p = folder / name
        if not p.exists():
            a.add("BLOCKER", name, "file exists", "missing", "run jobpilot render"); continue
        doc = fitz.open(p)
        raw = "\n".join(pg.get_text() for pg in doc)
        text = " ".join(re.sub(r"(\w)-\n(\w)", r"\1-\2", raw).split())   # a word wrapped at its own hyphen is one word
        if doc.page_count > pages_max: a.add("MAJOR", name, "%s fits %d page(s)" % (name, pages_max), "%d pages" % doc.page_count, "shorten")
        if len(text) < 300: a.add("BLOCKER", name, "text-based PDF (ATS)", "%d chars of text" % len(text), "re-render")
        for must in (P.full_name(prof), prof["person"]["email"]):
            if must not in text: a.add("BLOCKER", name, "name and e-mail on the page", must, "check the profile/template")
        lig = sorted(set(re.findall("[\ufb00-\ufb06\u00a0]", " ".join(pg.get_text() for pg in doc))))
        if lig: a.add("BLOCKER", name, "ATS-clean text (no ligature / no-break-space characters)", [hex(ord(c)) for c in lig],
                      "set preferences.font to a TTF pair that passes render.pick_font()")
        for junk in ("TODO", "None", "{{", "�"):
            if junk in text: a.add("BLOCKER", name, "no placeholders or broken characters", junk, "fix the spec")
        kb = p.stat().st_size // 1024
        if kb > 1900: a.add("MAJOR", name, "under 2 MB (portal limits)", "%d KB" % kb, "smaller photo")
        elif kb > 1000: a.add("MINOR", name, "under 1 MB is safest", "%d KB" % kb, "smaller photo")
        if name == "cv.pdf":
            if spec.get("headline") and " ".join(spec["headline"].split()) not in text:
                a.add("MAJOR", name, "headline printed", spec["headline"], "re-render")
            for term in spec.get("terms", []):
                if not vocab.rx(term).search(text):
                    a.add("MAJOR", name, "advert term on the rendered CV", term, "add it to a skills row")
        else:
            if spec.get("company", "").split()[0] not in text:
                a.add("BLOCKER", name, "letter addressed to the right company", spec.get("company"), "fix letter.to")
    return a.f


def audit(folder, spec, prof):
    f = audit_spec(spec, prof)
    if not has_todo(spec): f += audit_pdfs(folder, spec, prof)
    for i, x in enumerate(f): x["id"] = "A%02d" % (i + 1)
    return f


def passed(findings):
    return not any(x["severity"] in ("BLOCKER", "MAJOR") for x in findings)
