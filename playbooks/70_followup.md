# 70 Follow-up: replies, rejections, interviews, and the weekly report

1. **Gmail sweep** (connector, read-only): search the last 7 days for each SUBMITTED/EMAILED company:
   confirmations (add evidence if missing), "complete your application" reminders (= not sent → NEEDS_USER),
   rejections → `record <id> REJECTED "mail: <subject>"`, invitations → `record <id> INTERVIEW "mail: <subject>"`,
   other replies → `REPLIED`.
2. Watch for scams: payment requests, "agency fees", crypto, requests for ID scans before an interview → tell the
   user plainly, never reply.
3. Interviews: create `workspace/work/<chat>/interview_<company>.md`: the advert, the CV and letter that were sent
   (from the batch folder), the 5 likely questions per advert requirement, and the profile facts that answer them.
4. Never reply or send on the user's behalf; draft replies only when asked, into Gmail Drafts at most.
5. Weekly: `python3 -m jobpilot tracker` + `status`; report sent / replies / interviews / rejections, and what
   changed in the search (more GOOD jobs in which roles/cities).
