"""Spec -> cv.pdf + letter.pdf (text PDFs, A4) with PyMuPDF's HTML engine. Style: templates/style.css.

Rendering is dumb on purpose: it prints the spec and the profile facts, nothing else. All judgement lives in the
spec (written by the agent) and all checking lives in audit.py.
"""
import datetime, html, os, re
from pathlib import Path
import fitz
from . import profile as P, workspace
from .tailor import has_todo

CSS = Path(__file__).resolve().parents[1] / "templates" / "style.css"
H = {"de": {"summary": "Profil", "skills": "Kenntnisse", "experience": "Berufserfahrung", "education": "Ausbildung",
            "certs": "Zertifikate", "languages": "Sprachen", "soft": "Persönliche Stärken", "present": "heute",
            "permit": "Arbeitserlaubnis"},
     "en": {"summary": "Profile", "skills": "Skills", "experience": "Experience", "education": "Education",
            "certs": "Certifications", "languages": "Languages", "soft": "Strengths", "present": "present",
            "permit": "Work permit"}}
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
e = lambda s: html.escape(str(s or ""))


def fmt_date(d, lang):
    return d.strftime("%d.%m.%Y") if lang == "de" else "%d %s %d" % (d.day, MONTHS_EN[d.month - 1], d.year)


# PDF base-14 fonts get "fl"/"fi" ligatures when shaped (text "Airﬂow": an ATS misses the keyword), and some TTFs
# extract spaces as U+00A0. So a real TTF is embedded, chosen by a self-test, and subset to keep files small.
FONT_CANDIDATES = [  # (regular, bold); first one that passes the self-test wins. Override in profile.preferences.font
    ("/System/Library/Fonts/Supplemental/Trebuchet MS.ttf", "/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("C:/Windows/Fonts/trebuc.ttf", "C:/Windows/Fonts/trebucbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Georgia.ttf", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"),
]
CLEAN_SAMPLE = "Airflow first fluent office scikit-learn e-mail Data Engineer C++ C# Grüße"
_FONT = {}


def _font_css(reg, bold):
    return ("@font-face {font-family: JP; src: url('%s');} @font-face {font-family: JP; font-weight: bold; src: url('%s');}"
            " * {font-family: JP;}" % (Path(reg).name, Path(bold).name))


def _clean(reg, bold):
    import tempfile
    try:
        st = fitz.Story(html="<p>%s <b>%s</b></p>" % (CLEAN_SAMPLE, CLEAN_SAMPLE), user_css=_font_css(reg, bold), archive=fitz.Archive(str(Path(reg).parent)))
        f = tempfile.mktemp(suffix=".pdf"); w = fitz.DocumentWriter(f); box = fitz.paper_rect("a4")
        d = w.begin_page(box); st.place(box + (40, 40, -40, -40)); st.draw(d); w.end_page(); w.close()
        doc = fitz.open(f); clean_tounicode(doc); txt = doc[0].get_text(); doc.close(); os.remove(f)
        if re.search("[\ufb00-\ufb06\u00a0]", txt): return False          # ligatures / no-break spaces
        return " ".join(txt.split()).count(CLEAN_SAMPLE) == 2
    except Exception:
        return False


def pick_font(prof=None):
    """(regular, bold) TTF paths that extract as clean text, or None (then base-14 + an audit BLOCKER)."""
    want = (prof or {}).get("preferences", {}).get("font")
    if "f" in _FONT and not want: return _FONT["f"]
    cands = ([tuple(want)] if want else []) + FONT_CANDIDATES
    for reg, bold in cands:
        if os.path.exists(reg) and os.path.exists(bold) and Path(reg).parent == Path(bold).parent and _clean(reg, bold):
            _FONT["f"] = (reg, bold); return _FONT["f"]
    _FONT["f"] = None
    return None


PHOTO_PT = 70


def _pdf(html_text, out, archive_dir, font=None, photo=None):
    css = CSS.read_text() if CSS.exists() else ""
    if font:
        story = fitz.Story(html=html_text, user_css=css + "\n" + _font_css(*font), archive=_archive(archive_dir, Path(font[0]).parent))
    else:
        story = fitz.Story(html=html_text, user_css=css, archive=_archive(archive_dir))
    tmp = str(out) + ".tmp"
    writer = fitz.DocumentWriter(tmp)
    box = fitz.paper_rect("a4"); where = box + (46, 40, -46, -40)
    more, pages = 1, 0
    while more:
        dev = writer.begin_page(box)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page(); pages += 1
        if pages > 6: break
    writer.close()
    doc = fitz.open(tmp)
    if photo and Path(photo).exists():
        r = doc[0].rect
        doc[0].insert_image(fitz.Rect(r.width - 46 - PHOTO_PT, 40, r.width - 46, 40 + PHOTO_PT), filename=str(photo))
    try: doc.subset_fonts()
    except Exception: pass
    clean_tounicode(doc)
    doc.save(str(out), garbage=4, deflate=True); doc.close(); os.remove(tmp)
    return pages


# Fonts map some glyphs to look-alike code points (U+00A0 space, U+00AD/U+2010 hyphen, U+FB01 "fi"). An ATS then
# reads "scikit\u2010learn" and misses the keyword. Rewrite the single-glyph entries of each ToUnicode map to ASCII.
TOUNICODE_FIX = {"00A0": "0020", "00AD": "002D", "2010": "002D", "2011": "002D", "FB00": "00660066", "FB01": "00660069",
                 "FB02": "0066006C", "FB03": "006600660069", "FB04": "00660066006C"}


def clean_tounicode(doc):
    n = 0
    for x in range(1, doc.xref_length()):
        try: s = doc.xref_stream(x)
        except Exception: continue
        if not s or b"begincmap" not in s: continue
        t = s.decode("latin-1")
        def fix_block(m):
            b = m.group(0)
            for a, r in TOUNICODE_FIX.items():
                b = re.sub(r"(<[0-9A-Fa-f]+>\s*)<%s>" % a, lambda k: k.group(1) + "<%s>" % r, b, flags=re.I)
            return b
        t2 = re.sub(r"beginbfchar.*?endbfchar", fix_block, t, flags=re.S)
        if t2 != t: doc.update_stream(x, t2.encode("latin-1")); n += 1
    return n


def _archive(*dirs):
    a = fitz.Archive()
    for d in dirs:
        if Path(d).is_dir(): a.add(str(d))
    return a


def photo_path(prof):
    """workspace/profile/photo.jpg, only if the user said yes to a photo (checklist: documents.photo)."""
    want = (prof.get("documents") or {}).get("photo")
    p = workspace.path("profile", "photo.jpg")
    return p if want is True and p.exists() else Path("/nonexistent")


def cv_html(spec, prof):
    p, lang = prof["person"], spec.get("language", "en"); h = H[lang]
    photo = photo_path(prof)
    contact = " · ".join(e(x) for x in (p.get("city"), p.get("phone"), p.get("email"),
                                         (p.get("linkedin") or "").replace("https://", "").replace("www.", ""),
                                         (p.get("github") or "").replace("https://", "")) if x)
    # the HTML engine has no float and ignores table widths: the header keeps a right margin and render() stamps
    # the photo into that corner afterwards
    out = ['<div class="head%s"><h1>%s</h1><p class="headline">%s</p><p class="contact">%s</p>' % (
        " withphoto" if photo.exists() else "", e(P.full_name(prof)), e(spec["headline"]), contact)]
    if p.get("work_permit"): out.append('<p class="contact">%s: %s</p>' % (h["permit"], e(p["work_permit"])))
    out.append("</div>")
    out.append('<h2>%s</h2><p>%s</p>' % (h["summary"], e(spec["summary"])))
    out.append('<h2>%s</h2><table class="skills">' % h["skills"])
    for g, items in spec["skills"].items():
        if items: out.append("<tr><td class='k'>%s</td><td>%s</td></tr>" % (e(g), e(", ".join(items))))
    out.append("</table><h2>%s</h2>" % h["experience"])
    for x in spec["experience"]:
        src = P.experience(prof, x["id"])
        if not src: continue
        out.append('<p class="role"><b>%s</b>, %s<span class="when"> %s – %s · %s</span></p><ul>' % (
            e(src["title"]), e(src["company"]), e(src["start"]), e(src.get("end") or h["present"]), e(src.get("location", ""))))
        out += ["<li>%s</li>" % e(b) for b in x["bullets"]]
        out.append("</ul>")
    out.append("<h2>%s</h2>" % h["education"])
    for ed in prof.get("education", []):
        out.append('<p class="role"><b>%s</b>, %s<span class="when"> %s – %s</span></p>' % (
            e(ed["degree"]), e(ed["school"]), e(ed.get("start", "")), e(ed.get("end", ""))))
        if ed.get("detail"): out.append("<p>%s</p>" % e(ed["detail"]))
    if prof.get("certifications"):
        out.append("<h2>%s</h2><ul>%s</ul>" % (h["certs"], "".join("<li>%s</li>" % e(c) for c in prof["certifications"])))
    out.append("<h2>%s</h2><p>%s</p>" % (h["languages"], e(" · ".join("%s: %s" % (l["name"], l["level"]) for l in prof["languages"]))))
    if spec.get("soft_skills"):
        out.append("<h2>%s</h2><ul>%s</ul>" % (h["soft"], "".join("<li><b>%s</b>: %s</li>" % (e(t), e(d)) for t, d in spec["soft_skills"])))
    return "".join(out)


def letter_html(spec, prof, date=None):
    p, L, lang = prof["person"], spec["letter"], spec.get("language", "en")
    date = date or datetime.date.today()
    sender = "<br/>".join(e(x) for x in (P.full_name(prof), " ".join(filter(None, [p.get("street")])), " ".join(filter(None, [p.get("postcode"), p.get("city")])),
                                         p.get("phone"), p.get("email")) if x)
    to = "<br/>".join(e(x) for x in L["to"] if x)
    body = "".join("<p>%s</p>" % e(x) for x in L["paragraphs"])
    return ('<div class="letter"><p class="sender">%s</p><p class="to">%s</p><p class="date">%s, %s</p><p class="subject"><b>%s</b></p>'
            '<p>%s</p>%s<p class="closing">%s</p><p>%s</p></div>') % (sender, to, e(p.get("city")), fmt_date(date, lang), e(L["subject"]),
                                               e(L["salutation"]), body, e(L["closing"]), e(P.full_name(prof)))


def render(spec, prof, out_dir, date=None):
    """Write cv.pdf and letter.pdf into out_dir. Returns {cv_pages, letter_pages}."""
    if has_todo(spec): raise ValueError("spec still has TODO fields: finish the writing first")
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    arch = workspace.path("profile"); arch.mkdir(parents=True, exist_ok=True)
    font = pick_font(prof)
    cvp = _pdf(cv_html(spec, prof), out_dir / "cv.pdf", arch, font, photo_path(prof))
    lp = _pdf(letter_html(spec, prof, date), out_dir / "letter.pdf", arch, font)
    return {"cv_pages": cvp, "letter_pages": lp}
