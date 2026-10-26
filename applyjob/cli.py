"""applyjob command line. Every stage is one command; every command reads/writes the ledger.

  init                                   create the private workspace
  read-cv <file.pdf|.docx|.txt>          text of a CV / LinkedIn export -> workspace/inbox/<name>.txt (onboarding)
  profile new | profile | profile questions [--level core|apply|linkedin|email|optional]
                                         empty profile with every field · completeness per level · what to ask
  gate <stage>                           OK if the checklist items that stage needs are answered (search, tailor, queue, gaps, ...)
  search ba "<what>" [--where City]      Germany's federal job board (official API)
  search board <platform> <token>        one company's board: greenhouse|lever|ashby|personio|smartrecruiters
  import <file.xlsx|file.csv|file.txt>   a sheet, or any text with job links (e.g. LinkedIn job-alert mails)
  import-history <tracker.xlsx>          past applications -> SKIP "history", so they are never suggested again
  triage [--workers 12] [--limit N] [--redo]   fetch every FOUND advert -> GOOD / CHECK / REMOVED / CLOSED
  batch <label>                          new batch folder batches/<date>_<label>
  tailor <batch> [--limit N] [--ids ..]  GOOD jobs -> spec drafts (agent writes the TODO parts)
  render <batch> [refs..]                specs -> cv.pdf + letter.pdf
  audit <batch> [refs..]                 atomic findings -> AUDITED / AUDIT_FAIL + _apply/findings.xlsx
  queue <batch> [--groups N]             fill-agent groups (_apply/group_XX.json)
  record <ref> <STATUS> "<note>" [--evidence "page: ..."]
  approve-batch <batch>                  ONE line naming every open job: the user approves the whole batch BEFORE filling
  approve-line <batch> | approve <batch> "<pasted line>" | approved <batch>
  record <id> SUBMITTED needs --evidence "page:/mail: ..." and the user's approval (--manual: he submitted it himself)
  show <ref>                             one job: fields, notes, events, advert text
  edit <ref> [--company X] [--title X] [--url X] [--location X]
  status [batch] | tracker | gaps <linkedin_profile.txt>
  claim <area> | release <area> | claims  (set APPLYJOB_CHAT=<chat-name>)
  doctor                                 health check of workspace, profile, ledger, claims
"""
import argparse, concurrent.futures as cf, json, os, re, sys
from pathlib import Path
from . import applying, audit as A, checklist as C, ledger, profile as P, render as R, report, sources, tailor, triage, workspace


def die(msg):
    print(msg, file=sys.stderr); sys.exit(1)


def need_profile(stage):
    """Load the profile and refuse to run a stage until the checklist items it needs are answered."""
    p = workspace.path("profile", "profile.json")
    if not p.exists(): die("no profile yet: run `applyjob profile new`, then follow playbooks/00_onboarding.md")
    prof = P.load(p)
    levels = C.STAGE_NEEDS.get(stage, ("core",))
    errs = P.check(prof, levels)
    if errs:
        die("BLOCKED: '%s' needs these answers first. Ask the user, in one message:\n%s%s" % (
            stage, C.questions(prof, levels), ("\nshape problems:\n - " + "\n - ".join(P.structure(prof))) if P.structure(prof) else ""))
    return prof


def add_many(db, items):
    new = 0
    for it in items:
        _, created = ledger.add(db, it.get("company", ""), it.get("title", "") or it.get("url", ""), it.get("url", ""),
                                it.get("location", ""), it.get("source", ""))
        new += created
    print("%d found, %d new, %d already known" % (len(items), new, len(items) - new))


def cmd_triage(db, prof, workers, limit, redo=False):
    todo = ledger.jobs(db, ["FOUND", "GOOD", "CHECK", "REMOVED"] if redo else "FOUND")[:limit or None]
    def work(j):
        if redo and j["description"]:
            return j, "LIVE", j["description"]      # re-judge from the stored advert, no refetch
        if sources.platform(j["url"]) == "linkedin":
            return j, "UNKNOWN", ""     # LinkedIn pages are read by the agent in the user's own browser, not fetched
        st, text = sources.fetch(j["url"]) if j["url"] else ("UNKNOWN", "")
        return j, st, text
    n = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        for j, st, text in ex.map(work, todo):
            verdict, why = triage.judge(dict(j), prof, st, text)
            if sources.platform(j["url"]) == "linkedin":
                verdict, why = "CHECK", ["LinkedIn link: open it in the user's browser, read it, find the employer's own apply link"]
            note = "; ".join(why) or "fits"
            ledger.set_status(db, j["id"], verdict, note, actor="triage", description=text)
            n[verdict] = n.get(verdict, 0) + 1
    print("triaged %d: %s" % (len(todo), n))


def cmd_tailor(db, prof, batch, limit, ids):
    B = applying.batch_dir(batch)
    js = [j for j in ledger.jobs(db, "GOOD") if not j["batch"]]
    if ids: js = [j for j in js if str(j["id"]) in ids]
    for j in js[:limit or None]:
        folder = workspace.slug("%s_%s" % (j["company"], re.sub(r"\(.*?\)", "", j["title"])))
        D = B / folder; D.mkdir(exist_ok=True)
        spec = tailor.draft(dict(j), prof, j["description"] or "", j["id"])
        (D / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
        ledger.set_status(db, j["id"], "DRAFTED", "spec drafted: write the TODO parts", actor="tailor", batch=batch, folder=folder)
        print("drafted %4d %s" % (j["id"], folder))


def targets(db, batch, refs, statuses):
    js = [ledger.resolve(db, r) for r in refs] if refs else ledger.jobs(db, statuses, batch)
    return [j for j in js if j["batch"] == batch]


def cmd_render(db, prof, batch, refs):
    B = applying.batch_dir(batch); ok = bad = 0
    for j in targets(db, batch, refs, ["DRAFTED", "AUDIT_FAIL", "AUDITED"]):
        spec = json.loads((B / j["folder"] / "spec.json").read_text())
        try:
            r = R.render(spec, prof, B / j["folder"]); ok += 1
            print("rendered %4d %-45s cv %dp, letter %dp" % (j["id"], j["folder"][:45], r["cv_pages"], r["letter_pages"]))
        except ValueError as e:
            bad += 1; print("skipped  %4d %-45s %s" % (j["id"], j["folder"][:45], e))
    print("rendered %d, skipped %d" % (ok, bad))


def cmd_audit(db, prof, batch, refs):
    B = applying.batch_dir(batch); tot = {"pass": 0, "fail": 0}
    for j in targets(db, batch, refs, ["DRAFTED", "AUDIT_FAIL", "AUDITED"]):
        D = B / j["folder"]; spec = json.loads((D / "spec.json").read_text())
        f = A.audit(D, spec, prof)
        (D / "audit.json").write_text(json.dumps(f, ensure_ascii=False, indent=1))
        ok = A.passed(f); tot["pass" if ok else "fail"] += 1
        sev = {s: sum(1 for x in f if x["severity"] == s) for s in ("BLOCKER", "MAJOR", "MINOR")}
        ledger.set_status(db, j["id"], "AUDITED" if ok else "AUDIT_FAIL",
                          "" if ok else "%(BLOCKER)d blocker, %(MAJOR)d major, %(MINOR)d minor" % sev, actor="audit")
        print("%-5s %4d %-40s %s" % ("PASS" if ok else "FAIL", j["id"], j["folder"][:40], " ".join("%s=%d" % kv for kv in sev.items() if kv[1])))
        for x in f:
            if x["severity"] != "MINOR" or not ok:
                print("        %s %-7s %-16s %s | %s -> %s" % (x["id"], x["severity"], x["where"], x["rule"], x["evidence"][:70], x["fix"]))
    out, n = report.findings_sheet(B)
    print("audit: %(pass)d pass, %(fail)d fail" % tot, "| findings sheet:", out, n)


def main(argv=None):
    try:
        _main(argv)
    except (ledger.EvidenceError, ValueError, KeyError) as e:
        die("REFUSED: %s" % (e.args[0] if e.args else e))


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="applyjob", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd"); ap.add_argument("args", nargs="*")
    ap.add_argument("--where", default=""); ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--groups", type=int, default=0)
    ap.add_argument("--redo", action="store_true"); ap.add_argument("--manual", action="store_true"); ap.add_argument("--level", default=""); ap.add_argument("--ids", nargs="*", default=[]); ap.add_argument("--evidence", default="")
    ap.add_argument("--owner", default=os.environ.get("APPLYJOB_CHAT", ""))
    for f in ("company", "title", "url", "location"): ap.add_argument("--" + f, default="")
    a = ap.parse_args(argv)
    c, x = a.cmd, a.args
    if c == "init":
        print("workspace:", workspace.init()); return
    if c == "read-cv":
        workspace.init()
        text = sources.read_document(x[0])
        out = workspace.path("inbox", Path(x[0]).stem + ".txt"); out.write_text(text)
        print("%d characters -> %s" % (len(text), out)); return
    if c == "claims":
        for cl in workspace.claims(): print("%(area)s  held by %(owner)s since %(since)s" % cl)
        return
    if c in ("claim", "release"):
        if not a.owner: die("set APPLYJOB_CHAT=<your chat name> (or --owner)")
        if c == "claim":
            ok, held = workspace.claim(x[0], a.owner)
            if not ok: die("BUSY: %s is held by %s since %s. Work elsewhere or wait." % (x[0], held["owner"], held.get("since")))
            print("claimed", x[0])
        else:
            print("released" if workspace.release(x[0], a.owner) else "not yours / not claimed")
        return
    db = ledger.connect()
    if c == "profile":
        pp = workspace.path("profile", "profile.json")
        if x and x[0] == "new":
            if pp.exists(): die("a profile exists already: %s" % pp)
            workspace.init(); pp.write_text(json.dumps(C.skeleton(), ensure_ascii=False, indent=1))
            print("empty profile with every checklist field ->", pp); return
        if not pp.exists(): die("no profile yet: run `applyjob profile new`")
        prof = P.load(pp)
        if x and x[0] == "questions":
            lv = [a.level] if a.level else ["core", "apply", "linkedin", "email", "optional"]
            print(C.questions(prof, lv) or "nothing missing"); return
        for lv, (n, tot) in C.report(prof).items():
            print("%-9s %3d/%-3d %s" % (lv, n, tot, "complete" if n == tot else ("(blocks nothing)" if lv == "optional" else "INCOMPLETE")))
        s = P.structure(prof)
        if s: print("shape problems:\n - " + "\n - ".join(s))
        print("profile OK" if not P.check(prof, ("core",)) else "profile incomplete (core)")
        return
    if c == "gate":
        prof = need_profile(x[0]); print("OK: '%s' may run" % x[0]); return
    if c == "doctor":
        print("workspace:", workspace.home())
        p = workspace.path("profile", "profile.json")
        print("profile:", "missing" if not p.exists() else ("OK" if not P.check(P.load(p)) else "incomplete (run: applyjob profile)"))
        if p.exists() and workspace.path(".onboarding").exists() and not P.check(P.load(p)):
            print("note: profile complete but still unlocked; after the user confirmed it: rm workspace/.onboarding")
        print("ledger:", ledger.counts(db) or "empty")
        print("claims:", workspace.claims() or "none")
        return
    if c == "status":
        print(report.summary(db, x[0] if x else None)); return
    if c == "tracker":
        out, n = report.tracker(db); print("wrote %s (%d rows)" % (out, n)); return
    if c == "record":
        j = ledger.resolve(db, x[0])
        if x[1].upper() == "SUBMITTED" and not a.manual and not ledger.is_approved(db, j["id"]):
            die("REFUSED: job %d is not in the user's approval line (use --manual only if the USER submitted it)" % j["id"])
        ledger.set_status(db, j["id"], x[1], x[2] if len(x) > 2 else "", a.evidence, actor=a.owner or "agent")
        print("%s %d %s" % (x[1].upper(), j["id"], j["company"])); return
    if c == "show":
        j = ledger.resolve(db, x[0])
        for k in ("id", "company", "title", "url", "location", "status", "note", "batch", "folder", "source"): print("%-9s %s" % (k, j[k]))
        for ev in db.execute("SELECT * FROM events WHERE job_id=? ORDER BY id", (j["id"],)):
            print("  %s %-10s %s %s" % (ev["ts"][:16], ev["status"], ev["note"][:80], ev["evidence"][:80]))
        print("\n" + (j["description"] or "(no advert text)")[:6000]); return
    if c == "edit":
        j = ledger.resolve(db, x[0])
        ledger.edit(db, j["id"], a.owner or "agent", company=a.company, title=a.title, url=a.url, location=a.location)
        print("edited", j["id"]); return
    if c in ("approve-line", "approve-batch"):
        line = applying.approve_line(db, x[0], before_filling=(c == "approve-batch"))
        print(line or "no READY jobs"); return
    if c == "approve":
        need_profile("approve")
        done, refused = applying.approve(db, x[0], " ".join(x[1:]))
        print("APPROVED %d: %s" % (len(done), done) + (("\nrefused (not READY in this batch): " + ", ".join(refused)) if refused else "")); return
    if c == "approved":
        for j in applying.approved(db, x[0]): print("%d\t%s\t%s\t%s" % (j["id"], j["company"], j["title"], j["url"]))
        return
    prof = need_profile(c)
    if c == "search":
        if x[0] == "ba": add_many(db, sources.search_arbeitsagentur(x[1], a.where))
        elif x[0] == "board": add_many(db, sources.search_board(x[1], x[2]))
        else: die("search ba|board")
    elif c == "import":
        p = Path(x[0]).expanduser()
        items = sources.import_sheet(p) if p.suffix.lower() in (".xlsx", ".xlsm", ".csv") else sources.import_text(p.read_text())
        add_many(db, items)
    elif c == "import-history":
        items = sources.import_sheet(Path(x[0]).expanduser()); n = 0
        for it in items:
            if not (it["company"] and it["title"]): continue
            i, created = ledger.add(db, it["company"], it["title"], it.get("url", ""), it.get("location", ""), "history")
            if created: ledger.set_status(db, i, "SKIP", "history: applied before (%s)" % Path(x[0]).name, actor="history"); n += 1
        print("history: %d rows, %d new SKIP entries" % (len(items), n))
    elif c == "triage": cmd_triage(db, prof, a.workers, a.limit, a.redo)
    elif c == "batch":
        B = workspace.path("batches", "%s_%s" % (workspace.today(), workspace.slug(x[0]).lower().replace("_", "-")))
        B.mkdir(parents=True, exist_ok=False); (B / "_apply").mkdir(); print(B.name)
    elif c == "tailor": cmd_tailor(db, prof, x[0], a.limit, a.ids)
    elif c == "render": cmd_render(db, prof, x[0], x[1:])
    elif c == "audit": cmd_audit(db, prof, x[0], x[1:])
    elif c == "queue":
        q, files = applying.queue(db, x[0], a.groups)
        print("%d jobs in %d groups:" % (len(q), len(files))); [print("  ", f) for f in files]
        acc = [i for i in q if i["needs_account"]]
        if acc: print("needs the user's own account (agent marks LOGIN): %d" % len(acc))
    elif c == "gaps":
        rows = report.linkedin_gaps(db, prof, Path(x[0]).expanduser().read_text())
        for r in rows: print("%-28s %3d adverts  linkedin:%-3s profile:%s" % (r["term"], r["adverts"], "yes" if r["on_linkedin"] else "NO", "yes" if r["in_profile"] else "no"))
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
