# 50 Apply: 100 forms filled in parallel, submitted only on approval, every send proven

## Before
- The user is logged in to his browser (Chrome with the Claude in Chrome extension) in the right account. Check it
  on a neutral page first (account avatar). You never log in.
- `python3 -m applyjob claim batch:<label>`.

## Approve the whole batch once, BEFORE filling
1. `python3 -m applyjob approve-batch <batch>` prints ONE line naming every open job: `submit 12 Acme, 15 Beta, ...`.
   Give it to the user. He deletes what he doesn't want and pastes it back, once.
2. `python3 -m applyjob approve <batch> "<his pasted line>"`. A job whose name doesn't match its id is refused.
   "send all" or "apply to everything" is not an approval: answer with the line.

## One wave: fill AND submit, in parallel (nothing comes back to him job by job)
3. `python3 -m applyjob queue <batch> --groups 12` → `_apply/group_01..12.json` (~8 jobs each, each with `approved`).
4. Start one agent per group with `prompts/apply_agent.md` (replace {GROUP_FILE}, {BATCH}), all in parallel.
   Each agent fills every form and submits only jobs that are approved, complete, and free of CAPTCHA/login.
   Everything else stays open in a tab, with the exact reason.
5. Record each agent line at once: `record <id> SUBMITTED "" --evidence "page: <quote>"` (refused for unapproved jobs),
   or `NEEDS_USER|LOGIN|EMAIL_ONLY|CLOSED "<what exactly>"`. UNCLEAR → check Gmail for the confirmation mail first.
6. ONE report: sent n (with proof) · needs you n (tab + reason) · login n · e-mail only n · closed n.

## After
10. Gmail sweep the same day and the next: confirmations (fill missing evidence), "complete your application"
    reminders (= NOT sent: set back to NEEDS_USER), rejections.
11. `python3 -m applyjob tracker` and `status <batch>`; report sent n of approved n, with what still needs him.
12. Release the claim.

## Lessons (do not repeat)
- Hidden success templates exist in the page before submitting: only a message that appears after your click counts.
- `find`/accessibility trees can call a filled field empty: the screenshot decides.
- Overnight, filled forms expire (SmartRecruiters): submit in the same session or refill.
- After a failed submit some forms reload and drop the uploads: re-upload before retrying.
