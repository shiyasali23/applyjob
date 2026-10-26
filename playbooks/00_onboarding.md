# 00 Onboarding: learn the person (profile.json), never guess

Goal: `workspace/profile/profile.json` holds every fact any later stage may use. Shape: `examples/profile.example.json`.
Done when `python3 -m applyjob profile check` prints `profile OK` and the user confirmed the facts.

## Steps
1. `python3 -m applyjob profile new`: an empty profile with every checklist field (it also unlocks profile edits;
   later changes: `touch workspace/.onboarding`).
2. **Collect sources from the user** (ask once, all at once): current CV (PDF), LinkedIn profile (PDF export or
   pasted text), certificates, any "facts" notes, target roles, cities, contract type, salary, start date,
   languages with levels, work permit. Files go to `workspace/inbox/`.
   Read each file with `python3 -m applyjob read-cv <file>` (PDF/DOCX/TXT → `workspace/inbox/<name>.txt`).
   Fill `workspace/profile/profile.json` (shape: `examples/profile.example.json`). Put the CV file in `workspace/inbox/`
   and set `documents.master_cv` to its path (e.g. `inbox/cv.pdf`).
3. **Extract** into the profile: person, experience (one entry per role, with `stack` = tools that role really
   used, `bullets` = verified achievements with their real numbers), education, certifications, skills (grouped),
   languages. Copy numbers exactly; never round, never upgrade a title.
4. **Ask for what is missing**: `python3 -m applyjob profile questions --level core` → send it as is (short bullets).
   Then `--level apply`, `--level optional` (later `linkedin`, `email` when the user wants those). One message per
   level. Store each answer at its key. "-" = declined. Repeat until `python3 -m applyjob profile` shows the levels
   complete.
5. **Rules the user gives** go in the profile, not in your memory: `never_claim` (tools they do not know),
   `never_mention` (gaps, side jobs), `writing.*` (word limits, a sentence every letter must contain, banned words),
   `preferences.exclude_title_words`, `preferences.blockers`, `preferences.include_learnable_advert_skills`.
6. Optional photo: `workspace/profile/photo.jpg` (square, < 300 KB).
7. **Read the profile back to the user** in plain sentences (who, roles, numbers, rules) and ask "correct?".
   Fix what they correct. Then `profile check`, `rm workspace/.onboarding`.

## Hard rules
- A fact enters the profile only from the user's documents or the user's words. If two sources disagree, ask.
- Separate what a role USED (stack) from what the person KNOWS (skills). Audits rely on that split.
- Personal data stays in `workspace/` (git-ignored). Never paste it into issues, logs or other repos.
