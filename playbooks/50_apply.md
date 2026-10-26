# 50 Apply: 100 forms filled in parallel, submitted only on approval, every send proven

## Before
- The user is logged in to his browser (Chrome with the Claude in Chrome extension) in the right account. Check it
  on a neutral page first (account avatar). You never log in.
- `python3 -m jobpilot claim batch:<label>`.

## Wave 1: fill (parallel, nothing is submitted)
1. `python3 -m jobpilot queue <batch> --groups 12` → `_apply/group_01..12.json` (~8 jobs each; 12 agents ≈ 100 forms).
2. Start one fill agent per group with `prompts/fill_agent.md` (replace {GROUP_FILE}). Run them in parallel.
3. Each agent returns one line per job. Record each line at once:
   `python3 -m jobpilot record <id> READY|NEEDS_USER|LOGIN|EMAIL_ONLY|CLOSED|EXPIRED "<what exactly>"`.
4. Jobs on platforms that need the user's account (Workday, SuccessFactors, JOIN, LinkedIn Easy Apply): `LOGIN`.

## Approval (one message from the user)
5. Report: READY n, NEEDS_USER n (each with the exact field), LOGIN n, EMAIL_ONLY n, CLOSED n.
6. `python3 -m jobpilot approve-line <batch>` prints `submit 12 Acme, 15 Beta, ...`. Give it to the user. He pastes
   it back (he may delete jobs from it). Then `python3 -m jobpilot approve <batch> "<his pasted line>"`.
   Only jobs in his paste become APPROVED. Never approve on his behalf.

## Wave 2: submit approved jobs only (≤ 4 submit agents in parallel, or yourself)
7. `python3 -m jobpilot approved <batch>` is the ONLY list a submit agent may act on (`prompts/submit_agent.md`).
   Per job: screenshot → re-check every field and both files (forms expire, reload and drop uploads) → submit →
   wait 6-8 s → screenshot → read the confirmation.
8. Record with evidence: `record <id> SUBMITTED "" --evidence "page: <quoted confirmation>"`. Unclear page: search
   Gmail for the confirmation mail first; JOIN/Arbeitnow need a mail (their on-page badge has lied before).
9. Validation error: fix (re-upload, retype React fields), retry once, else `NEEDS_USER`.

## After
10. Gmail sweep the same day and the next: confirmations (fill missing evidence), "complete your application"
    reminders (= NOT sent: set back to NEEDS_USER), rejections.
11. `python3 -m jobpilot tracker` and `status <batch>`; report sent n of approved n, with what still needs him.
12. Release the claim.

## Lessons (do not repeat)
- Hidden success templates exist in the page before submitting: only a message that appears after your click counts.
- `find`/accessibility trees can call a filled field empty: the screenshot decides.
- Overnight, filled forms expire (SmartRecruiters): submit in the same session or refill.
- After a failed submit some forms reload and drop the uploads: re-upload before retrying.
