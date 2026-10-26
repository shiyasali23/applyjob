"""Company job boards: read thousands of public ATS feeds in parallel and keep the jobs located in Germany.

data/germany/boards.csv.gz lists 24,443 boards (kind, token, domain, company). They come from the Common Crawl
index and from links on German company websites. Many companies are international, so every job is filtered by
its own location: only Germany (or remote) passes. Supported feeds (public JSON/XML, no login, no scraping):
personio · greenhouse · lever · ashby · smartrecruiters · recruitee · teamtailor · workable.
Workday, softgarden, JOIN and d.vinci boards are listed but not read (they need page scraping or an account).
"""
import concurrent.futures as cf, csv, gzip, json, re, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
from . import sources

DATA = Path(__file__).resolve().parents[1] / "data" / "germany" / "boards.csv.gz"
SUPPORTED = ("personio", "greenhouse", "lever", "ashby", "smartrecruiters", "recruitee", "teamtailor", "workable")

GERMAN_PLACES = """deutschland germany berlin hamburg münchen munich muenchen köln koeln cologne frankfurt stuttgart düsseldorf
duesseldorf dortmund essen leipzig bremen dresden hannover hanover nürnberg nuremberg duisburg bochum wuppertal bielefeld
bonn münster mannheim karlsruhe augsburg wiesbaden mönchengladbach gelsenkirchen aachen braunschweig kiel chemnitz halle
magdeburg freiburg krefeld mainz lübeck erfurt oberhausen rostock kassel hagen potsdam saarbrücken hamm ludwigshafen
oldenburg osnabrück leverkusen heidelberg darmstadt solingen regensburg paderborn ingolstadt würzburg wolfsburg ulm
heilbronn pforzheim göttingen bottrop reutlingen koblenz bremerhaven erlangen trier jena siegen hildesheim cottbus
gütersloh walldorf garching ottobrunn unterföhring eschborn neuss ratingen sindelfingen böblingen herzogenaurach""".split()
GERMANY_RE = re.compile(r"(?<![a-zäöüß])(" + "|".join(map(re.escape, GERMAN_PLACES)) + r")(?![a-zäöüß])|\bDE\b|, ?DE$", re.I)
REMOTE_RE = re.compile(r"\b(remote|anywhere|homeoffice|home office)\b", re.I)


def in_germany(location, remote_ok=True):
    loc = location or ""
    return bool(GERMANY_RE.search(loc)) or (remote_ok and bool(REMOTE_RE.search(loc)) and not re.search(
        r"\b(us|usa|united states|canada|india|uk|united kingdom|singapore|brazil|australia)\b", loc, re.I))


def load(kinds=SUPPORTED):
    with gzip.open(DATA, "rt", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["kind"] in kinds]


def _json(url):
    s, b = sources.get(url, {"Accept": "application/json"})
    return json.loads(b) if s == 200 and b else None


def pretty(tok):
    return re.sub(r"[-_]+", " ", tok).strip().title()


def read(kind, tok):
    """One board -> [{company, title, url, location, description}] (empty on any error)."""
    try:
        if kind == "personio":
            for tld in ("de", "com"):
                s, b = sources.get("https://%s.jobs.personio.%s/xml" % (tok, tld))
                if s == 200 and b: break
            else:
                return []
            out = []
            for p in ET.fromstring(b).findall("position"):
                jid, title = p.findtext("id"), (p.findtext("name") or "").strip()
                if not (jid and title): continue
                desc = "\n".join("%s\n%s" % (d.findtext("name") or "", sources.text_of(d.findtext("value") or ""))
                                 for d in p.findall("jobDescriptions/jobDescription"))
                out.append({"company": (p.findtext("subcompany") or "").strip() or pretty(tok), "title": title,
                            "url": "https://%s.jobs.personio.%s/job/%s" % (tok, tld, jid),
                            "location": (p.findtext("office") or "").strip(), "description": desc})
            return out
        if kind == "greenhouse":
            j = _json("https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=true" % tok) or {}
            return [{"company": x.get("company_name") or pretty(tok), "title": x.get("title") or "", "url": x.get("absolute_url") or "",
                     "location": (x.get("location") or {}).get("name", ""), "description": sources.text_of(sources.htmlmod.unescape(x.get("content") or ""))}
                    for x in j.get("jobs") or []]
        if kind == "lever":
            j = _json("https://api.lever.co/v0/postings/%s?mode=json" % tok)
            if j is None: j = _json("https://api.eu.lever.co/v0/postings/%s?mode=json" % tok)
            return [{"company": pretty(tok), "title": x.get("text") or "", "url": x.get("hostedUrl") or "",
                     "location": ", ".join((x.get("categories") or {}).get("allLocations") or []) or (x.get("categories") or {}).get("location", ""),
                     "description": x.get("descriptionPlain") or ""} for x in j or []]
        if kind == "ashby":
            j = _json("https://api.ashbyhq.com/posting-api/job-board/%s" % tok) or {}
            out = []
            for x in j.get("jobs") or []:
                if x.get("isListed") is False: continue
                locs = [x.get("location") or ""] + [s.get("location", "") for s in x.get("secondaryLocations") or []]
                country = ((x.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or ""
                out.append({"company": pretty(tok), "title": x.get("title") or "", "url": x.get("jobUrl") or "",
                            "location": ", ".join([l for l in locs if l] + ([country] if country else [])),
                            "description": x.get("descriptionPlain") or ""})
            return out
        if kind == "smartrecruiters":
            j = _json("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100" % tok) or {}
            return [{"company": (x.get("company") or {}).get("name") or pretty(tok), "title": x.get("name") or "",
                     "url": "https://jobs.smartrecruiters.com/%s/%s" % (tok, x.get("id")),
                     "location": (x.get("location") or {}).get("fullLocation", ""), "description": ""} for x in j.get("content") or []]
        if kind == "recruitee":
            j = _json("https://%s.recruitee.com/api/offers/" % tok) or {}
            return [{"company": x.get("company_name") or pretty(tok), "title": x.get("title") or "",
                     "url": x.get("careers_url") or "", "location": x.get("location") or ", ".join(filter(None, [x.get("city"), x.get("country")])),
                     "description": sources.text_of((x.get("description") or "") + "\n" + (x.get("requirements") or ""))}
                    for x in j.get("offers") or [] if (x.get("status") or "published") == "published"]
        if kind == "teamtailor":
            j = _json("https://%s.teamtailor.com/jobs.json" % tok) or {}
            out = []
            for x in j.get("items") or []:
                jp = x.get("_jobposting") or {}
                loc = jp.get("jobLocation"); loc = loc[0] if isinstance(loc, list) and loc else loc
                addr = (loc or {}).get("address") or {} if isinstance(loc, dict) else {}
                out.append({"company": j.get("title") or pretty(tok), "title": x.get("title") or "", "url": x.get("url") or "",
                            "location": ", ".join(filter(None, [addr.get("addressLocality"), addr.get("addressCountry")])),
                            "description": sources.text_of(x.get("content_html") or "")})
            return out
        if kind == "workable":
            j = _json("https://apply.workable.com/api/v1/widget/accounts/%s?details=true" % tok) or {}
            return [{"company": j.get("name") or pretty(tok), "title": x.get("title") or "", "url": x.get("url") or x.get("shortlink") or "",
                     "location": ", ".join(filter(None, [x.get("city"), x.get("country")])), "description": sources.text_of(x.get("description") or "")}
                    for x in j.get("jobs") or []]
    except Exception:
        return []
    return []


def scan(want_title, kinds=SUPPORTED, workers=24, limit=0, remote_ok=True, progress=None):
    """Read every board in parallel. Keep jobs whose title passes want_title() and whose location is in Germany."""
    boards = load(kinds)
    if limit: boards = boards[:limit]
    found, done = [], 0
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(read, b["kind"], b["token"]): b for b in boards}
        for fu in cf.as_completed(futs):
            b = futs[fu]; done += 1
            for job in fu.result():
                if job["title"] and job["url"] and want_title(job["title"]) and in_germany(job["location"], remote_ok):
                    job["source"] = "board:%s" % b["kind"]; found.append(job)
            if progress and done % 500 == 0: progress(done, len(boards), len(found))
    return boards, found
