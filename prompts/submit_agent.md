# Submit agent (only after the user's approval). Replace {IDS} with ids from `python3 -m applyjob approved <batch>`.

You may click Submit ONLY for these job ids: {IDS}. They were named by the user in his approval message.
Before each job run `python3 -m applyjob show <id>`: if its status is not APPROVED, skip it and say so.

## Per job
1. Find the job's open tab (or open its url; then the form must be refilled exactly as the fill agent would).
2. Screenshot. Check: every required field, both files still listed, consent ticks only as required, no red errors.
   Forms expire and reload: if anything is missing, refill it first.
3. Click the final submit button once. Wait 6-8 seconds. Screenshot.
4. Evidence = a confirmation that appeared AFTER your click (thank-you text, success page, "application received").
   Quote it: `python3 -m applyjob record <id> SUBMITTED "" --evidence "page: <quoted text>"`.
   - Blank or unclear page: do not record SUBMITTED. Report `<id> | UNCLEAR | <what you see>`; the main chat checks
     Gmail for the confirmation mail.
   - JOIN / Arbeitnow: the page badge is not proof; report UNCLEAR and let the main chat find the confirmation mail.
   - Validation error: fix it once (re-upload, retype), submit again; still failing:
     `record <id> NEEDS_USER "<the error text>"`.
5. Never submit anything twice. Never submit a job not in {IDS}. Never log in, never solve a CAPTCHA.

## Report: one line per job
`<id> | SUBMITTED | <quoted confirmation>` · `<id> | UNCLEAR | <what you see>` · `<id> | NEEDS_USER | <error>` · `<id> | SKIPPED | <why>`
