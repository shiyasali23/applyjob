# 60 LinkedIn profile: optimise for the jobs being applied to, drafts first, user publishes

Never log in, post, connect, message, follow or endorse for the user. Never automate actions at volume.

1. **Get the current profile text**: the user pastes it, or a PDF export (More → Save to PDF) into `workspace/inbox/`,
   or (only if the user asks in this chat) read it in his logged-in browser. Save the text as
   `workspace/work/<chat>/linkedin_profile.txt`.
2. **Keyword gaps**: `python3 -m applyjob gaps workspace/work/<chat>/linkedin_profile.txt` lists the skills the
   target adverts ask for most, whether the LinkedIn text has them, and whether the profile backs them
   (`profile:yes`). Only `profile:yes` skills may be added.
3. **Draft** (into `workspace/work/<chat>/linkedin_drafts.md`), every claim from `profile.json`:
   - Headline (≤ 220 chars): target role + 3-4 strongest backed skills + one proof. No "seeking opportunities".
   - About (3 short paragraphs): what the person builds, proof with real numbers, what they want next.
   - Experience entries: the profile bullets in the adverts' vocabulary (same facts, same numbers).
   - Skills: the top backed gap skills first (LinkedIn shows the top skills; recruiters filter on them).
   - Settings to suggest: Open to Work (recruiters only), job titles and locations = preferences, custom URL.
4. Run the same checks as the audit by eye: no invented numbers, no tools the role did not use, no buzzwords.
5. Give the user the drafts. If he asks you to put them on his profile in this chat: edit the fields in his
   logged-in browser and stop before every Save, so he clicks Save himself.
