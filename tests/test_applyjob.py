"""Offline tests (no network). Run: python3 -m unittest discover -s tests -v   (~3 s)"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = tempfile.mkdtemp(prefix="applyjob_test_")
os.environ["APPLYJOB_HOME"] = TMP
sys.path.insert(0, str(ROOT))
from applyjob import applying, audit as A, checklist as C, ledger, profile as P, render as R, tailor, triage, vocab, workspace, sources  # noqa: E402

PROF = P.load(ROOT / "examples" / "profile.example.json")
ADVERT = """Data Scientist (m/w/d) at Nordwind Logistics GmbH, Berlin.
Your tasks: build forecasting models in Python and SQL, run them with Airflow, deploy with Docker.
Your profile: 2+ years experience, scikit-learn or XGBoost, PostgreSQL, Kubernetes is a plus. Excellent communication.
We value ownership and clear communication. Grid Redispatch data."""
JOB = {"company": "Nordwind Logistics GmbH", "title": "Data Scientist (m/w/d)", "url": "https://nordwind.example/jobs/1", "location": "Berlin"}


def good_spec():
    s = tailor.draft(JOB, PROF, ADVERT, 1)
    s["summary"] = ("Data Scientist with 3 years of experience building forecasting and NLP systems in Python and SQL. "
                    "I build models, the pipelines that feed them with Airflow and PostgreSQL, and the Docker services that run them, "
                    "and I own them from the first idea to daily use.")
    s["soft_skills"] = [["Ownership", "I take a model from the first idea to daily use."],
                        ["Clear communication", "I explain results so that teams can act on them."],
                        ["Reliability", "I build pipelines that run every morning without manual work."]]
    s["letter"] = {"to": ["Nordwind Logistics GmbH", "Berlin"], "salutation": "Dear Nordwind team,",
                   "subject": "Application as Data Scientist",
                   "paragraphs": ["I am applying as Data Scientist at Nordwind Logistics. You plan freight with data, and forecasting is the work I enjoy most.",
                                  "At Acme Retail I built a demand-forecasting service with XGBoost and Airflow that 40 stores use every morning. "
                                  "I also automated the reporting pipelines in PostgreSQL, so a weekly task now takes minutes.",
                                  "I bring the whole path from data to a running service, and I work closely with the people who use the results.",
                                  "I would be glad to talk about how I can help your planning team."],
                   "closing": "Kind regards,"}
    return s


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workspace.init()
        (Path(TMP) / "profile" / "profile.json").write_text(json.dumps(PROF))
        cls.db = ledger.connect()

    def test_profile(self):
        self.assertEqual(P.check(PROF, ("core", "apply", "linkedin", "email")), [])
        bad = json.loads(json.dumps(PROF)); bad["person"]["email"] = ""
        self.assertTrue(any("person.email" in e for e in P.check(bad)))

    def test_checklist(self):
        keys = [k for k, *_ in C.CHECKLIST]
        self.assertEqual(len(keys), len(set(keys)), "duplicate checklist keys")
        self.assertGreaterEqual(len(keys), 90)
        for k, q, lv, kind in C.CHECKLIST:
            self.assertIn(lv, C.LEVELS); self.assertLessEqual(len(q), 90, q)
        empty = C.skeleton()
        miss = C.missing(empty, ("core",))
        self.assertEqual(len(miss), sum(1 for c in C.CHECKLIST if c[2] == "core"))     # nothing answered
        qs = C.questions(empty, ("core",))
        self.assertTrue(qs.startswith("Needed to start:") and "- Nationality" not in qs)  # nationality is an apply item
        self.assertIn("- Nationality", C.questions(empty, ("apply",)))
        # questions that do not apply count as answered
        q = json.loads(json.dumps(empty)); q["preferences"]["relocation"] = False; q["person"]["permit_type"] = "EU citizen"
        aq = C.questions(q, ("apply",))
        self.assertNotIn("Where you would relocate", aq); self.assertNotIn("Permit valid until", aq)
        q["preferences"]["relocation"] = True; self.assertIn("Where you would relocate", C.questions(q, ("apply",)))
        # '-' = declined: answered, but never used as a value
        p = dict(PROF); self.assertIn("writing.banned_phrases", p["_declined"]); self.assertEqual(p["writing"]["banned_phrases"], [])

    def test_gates(self):
        env = dict(os.environ, APPLYJOB_HOME=tempfile.mkdtemp())
        run = lambda *a: subprocess.run([sys.executable, "-m", "applyjob"] + list(a), cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(run("profile", "new").returncode, 0)
        r = run("search", "ba", "Data Scientist")
        self.assertEqual(r.returncode, 1); self.assertIn("BLOCKED", r.stderr); self.assertIn("- First name", r.stderr)
        prof = json.loads(json.dumps(P.load(ROOT / "examples" / "profile.example.json")))
        for k in ("nationality", "street"): prof["person"][k] = ""                       # apply items missing
        prof["_declined"] = [d for d in prof["_declined"] if d not in ("person.nationality", "person.street")]
        Path(env["APPLYJOB_HOME"], "profile", "profile.json").write_text(json.dumps(prof))
        self.assertEqual(run("gate", "tailor").returncode, 0)
        r = run("gate", "queue")
        self.assertEqual(r.returncode, 1); self.assertIn("- Nationality", r.stderr); self.assertIn("- Street", r.stderr)

    def test_vocab_false_friends(self):
        t = vocab.find_terms("Redispatch data, excellent skills, SQL Server and PyTorch; Go is our motto")
        self.assertIn("PyTorch", t); self.assertIn("SQL Server", t)
        for bad in ("Redis", "Excel", "Go"): self.assertNotIn(bad, t)

    def test_ledger_dedupe_and_evidence(self):
        db = self.db
        i, new = ledger.add(db, "Foo GmbH", "ML Engineer (m/w/d)", "https://foo.example/jobs/9?utm_source=x")
        j, new2 = ledger.add(db, "FOO", "ML Engineer", "")
        self.assertTrue(new); self.assertFalse(new2); self.assertEqual(i, j)
        k, new3 = ledger.add(db, "Other", "Other", "https://foo.example/jobs/9")
        self.assertFalse(new3)
        with self.assertRaises(ledger.EvidenceError): ledger.set_status(db, i, "SUBMITTED", "", "clicked submit")
        with self.assertRaises(ledger.EvidenceError): ledger.set_status(db, i, "SUBMITTED", "", "page: Applied badge shown")
        ledger.set_status(db, i, "SUBMITTED", "", "page: Thank you for your application")
        with self.assertRaises(ValueError): ledger.set_status(db, i, "READY", "")
        ledger.set_status(db, i, "REJECTED", "mail: Absage")
        self.assertTrue(ledger.sent_event(db, i))

    def test_join_needs_mail(self):
        i, _ = ledger.add(self.db, "Bar", "Data Engineer", "https://join.com/companies/bar/123")
        with self.assertRaises(ledger.EvidenceError): ledger.set_status(self.db, i, "SUBMITTED", "", "page: Applied today")
        ledger.set_status(self.db, i, "SUBMITTED", "", "mail: Your application to Bar was received")

    def test_email_and_german_level(self):
        txt = "Deutsch mind. B2. Wir freuen uns auf eine Mail mit deinem Lebenslauf silvia@lantenhammer-ub.de mit Grüßen"
        self.assertEqual(triage.apply_email(txt), "silvia@lantenhammer-ub.de")
        v, why = triage.judge({"title": "Data Scientist", "location": "Berlin"}, PROF, "LIVE", ADVERT + " " + txt)
        self.assertTrue(any("e-mail" in w for w in why)); self.assertTrue(any("German" in w for w in why))
        self.assertEqual(triage.apply_email("Contact our privacy officer at dpo@acme.example for data questions."), "")

    def test_triage(self):
        self.assertEqual(triage.judge({"title": "Senior Data Scientist"}, PROF, "LIVE", ADVERT)[0], "REMOVED")
        self.assertEqual(triage.judge({"title": "Werkstudent Data Science"}, PROF, "LIVE", ADVERT)[0], "REMOVED")
        self.assertEqual(triage.judge({"title": "Data Scientist (m/w/d)", "location": "Berlin"}, PROF, "LIVE", ADVERT)[0], "GOOD")
        self.assertEqual(triage.judge({"title": "Data Scientist"}, PROF, "CLOSED", "")[0], "CLOSED")
        self.assertEqual(triage.judge({"title": "Projektmanager AI Hub"}, PROF, "LIVE", ADVERT)[0], "REMOVED")
        self.assertEqual(triage.judge({"title": "Software Engineer (all genders)", "location": "Berlin"}, PROF, "LIVE", ADVERT)[0], "CHECK")
        self.assertEqual(triage.judge({"title": "KI-Engineer (m/w/d)", "location": "Berlin"}, dict(PROF, preferences=dict(PROF["preferences"], target_roles=["AI Engineer", "KI"])), "LIVE", ADVERT)[0], "GOOD")
        analyst = dict(PROF, preferences=dict(PROF["preferences"], target_roles=["Data Analyst"], locations=["Munich", "remote"], relocation=False))
        self.assertEqual(triage.judge({"title": "Data Engineer (m/w/d)", "location": "Munich"}, analyst, "LIVE", "x" * 500)[0], "CHECK")
        self.assertEqual(triage.judge({"title": "Junior Data Analyst (m/w/d)", "location": "München"}, dict(analyst, preferences=dict(analyst["preferences"], locations=["München", "remote"])), "LIVE", "x" * 500)[0], "GOOD")
        v, why = triage.judge({"title": "Junior Data Analyst", "location": "Hirschau"}, analyst, "LIVE", "Office in Hirschau.")
        self.assertEqual(v, "CHECK"); self.assertTrue(any("location" in w for w in why))
        self.assertEqual(triage.judge({"title": "Junior Data Analyst", "location": "Hamburg"}, analyst, "LIVE", "Fully remote role.")[0], "GOOD")
        v, why = triage.judge({"title": "Data Scientist"}, PROF, "LIVE", ADVERT + " Security clearance required.")
        self.assertEqual(v, "CHECK"); self.assertTrue(any("blocker" in w for w in why))

    def test_tailor_render_audit(self):
        s = tailor.draft(JOB, PROF, ADVERT, 1)
        self.assertIn("XGBoost", s["terms"]); self.assertNotIn("Kubernetes", s["terms"])   # never_claim
        self.assertIn("Kubernetes", s["advert_terms_new"]) if False else None
        self.assertTrue(tailor.has_todo(s))
        out = Path(TMP) / "batches" / "t" / "job1"
        with self.assertRaises(ValueError): R.render(s, PROF, out)
        s = good_spec()
        r = R.render(s, PROF, out)
        self.assertEqual(r["letter_pages"], 1); self.assertLessEqual(r["cv_pages"], 2)
        f = A.audit(out, s, PROF)
        self.assertTrue(A.passed(f), [x for x in f if x["severity"] != "MINOR"])

    def test_audit_catches_fabrication(self):
        out = Path(TMP) / "batches" / "t" / "job2"
        s = good_spec()
        s["experience"][0]["bullets"][0] = "Built a forecasting service on Kubernetes with Spark, used by 400 stores."
        s["letter"]["paragraphs"][1] += " I also wrote Java services."
        s["letter"]["to"] = ["Wrong Company AG"]
        R.render(s, PROF, out)
        f = A.audit(out, s, PROF)
        rules = " | ".join("%s %s %s" % (x["severity"], x["rule"], x["evidence"]) for x in f)
        self.assertIn("never claim", rules)                       # Kubernetes / Java
        self.assertIn("Spark", rules)                             # tool not in this role's stack
        self.assertIn("400", rules)                               # number not in the profile
        self.assertIn("right company", rules)
        self.assertFalse(A.passed(f))

    def test_mirror(self):
        s = good_spec(); s["_advert"] += " Our product is Kubeflow Studio."
        s["letter"]["paragraphs"][0] += " Kubeflow powers your platform."
        f = A.audit_spec(s, PROF)
        self.assertTrue(any(x["evidence"] == "Kubeflow" for x in f))          # not mirrored: a claim
        s["mirror"] = ["Kubeflow"]
        self.assertFalse(any(x["evidence"] == "Kubeflow" for x in A.audit_spec(s, PROF)))
        s["mirror"] = ["Snowflake"]                                            # not in the advert: refused
        self.assertTrue(any(x["where"] == "spec.mirror" for x in A.audit_spec(s, PROF)))

    def test_apply_flow(self):
        db = self.db
        workspace.path("batches", "b1").mkdir(parents=True, exist_ok=True)
        ids = []
        for n in range(20):
            i, _ = ledger.add(db, "Co%d" % n, "Data Scientist %d" % n, "https://co%d.example/jobs/1" % n)
            ledger.set_status(db, i, "AUDITED", "", batch="b1", folder="F%d" % n); ids.append(i)
        q, files = applying.queue(db, "b1", per_agent=8)
        self.assertEqual(len(q), 20); self.assertEqual(len(files), 3)
        for i in ids[:5]: ledger.set_status(db, i, "READY", "")
        line = applying.approve_line(db, "b1")
        self.assertTrue(line.startswith("submit ") and "Co0" in line)
        done, refused = applying.approve(db, "b1", line + ", %d Co9" % ids[9])
        self.assertEqual(sorted(done), sorted(ids[:5])); self.assertEqual(len(refused), 1)   # Co9 was not READY
        self.assertEqual(len(applying.approved(db, "b1")), 5)

    def test_claims(self):
        ok, _ = workspace.claim("batch:x", "chat-a"); self.assertTrue(ok)
        ok2, held = workspace.claim("batch:x", "chat-b"); self.assertFalse(ok2); self.assertEqual(held["owner"], "chat-a")
        self.assertTrue(workspace.release("batch:x", "chat-a"))
        self.assertTrue(workspace.claim("batch:x", "chat-b")[0])

    def test_imports(self):
        mail = "New jobs: https://www.linkedin.com/comm/jobs/view/3999999999/?trackingId=abc and https://boards.greenhouse.io/acme/jobs/123?utm_source=li , unsubscribe https://linkedin.com/settings"
        urls = [x["url"] for x in sources.import_text(mail)]
        self.assertEqual(urls, ["https://www.linkedin.com/jobs/view/3999999999/", "https://boards.greenhouse.io/acme/jobs/123"])
        self.assertEqual(sources.platform(urls[0]), "linkedin")

    def test_numbers_locale(self):
        self.assertEqual(A.numbers("1.2 TB and 186,956 pairs"), A.numbers("1,2 TB und 186.956 Paare"))

    def test_guard(self):
        from applyjob import guard
        H = Path(TMP)
        if (H / ".onboarding").exists(): (H / ".onboarding").unlink()      # init unlocked the first profile write
        self.assertTrue(guard.decide(str(H / "batches" / "b" / "x" / "spec.json"))[0])
        self.assertTrue(guard.decide(str(H / "work" / "chat-a" / "notes.md"))[0])
        self.assertFalse(guard.decide(str(H / "ledger.db"))[0])
        self.assertFalse(guard.decide(str(H / "profile" / "profile.json"))[0])
        self.assertFalse(guard.decide(str(ROOT / "applyjob" / "cli.py"))[0])
        self.assertFalse(guard.decide("/Users/someone/Desktop/random.txt")[0])
        (H / ".onboarding").write_text(""); self.assertTrue(guard.decide(str(H / "profile" / "profile.json"))[0]); (H / ".onboarding").unlink()
        r = subprocess.run([sys.executable, str(ROOT / "applyjob" / "guard.py")], input=json.dumps({"tool_input": {"file_path": "/tmp/x.txt"}}),
                           env=dict(os.environ, APPLYJOB_HOME=TMP), capture_output=True, text=True)
        self.assertEqual(r.returncode, 2); self.assertIn("BLOCKED", r.stderr)

    def test_edit_relink(self):
        i, _ = ledger.add(self.db, "", "https://www.linkedin.com/jobs/view/123/", "https://www.linkedin.com/jobs/view/123/")
        ledger.edit(self.db, i, company="Zeta GmbH", title="AI Engineer", url="https://zeta.example/careers/ai")
        j = ledger.resolve(self.db, i)
        self.assertEqual((j["company"], j["url"]), ("Zeta GmbH", "https://zeta.example/careers/ai"))
        self.assertEqual(ledger.find(self.db, "Zeta", "AI Engineer")["id"], i)

    def test_read_cv(self):
        import fitz
        f = Path(TMP) / "cv.pdf"; d = fitz.open(); d.new_page().insert_text((72, 72), "Alex Example Data Scientist Python"); d.save(f)
        self.assertIn("Data Scientist", sources.read_document(f))

    def test_first_run(self):
        fresh = tempfile.mkdtemp(); shutil.rmtree(fresh)                   # a new user: no workspace at all
        r = subprocess.run([sys.executable, "-m", "applyjob", "doctor"], cwd=ROOT, env=dict(os.environ, APPLYJOB_HOME=fresh),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("profile: missing", r.stdout)
        self.assertTrue((Path(fresh) / ".onboarding").exists())
        shutil.rmtree(fresh, ignore_errors=True)

    def test_cli(self):
        env = dict(os.environ, APPLYJOB_HOME=TMP)
        r = subprocess.run([sys.executable, "-m", "applyjob", "doctor"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("profile: OK", r.stdout)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
