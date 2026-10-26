# 20 Triage: GOOD / CHECK / REMOVED, with a reason for every job

1. `python3 -m applyjob triage --workers 12` fetches every FOUND advert (platform APIs first) and judges it by the
   profile's preferences: excluded title words and contract types → REMOVED; closed → CLOSED; anything uncertain
   (blockers, years, location, unreadable page, LinkedIn link) → CHECK with the reason.
2. **Read every CHECK advert yourself** (`python3 -m applyjob show <id>`, or open it in the browser when the text is
   empty) and decide:
   - `record <id> GOOD "<why it fits>"` or `record <id> REMOVED "<the real blocker>"`.
   - Real blockers: a hard requirement the profile cannot meet (years far above, a degree type, a language the
     person does not speak as a CORE skill, security clearance), not a real job (aggregator, course, event),
     no longer accepting applications.
   - NOT blockers: "German/English fluent" when the user said apply anyway, relocation when the user relocates,
     nice-to-have tools. Follow the profile's preferences, not your own taste.
3. Duplicates the ledger could not merge (same job via two agencies, same role in two cities): keep both, note
   "send one" on the second.
4. Sample 10 GOOD jobs and read them in full. If any is wrong, fix the profile's preferences, not just the row.
5. Report: GOOD n / CHECK n / REMOVED n (top 5 reasons) / CLOSED n. Ask the user to confirm before tailoring
   ("go N good ones").
