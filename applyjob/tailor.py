"""Tailoring: advert + profile -> a document SPEC (JSON). The agent completes the writing; the code checks it.

A spec holds everything the CV and the letter will say. It starts as a draft:
- facts copied from the profile (experience bullets, education, languages), never invented;
- the advert's terms split into KNOWN (in the profile) and NEW (learnable, decided by the profile's rule);
- skills rows re-ordered so the advert's skills come first;
- empty "TODO" slots for the parts only a writer can do well: summary, reworded bullets, letter paragraphs.
`applyjob render` refuses a spec that still has TODO in it.
"""
import json, re
from . import profile as P, triage, vocab

TODO = "TODO"


def digest(text, n=8000):
    """The advert as one block (intro with the employer's own words, tasks, requirements, values)."""
    return " ".join(text.split())[:n]


def asks(text, what):
    rx = {"salary": r"(gehaltsvorstellung|gehaltswunsch|salary expectation|desired salary)",
          "start": r"(eintrittstermin|frühestmöglichen eintritt|earliest start|start date|notice period|kündigungsfrist)",
          "german": r"(deutsch\w*\W{0,3}(mind(\.|estens)?\s*)?(b1|b2|c1|c2)\b|deutschkenntnisse|deutsch\w*[^.]{0,30}(fließend|verhandlungssicher|sehr gut|c1|c2)|(fließend|verhandlungssicher)[^.]{0,30}deutsch|fluent german)"}[what]
    m = re.search(r"[^.]{0,60}" + rx + r"[^.]{0,60}", text, re.I)
    return m.group(0).strip() if m else ""


def detect_language(text):
    de = len(re.findall(r"\b(und|die|der|wir|sie|mit|für|ihre|deine|bei|eine)\b", text[:4000], re.I))
    en = len(re.findall(r"\b(and|the|we|you|with|for|your|our|will|team)\b", text[:4000], re.I))
    return "de" if de > en else "en"


def draft(job, prof, advert_text, job_id=None):
    pref = prof.get("preferences", {})
    lang = pref.get("document_language", "en")
    if lang == "advert": lang = detect_language(advert_text)
    known = P.known_skills(prof)
    never = {P.norm(x) for x in prof.get("never_claim", [])}
    terms = vocab.find_terms(advert_text, extra=[s for g in prof.get("skills", {}).values() for s in g])
    t_known = [t for t in terms if P.norm(t) in known]
    t_new = [t for t in terms if P.norm(t) not in known and P.norm(t) not in never]
    skills = {}
    for g, items in prof.get("skills", {}).items():
        first = [x for x in items if P.norm(x) in {P.norm(t) for t in terms}]
        skills[g] = first + [x for x in items if x not in first]
    if pref.get("include_learnable_advert_skills") and t_new:
        skills.setdefault(pref.get("learnable_group", "Further skills"), [])
        skills[pref.get("learnable_group", "Further skills")] = t_new + skills[pref.get("learnable_group", "Further skills")]
    title = re.sub(r"\s*\((m|w|d|f|x|all genders?|gn)[^)]*\)\s*", " ", job.get("title") or "", flags=re.I).strip()
    return {
        "job_id": job_id, "company": job.get("company", ""), "title": job.get("title", ""), "url": job.get("url", ""),
        "location": job.get("location", ""), "language": lang,
        "headline": title or TODO,
        "summary": TODO,
        "skills": skills,
        "terms": t_known + (t_new if pref.get("include_learnable_advert_skills") else []),
        "advert_terms_new": t_new,
        "experience": [{"id": e["id"], "bullets": list(e["bullets"])} for e in prof.get("experience", [])],
        "soft_skills": [],
        "mirror": [],              # the employer's own product/team words used in the letter (must appear in the advert)
        "letter": {"to": [job.get("company", "")], "salutation": TODO, "subject": TODO,
                   "paragraphs": [TODO], "closing": TODO},
        "asks_salary": asks(advert_text, "salary"), "asks_start": asks(advert_text, "start"),
        "asks_german": asks(advert_text, "german"),
        "apply_email": triage.apply_email(advert_text),
        "_advert": digest(advert_text),
    }


def has_todo(spec):
    return TODO in json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}, ensure_ascii=False)
