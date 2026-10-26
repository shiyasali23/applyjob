# 10 Search: find jobs from allowed sources only

Every found job goes into the ledger (`FOUND`); duplicates (same company+title, or same link) are merged automatically.

## Sources, best first
1. **Official APIs** (fast, complete, allowed):
   - `python3 -m jobpilot search ba "Data Scientist" --where Berlin` (German federal job board, 100s per query;
     run one query per target role and city)
   - `python3 -m jobpilot search board greenhouse <token>` (also `lever`, `ashby`, `personio`, `smartrecruiters`):
     every open job of one company. The token is in the company's job-board URL.
2. **Sheets from the user** (any Excel/CSV with company/title/link columns): `python3 -m jobpilot import file.xlsx`.
3. **LinkedIn**, the user's own account, logged in by the user (never by you):
   - Best: the user's **LinkedIn job-alert e-mails**. Read them with the Gmail connector (or the user forwards them),
     save the text to `workspace/inbox/linkedin_<date>.txt`, then `python3 -m jobpilot import workspace/inbox/...txt`.
     Only job links are kept; tracking parameters are stripped.
   - Or the user opens a LinkedIn search and you read the **job pages one at a time** in the browser (no scrolling
     loops, no exporting result lists, no automation at volume: LinkedIn User Agreement §8.2), then save the links
     the same way.
   - For every LinkedIn job, find the **employer's own apply page** (career site / ATS) and switch the job to it:
     `python3 -m jobpilot edit <id> --company "X GmbH" --title "Exact title" --url <employer link>`.
     Easy-Apply-only jobs: leave the LinkedIn link; the user applies to those himself (status `LOGIN`).
4. **Other boards** (StepStone, Indeed, company pages): same as LinkedIn, one page at a time, save links, import.

## After every search
`python3 -m jobpilot status` and tell the user: N found, N new, N duplicates, by source.
