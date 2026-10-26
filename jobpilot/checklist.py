"""The checklist: every detail any stage can need, in one array. The agent asks until each item a stage needs is set.

Each item: (key, question, level, kind)
  key       dotted path in profile.json ("person.nationality")
  question  what the agent asks: short, no explanation
  level     core = before search/tailoring · apply = before filling forms · linkedin = before LinkedIn work ·
            email = before outreach mails · optional = asked once, never blocks
  kind      str · list · dict · bool · num · date (YYYY-MM-DD) · file (path in workspace/) · text

A value counts as answered when it is non-empty, or the user declined it: "-" (forms then leave that field to him).
Collected from real applications: every field below once stopped a real form or a real document.
"""
from . import workspace

CHECKLIST = [
    # ---------------------------------------------------------------- identity
    ("person.first_name", "First name", "core", "str"),
    ("person.last_name", "Last name", "core", "str"),
    ("person.preferred_name", "Preferred name (if different)", "optional", "str"),
    ("person.email", "Email for applications", "core", "str"),
    ("person.phone", "Phone (with country code)", "core", "str"),
    ("person.city", "City you live in", "core", "str"),
    ("person.country", "Country you live in", "core", "str"),
    ("person.linkedin", "LinkedIn URL", "core", "str"),
    ("person.github", "GitHub URL", "optional", "str"),
    ("person.website", "Portfolio / website", "optional", "str"),
    ("documents.photo", "Photo for the CV (yes/no)", "core", "bool"),
    # ---------------------------------------------------------------- personal (forms ask)
    ("person.salutation", "Salutation (Mr/Ms/Mx/none)", "apply", "str"),
    ("person.gender", "Gender (for forms)", "apply", "str"),
    ("person.pronouns", "Pronouns", "optional", "str"),
    ("person.date_of_birth", "Date of birth", "apply", "date"),
    ("person.place_of_birth", "Place of birth", "optional", "str"),
    ("person.nationality", "Nationality", "apply", "str"),
    ("person.second_nationality", "Second nationality", "optional", "str"),
    ("person.street", "Street + house number", "apply", "str"),
    ("person.postcode", "Postcode", "apply", "str"),
    ("person.region", "State / region", "optional", "str"),
    ("person.marital_status", "Marital status (some forms ask)", "optional", "str"),
    ("person.disability_status", "Disability status (or 'prefer not to say')", "apply", "str"),
    ("person.eeo_answers", "Diversity self-ID answers (or 'prefer not to say')", "optional", "str"),
    # ---------------------------------------------------------------- work authorisation
    ("person.work_permit", "Work permit (as printed on the CV)", "core", "str"),
    ("person.permit_type", "Permit type (citizen / EU / Blue Card / visa type)", "apply", "str"),
    ("person.permit_valid_until", "Permit valid until", "apply", "date"),
    ("person.needs_sponsorship", "Need visa sponsorship? (yes/no)", "core", "bool"),
    ("person.can_work_in", "Countries you may work in", "apply", "list"),
    ("person.security_clearance", "Security clearance (none/level)", "apply", "str"),
    ("person.background_check_ok", "Background check OK? (yes/no)", "optional", "bool"),
    # ---------------------------------------------------------------- availability and terms
    ("preferences.available_from", "Earliest start date", "core", "str"),
    ("preferences.notice_period", "Notice period", "apply", "str"),
    ("preferences.salary_expectation", "Salary expectation (gross per year + currency)", "core", "str"),
    ("preferences.salary_minimum", "Lowest salary you accept", "optional", "str"),
    ("preferences.contract", "Contract types (full-time/part-time/freelance/...)", "core", "list"),
    ("preferences.weekly_hours", "Weekly hours", "optional", "num"),
    ("preferences.work_mode", "Work mode (onsite/hybrid/remote)", "core", "list"),
    ("preferences.office_days_ok", "Office days per week you accept", "apply", "str"),
    ("preferences.relocation", "Relocate? (yes/no)", "core", "bool"),
    ("preferences.relocation_regions", "Where you would relocate", "apply", "list"),
    ("preferences.travel_ok", "Business travel OK? (none/%)", "apply", "str"),
    ("person.drivers_licence", "Driver's licence (no / class)", "apply", "str"),
    ("person.own_car", "Own car (yes/no)", "optional", "bool"),
    # ---------------------------------------------------------------- experience numbers (forms ask)
    ("answers.years_experience", "Years of experience to state", "core", "num"),
    ("answers.years_experience_excl_internships", "Years excluding internships", "apply", "num"),
    ("answers.years_by_field", "Years per field (e.g. ML: 3, e-commerce: 0)", "apply", "text"),
    ("answers.people_managed", "People you managed (0 if none)", "apply", "num"),
    ("answers.industries", "Industries you worked in", "apply", "list"),
    ("answers.startups_worked_with", "Start-ups you worked at (or none)", "optional", "list"),
    ("answers.teaching_experience", "Teaching / training experience", "optional", "str"),
    ("answers.previous_employers_to_flag", "Companies you worked for before (re-hire questions)", "optional", "list"),
    ("answers.relatives_at_companies", "Relatives at a company you apply to (conflict-of-interest)", "optional", "str"),
    # ---------------------------------------------------------------- education and languages
    ("education", "Degrees (degree, school, dates, grade)", "core", "list"),
    ("answers.highest_degree", "Highest degree (one line)", "core", "str"),
    ("languages", "Languages + level (CEFR)", "core", "list"),
    ("answers.language_certificates", "Language certificates", "optional", "list"),
    ("certifications", "Certifications", "optional", "list"),
    # ---------------------------------------------------------------- experience and skills (from the CV)
    ("documents.master_cv", "Master CV file (PDF/Word)", "core", "file"),
    ("experience", "Every role: title, company, dates, tools used, achievements with numbers", "core", "list"),
    ("skills", "Skills, grouped", "core", "dict"),
    ("summary", "One-line professional summary", "core", "str"),
    ("never_claim", "Tools/languages you do NOT know", "core", "list"),
    ("never_mention", "Things never to mention (gaps, side jobs)", "core", "list"),
    ("preferences.include_learnable_advert_skills", "List advert skills you can learn fast? (yes/no)", "core", "bool"),
    # ---------------------------------------------------------------- what to apply for
    ("preferences.target_roles", "Target job titles", "core", "list"),
    ("preferences.locations", "Cities / countries", "core", "list"),
    ("preferences.exclude_title_words", "Title words to skip (Senior, Lead, ...)", "core", "list"),
    ("preferences.max_years_required", "Max years an advert may ask", "core", "num"),
    ("preferences.blockers", "Hard no's (clearance, PhD, ...)", "optional", "list"),
    ("preferences.industries_excluded", "Industries to avoid", "optional", "list"),
    ("preferences.companies_excluded", "Companies to avoid", "optional", "list"),
    ("preferences.apply_if_language_required", "Apply when a language you lack is required? (yes/no)", "core", "bool"),
    ("preferences.document_language", "CV/letter language (en/de/advert)", "core", "str"),
    # ---------------------------------------------------------------- documents and form uploads
    ("documents.certificates_pdf", "Certificates as one PDF (for forms that require it)", "apply", "file"),
    ("documents.transcript_pdf", "Degree certificate / transcript PDF", "optional", "file"),
    ("documents.work_references_pdf", "Work references PDF", "optional", "file"),
    ("answers.reference_contact", "A reference (name, role, email/phone, relation)", "apply", "text"),
    ("writing.letter_required_sentence", "A sentence every letter must contain", "optional", "text"),
    ("writing.banned_phrases", "Words never to use", "optional", "list"),
    # ---------------------------------------------------------------- form answers
    ("answers.source_answer", "'How did you hear about us?' answer", "apply", "str"),
    ("answers.talent_pool", "Join talent pools? (yes/no)", "apply", "bool"),
    ("answers.newsletter", "Newsletters? (yes/no)", "apply", "bool"),
    ("answers.essay_policy", "Essay questions: draft for your OK, or leave to you?", "apply", "str"),
    # ---------------------------------------------------------------- browser and accounts
    ("accounts.browser_profile", "Browser profile / email you are logged in with", "apply", "str"),
    ("accounts.existing", "Job sites where you already have an account", "optional", "list"),
    # ---------------------------------------------------------------- LinkedIn
    ("linkedin.profile_text", "LinkedIn profile text or PDF export", "linkedin", "file"),
    ("linkedin.edit_mode", "LinkedIn: drafts only, or edit in your browser (you click Save)?", "linkedin", "str"),
    ("linkedin.keep", "LinkedIn: things never to remove or change", "linkedin", "list"),
    ("linkedin.off_limits", "LinkedIn: entries to keep off LinkedIn", "linkedin", "list"),
    ("linkedin.voice", "LinkedIn voice (e.g. plain, senior)", "linkedin", "str"),
    ("linkedin.language", "LinkedIn language(s)", "linkedin", "str"),
    ("linkedin.open_to_work", "Open to Work: recruiters only / public / off", "linkedin", "str"),
    # ---------------------------------------------------------------- outreach e-mail
    ("email.send_from", "Email address to send from", "email", "str"),
    ("email.signature", "Email signature", "email", "text"),
    ("email.per_week", "Max outreach emails per week", "email", "num"),
    ("email.follow_up", "Follow-ups (none / one after N days)", "email", "str"),
]

LEVELS = ("core", "apply", "linkedin", "email", "optional")
# which levels each stage needs complete before it may run
STAGE_NEEDS = {"search": ("core",), "triage": ("core",), "tailor": ("core",), "render": ("core",), "audit": ("core",),
               "queue": ("core", "apply"), "approve": ("core", "apply"), "gaps": ("core", "linkedin"),
               "linkedin": ("core", "linkedin"), "email": ("core", "email")}
DECLINED = "-"


def get(prof, key):
    cur = prof
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur: return None
        cur = cur[part]
    return cur


def _yes(v):
    return v is True or str(v).strip().lower() in ("yes", "ja", "true", "y")


def _citizen(prof):
    s = " ".join(str(get(prof, k) or "") for k in ("person.permit_type", "person.work_permit")).lower()
    return any(w in s for w in ("citizen", "staatsbürger", "eu ", "eu-", "eu/", "passport")) or s.strip() in ("eu", "eea")


# a question that does not apply to this person counts as answered
WHEN = {
    "preferences.relocation_regions": lambda p: _yes(get(p, "preferences.relocation")),
    "person.permit_valid_until": lambda p: not _citizen(p),
    "preferences.office_days_ok": lambda p: any(m in ("hybrid", "onsite") for m in (get(p, "preferences.work_mode") or [])),
    "answers.years_experience_excl_internships": lambda p: any((e.get("kind") == "internship" or "intern" in (e.get("title") or "").lower()
                                                               or "praktik" in (e.get("title") or "").lower()) for e in (get(p, "experience") or [])),
}


def answered(prof, key, kind):
    if key in (prof.get("_declined") or []): return True
    if key in WHEN and not WHEN[key](prof): return True
    v = get(prof, key)
    if v is None: return False
    if v == DECLINED: return True
    if isinstance(v, bool): return True
    if isinstance(v, (int, float)): return True
    if kind == "file" and isinstance(v, str) and v and v != DECLINED:
        p = workspace.path(v) if not v.startswith("/") else None
        return bool(p and p.exists())
    return bool(v)


def missing(prof, levels):
    return [(k, q, lv, kind) for k, q, lv, kind in CHECKLIST if lv in levels and not answered(prof, k, kind)]


def report(prof):
    """{level: (answered, total)}"""
    out = {}
    for lv in LEVELS:
        items = [c for c in CHECKLIST if c[2] == lv]
        out[lv] = (sum(answered(prof, k, kind) for k, _, _, kind in items), len(items))
    return out


def questions(prof, levels):
    """Short bullet questions, grouped by level, for ONE message to the user."""
    lines = []
    for lv in levels:
        qs = [q for k, q, l, kind in CHECKLIST if l == lv and not answered(prof, k, kind)]
        if qs:
            lines.append("%s:" % {"core": "Needed to start", "apply": "Needed for application forms", "linkedin": "LinkedIn",
                                  "email": "Outreach email", "optional": "Optional (say '-' to skip)"}[lv])
            lines += ["- " + q for q in qs]
    return "\n".join(lines)


def skeleton():
    """An empty profile with every checklist key, for onboarding (the agent fills it)."""
    prof = {}
    for k, _, _, kind in CHECKLIST:
        cur = prof
        parts = k.split(".")
        for p in parts[:-1]: cur = cur.setdefault(p, {})
        cur.setdefault(parts[-1], {"list": [], "dict": {}, "bool": None, "num": None}.get(kind, ""))
    return prof
