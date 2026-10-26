# jobpilot

An agent harness that runs a whole job search with an AI coding agent (Claude Code, or any agent that reads
`AGENTS.md`): learn the applicant → find jobs → triage → write a tailored CV + cover letter per job → audit every
document atomically and fix → fill ~100 application forms in parallel in your own browser → you approve them in one
message → submit → prove every send → follow up. It also tunes your LinkedIn profile to the jobs you target.

**Honest by construction.** Every fact comes from one profile file. The audit blocks invented numbers, tools a role
never used, skills you said you don't have, and PDFs whose text an ATS cannot read. Nothing is marked sent without a
quoted confirmation. You approve every submission. It never logs in for you, never solves CAPTCHAs and never automates
LinkedIn at volume.

## Start in 3 steps (for anyone)
1. `git clone <this repo> && cd jobpilot && pip install pymupdf openpyxl`
2. Open the folder in Claude Code (`claude` in the terminal, or the desktop app).
3. Say **"hi"**. It asks for your **master CV** (PDF/Word), reads it, asks only what is missing (nationality,
   salary, start date, …), shows you your profile to confirm, and then you can say *"find jobs"*.
Your data stays on your computer in `workspace/` (git-ignored, never uploaded).

## Quick start (manual)
```bash
pip install pymupdf openpyxl            # the only dependencies (Python 3.9+)
python3 -m jobpilot init                 # creates the private workspace/ (git-ignored)
```
Then open this folder in Claude Code and say: *"Onboard me"* (it follows `playbooks/00_onboarding.md`), later
*"Find data science jobs in Berlin and Hamburg"*, *"Tailor and audit the good ones"*, *"Apply"*.

## The checklist (why it never forgets a detail)
`jobpilot/checklist.py` holds every detail a job search can need: 97 items collected from real application forms
(identity, salutation, date of birth, nationality, address, work permit and expiry, sponsorship, start date, notice
period, gross salary, work mode, office days, relocation, travel, driver's licence, years with and without internships,
years per field, people managed, references, certificates, talent pool, LinkedIn and e-mail preferences, ...).
- `python3 -m jobpilot profile` shows completeness per level: core · apply · linkedin · email · optional.
- `python3 -m jobpilot profile questions --level apply` prints only what is still missing, as short bullets.
- Every stage refuses to run until its level is complete (search/tailor need core, forms need apply).
- Questions that don't apply are skipped (no relocation question if you don't relocate; no permit expiry for EU
  citizens). Answer `-` to decline a question: forms then leave that field to you.

## Pipeline
| # | Stage | You say | It does |
|---|---|---|---|
| 0 | Onboarding | "onboard me" + your CV | builds `workspace/profile/profile.json`, asks only what's missing |
| 1 | Search | "find ML jobs in Berlin" | official APIs (Arbeitsagentur, Greenhouse, Lever, Ashby, Personio, SmartRecruiters), your sheets, your LinkedIn alerts |
| 2 | Triage | "go" | GOOD / CHECK / REMOVED with a reason; agent reads every CHECK |
| 3 | Tailor | "write them" | one spec per job; the agent writes summary, bullets, 4-paragraph letter |
| 4 | Audit | (automatic) | atomic findings (BLOCKER/MAJOR/MINOR) → fix → re-render → until clean; `findings.xlsx` |
| 5 | Apply | "apply" | ~100 forms filled by parallel agents → one approval line → you paste it → submit → evidence |
| 6 | LinkedIn | "optimise my LinkedIn" | keyword gaps vs your target adverts, drafts; you publish |
| 7 | Follow-up | "any replies?" | Gmail sweep → replies, interviews, rejections; tracker |

## Commands
`python3 -m jobpilot` lists them all. Most used: `status`, `show <id>`, `record <id> <STATUS> "<note>"`,
`approve-line <batch>`, `tracker`.

## Safety design
- **One truth:** `workspace/ledger.db` (SQLite) holds every job and every event; `tracker.xlsx` is generated from it.
- **Evidence rule:** SUBMITTED/EMAILED require `page: <quote>` or `mail: <subject>`; badges are refused.
- **Approval rule:** only jobs named in your pasted approval line become APPROVED; only APPROVED jobs are submitted.
- **Parallel chats:** each chat names itself (`JOBPILOT_CHAT`), claims its batch (`claim`), writes scratch only to
  `workspace/work/<chat>/`. A Claude Code hook (`.claude/settings.json` → `jobpilot/guard.py`) blocks writes anywhere else.
- **ATS-clean PDFs:** a font self-test, plus a ToUnicode clean-up, so "scikit-learn" and "Airflow" extract as plain text
  (no ligatures, no look-alike hyphens); the audit blocks any PDF that still contains them.

## Tests
`python3 -m unittest discover -s tests -v` (offline, ~1 s).

## Limits
- CV design is one clean template (`templates/style.css`); bring your own by editing the CSS.
- Sites that require an account (Workday, SuccessFactors, LinkedIn Easy Apply) are left to you by design.
- It cannot promise an ATS score; it guarantees a text PDF, the posting title in the headline, the advert's skills on
  the page (when your profile has them), and nothing claimed that you did not do.
