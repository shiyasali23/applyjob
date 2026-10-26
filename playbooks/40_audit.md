# 40 Audit: atomic error list → fix → re-audit until clean

`python3 -m applyjob render <batch>` then `python3 -m applyjob audit <batch>`.
Each finding is ONE problem at ONE place: `A07 BLOCKER cv.acme.b2 | rule | evidence -> fix`. All findings of the batch
are also in `batches/<b>/_apply/findings.xlsx` (one row each), for the user.

## Severities
- **BLOCKER** would be false or broken: a fabricated number or tool, never_claim/never_mention text, wrong company,
  unreadable PDF text (ligatures!), placeholders. Never send.
- **MAJOR** costs the interview: advert term missing on the CV, headline ≠ posting title, letter too long/short,
  salary rule broken, page limits. Fix before sending.
- **MINOR** polish: duplicate skill, long sentence, dash style. Fix when cheap.

## Loop (per job, until 0 BLOCKER and 0 MAJOR)
1. Read the finding. Decide if the CHECK is right or the document is (the checker can be wrong: prove it before
   "fixing" a document, and if the checker is wrong, tell the user and note it in `workspace/work/<chat>/checker_issues.md`).
2. Fix the spec (never the PDF). Re-render that job: `render <batch> <id>`; re-audit: `audit <batch> <id>`.
3. Never fix by inventing: a missing advert skill goes into a skills row only if the profile allows learnable skills;
   otherwise remove it from `terms` and accept the gap.

## Then the human layer (no gate catches these)
4. **Read every summary and every letter yourself** (dump them compactly). Grammar, tone, a sentence that sounds
   like a template, a claim that is true but overstated → fix.
5. Open 3 rendered CVs and 3 letters of different job families as images and look at them.
6. Report: N audited, N pass, N fail with the top rules, and what the user must decide.
