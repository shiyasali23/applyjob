# 30 Tailor: one CV + one letter per job, written for that job, true to the profile

1. `python3 -m applyjob batch <label>` (e.g. `berlin-ml-oct`) → `batches/<date>_<label>`; claim it.
2. `python3 -m applyjob tailor <batch>` drafts `spec.json` per GOOD job: headline (= posting title), skills rows
   re-ordered with the advert's skills first, the profile's bullets, the advert's terms, and TODO slots.
3. **Write every TODO slot** (batches of ~10 jobs; read `_advert` in each spec first, then the profile):
   - `summary`: 3-4 sentences. Starts with the headline role, years of experience as the profile states them,
     the 2-3 things THIS employer needs, proven by the profile. No title repeated inside its own sentence.
   - `experience[].bullets`: reword the profile bullets in the advert's words. Same facts, same numbers, only tools
     from that role's `stack`. Keep every role (no gaps).
   - `soft_skills`: 3 × [title, one sentence in first person], from the advert's values; behaviour, no tools.
   - `letter.subject`: "Application as <exact posting title>" (in the document language).
   - `letter.salutation`: the named contact if the advert names one, else the team ("Dear <Company> team,").
   - `letter.to`: company, contact, street, postcode city (from the advert or the employer's imprint, never memory).
   - `letter.paragraphs`, 4 short paragraphs, plain language, sentences ≤ 24 words:
     1. "I am applying as <role> at <Company>." + who the person is in one line + what THEY build (their own nouns).
     2. Their top 2-3 requirements mapped to real achievements: systems, scale, users, ownership. 0-2 numbers.
     3. What the person brings to the team; relocation if needed; salary/start ONLY if the advert asks
        (`asks_salary`, `asks_start`); the profile's `writing.letter_required_sentence` if set.
     4. One closing sentence asking for a conversation.
   - `mirror`: the employer's own product/team words you quote in the letter (e.g. their product name). They must
     appear in the advert; the audit then knows they are not skill claims.
   - `letter.closing`: "Kind regards," / "Mit freundlichen Grüßen,".
4. Never: model scores as brags, buzzwords, hedging ("although I lack…"), facts outside the profile,
   a tool in a bullet that the role did not use, a number not in the profile.
5. Next: playbooks/40_audit.md.
