"""Finding jobs: official public APIs + imports. No scraping of sites that forbid it (LinkedIn search results).

search:  arbeitsagentur (Germany's federal job board API), greenhouse / lever / ashby / personio / smartrecruiters
         company boards (public posting APIs, the same ones the career pages use).
import:  an Excel/CSV sheet, or free text full of links (LinkedIn job-alert e-mails, a pasted list, a chat).
fetch:   one advert -> (status LIVE/CLOSED/UNKNOWN, plain text)
"""
import base64, csv, html as htmlmod, json, re, ssl, urllib.parse, urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
BA_KEY = {"X-API-Key": "jobboerse-jobsuche"}      # public key used by arbeitsagentur.de itself


def get(url, headers=None, limit=2_000_000):
    h = {"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}; h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25, context=ssl.create_default_context()) as r:
            return r.status, r.read(limit).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return None, ""


def text_of(html):
    html = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>|</(p|li|div|h\d|tr)>", "\n", html, flags=re.I)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", html))
    return "\n".join(" ".join(l.split()) for l in t.split("\n") if l.strip())


CLOSED_RE = re.compile(r"(nicht mehr verfügbar|no longer (available|accepting)|stelle (ist )?(bereits )?besetzt|"
                       r"anzeige (ist )?abgelaufen|position (has been )?filled|job (is )?closed|keine bewerbungen mehr)", re.I)


def fetch(url):
    """One advert -> (LIVE|CLOSED|UNKNOWN, text). Uses the platform API when there is one."""
    m = re.search(r"arbeitsagentur\.de/jobsuche/jobdetail/([^/?#]+)", url)
    if m:
        s, b = get("https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails/" +
                   base64.b64encode(m.group(1).encode()).decode(), BA_KEY)
        if s == 200:
            j = json.loads(b)
            return "LIVE", "%s\n%s\n%s" % (j.get("stellenangebotsTitel", ""), j.get("firmenname", ""), j.get("stellenangebotsBeschreibung", ""))
        return ("CLOSED" if s in (400, 404, 410) else "UNKNOWN"), ""
    m = re.search(r"jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", url)
    if m:
        s, b = get("https://api.ashbyhq.com/posting-api/job-board/%s" % m.group(1))
        if s == 200:
            for j in json.loads(b).get("jobs", []):
                if j.get("id") == m.group(2): return "LIVE", "%s\n%s" % (j.get("title", ""), text_of(j.get("descriptionHtml", "")))
            return "CLOSED", ""
    m = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if m:
        s, b = get("https://boards-api.greenhouse.io/v1/boards/%s/jobs/%s" % m.groups())
        if s == 200:
            j = json.loads(b); return "LIVE", "%s\n%s" % (j.get("title", ""), text_of(htmlmod.unescape(j.get("content", ""))))
        return ("CLOSED" if s == 404 else "UNKNOWN"), ""
    m = re.search(r"jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})", url)
    if m:
        s, b = get("https://api.lever.co/v0/postings/%s/%s" % m.groups())
        if s == 200:
            j = json.loads(b); return "LIVE", "%s\n%s" % (j.get("text", ""), j.get("descriptionPlain", "") + "\n" + "\n".join(
                l.get("text", "") + "\n" + text_of(l.get("content", "")) for l in j.get("lists", [])))
        return ("CLOSED" if s == 404 else "UNKNOWN"), ""
    m = re.search(r"smartrecruiters\.com/([^/]+)/(\d+)", url)
    if m:
        s, b = get("https://api.smartrecruiters.com/v1/companies/%s/postings/%s" % m.groups())
        if s == 200:
            j = json.loads(b); sec = j.get("jobAd", {}).get("sections", {})
            return "LIVE", "%s\n%s" % (j.get("name", ""), "\n".join(text_of(v.get("text", "")) for v in sec.values() if isinstance(v, dict)))
        return ("CLOSED" if s == 404 else "UNKNOWN"), ""
    s, b = get(url)
    if s in (404, 410): return "CLOSED", ""
    t = text_of(b)
    if CLOSED_RE.search(t[:30000]): return "CLOSED", t
    return ("LIVE" if s == 200 and len(t) > 400 else "UNKNOWN"), t


# ------------------------------------------------------------------ search: official APIs
def search_arbeitsagentur(what, where="Deutschland", pages=5, days=30, fulltime=True):
    """Bundesagentur für Arbeit job exchange (v6 search API, the one its own site uses)."""
    out = []
    for page in range(1, pages + 1):
        q = {"was": what, "wo": where or "Deutschland", "angebotsart": 1, "veroeffentlichtseit": days, "size": 100, "page": page}
        if fulltime: q["arbeitszeit"] = "vz"
        s, b = get("https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs?" + urllib.parse.urlencode(q), BA_KEY)
        if s != 200: break
        items = json.loads(b).get("ergebnisliste") or []
        for j in items:
            ref = j.get("referenznummer")
            if not ref: continue
            places = ", ".join(dict.fromkeys((l.get("adresse") or {}).get("ort", "") for l in j.get("stellenlokationen") or [] if (l.get("adresse") or {}).get("ort")))
            out.append({"company": j.get("firma", ""), "title": j.get("stellenangebotsTitel", ""), "location": places,
                        "url": "https://www.arbeitsagentur.de/jobsuche/jobdetail/" + ref, "source": "arbeitsagentur"})
        if len(items) < 100: break
    return out


def search_board(platform, token):
    """All open jobs of one company board. platform: greenhouse|lever|ashby|personio|smartrecruiters."""
    out = []
    if platform == "greenhouse":
        s, b = get("https://boards-api.greenhouse.io/v1/boards/%s/jobs" % token)
        for j in (json.loads(b).get("jobs", []) if s == 200 else []):
            out.append({"company": token, "title": j.get("title", ""), "location": (j.get("location") or {}).get("name", ""), "url": j.get("absolute_url", "")})
    elif platform == "lever":
        s, b = get("https://api.lever.co/v0/postings/%s?mode=json" % token)
        for j in (json.loads(b) if s == 200 else []):
            out.append({"company": token, "title": j.get("text", ""), "location": (j.get("categories") or {}).get("location", ""), "url": j.get("hostedUrl", "")})
    elif platform == "ashby":
        s, b = get("https://api.ashbyhq.com/posting-api/job-board/%s" % token)
        for j in (json.loads(b).get("jobs", []) if s == 200 else []):
            out.append({"company": token, "title": j.get("title", ""), "location": j.get("location", ""), "url": j.get("jobUrl", "")})
    elif platform == "personio":
        s, b = get("https://%s.jobs.personio.de/xml" % token)
        for m in re.finditer(r"<position>(.*?)</position>", b or "", re.S):
            x = m.group(1); g = lambda t: (re.search(r"<%s>(.*?)</%s>" % (t, t), x, re.S) or [None, ""])[1]
            out.append({"company": token, "title": htmlmod.unescape(g("name")), "location": g("office"),
                        "url": "https://%s.jobs.personio.de/job/%s" % (token, g("id"))})
    elif platform == "smartrecruiters":
        s, b = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100" % token)
        for j in (json.loads(b).get("content", []) if s == 200 else []):
            out.append({"company": (j.get("company") or {}).get("name", token), "title": j.get("name", ""),
                        "location": (j.get("location") or {}).get("city", ""), "url": "https://jobs.smartrecruiters.com/%s/%s" % (token, j.get("id"))})
    else:
        raise ValueError("unknown platform %s" % platform)
    for o in out: o["source"] = platform
    return out


# ------------------------------------------------------------------ imports
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
JOB_URL_HINT = re.compile(r"(job|career|karriere|stellen|position|vacanc|apply|bewerb|posting|jobs\.|greenhouse|lever\.co|ashbyhq|personio|smartrecruiters|workday|linkedin\.com/jobs/view)", re.I)


def clean_url(u):
    u = u.rstrip(".,;")
    m = re.search(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)", u)
    if m: return "https://www.linkedin.com/jobs/view/%s/" % m.group(1)      # strip tracking parameters
    return re.sub(r"[?&](utm_[^&]+|trk[^&]*|refId=[^&]+|trackingId=[^&]+)", "", u)


def import_text(text):
    """Every job link in a block of text (a LinkedIn job-alert mail, a chat, a list)."""
    seen, out = set(), []
    for u in URL_RE.findall(text or ""):
        u = clean_url(u)
        if JOB_URL_HINT.search(u) and u not in seen:
            seen.add(u); out.append({"company": "", "title": "", "location": "", "url": u, "source": "import:text"})
    return out


def import_sheet(p):
    """Excel or CSV: finds the company / title / url / location columns by their header names."""
    p = Path(p).expanduser()
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        rows = list(openpyxl.load_workbook(p, read_only=True, data_only=True).active.iter_rows(values_only=True))
    else:
        rows = list(csv.reader(open(p, encoding="utf-8-sig")))
    if not rows: return []
    head = [str(h or "").strip().lower() for h in rows[0]]
    def col(*names):
        return next((i for i, h in enumerate(head) for n in names if n in h), None)
    ci, ti, ui, li = col("company", "firma", "employer", "arbeitgeber"), col("title", "role", "position", "job", "stelle"), \
        col("url", "link", "apply"), col("location", "ort", "city", "stadt")
    if ui is None and ti is None: raise ValueError("sheet needs a url/link or a title column; headers: %s" % head)
    out = []
    for r in rows[1:]:
        g = lambda i: str(r[i]).strip() if i is not None and i < len(r) and r[i] is not None else ""
        if not (g(ui) or g(ti)): continue
        out.append({"company": g(ci), "title": g(ti), "url": clean_url(g(ui)) if g(ui) else "", "location": g(li), "source": "import:" + p.name})
    return out


PLATFORMS = [("linkedin.com", "linkedin"), ("ashbyhq", "ashby"), ("personio", "personio"), ("greenhouse", "greenhouse"),
             ("lever.co", "lever"), ("workable", "workable"), ("smartrecruiters", "smartrecruiters"), ("join.com", "join"),
             ("arbeitnow", "arbeitnow"), ("myworkdayjobs", "workday"), ("successfactors", "successfactors"),
             ("sapsf", "successfactors"), ("arbeitsagentur", "arbeitsagentur"), ("stepstone", "stepstone"), ("indeed", "indeed")]
NEEDS_ACCOUNT = {"workday", "successfactors", "join", "linkedin"}   # the user does these himself


def platform(url):
    return next((name for k, name in PLATFORMS if k in (url or "")), "company-site")


def read_document(p):
    """Text of a CV / LinkedIn export: PDF, DOCX, TXT/MD. For onboarding (the agent reads it and fills the profile)."""
    p = Path(p).expanduser()
    suf = p.suffix.lower()
    if suf == ".pdf":
        import fitz
        return "\n".join(pg.get_text(sort=True) for pg in fitz.open(p))
    if suf == ".docx":
        import zipfile
        xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        return htmlmod.unescape(re.sub(r"<[^>]+>", "", xml))
    return p.read_text(encoding="utf-8", errors="ignore")
