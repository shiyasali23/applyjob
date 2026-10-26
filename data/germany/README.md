# data/germany: company job boards

`boards.csv.gz`: 24,443 company job boards (`kind, token, domain, company`), collected in Sept-Oct 2026 from the
public Common Crawl index and from links on German company websites (`domain` is the site that linked the board;
`cc-index` means the board was found in the index directly).

`python3 -m applyjob search germany` reads every supported board through its public job feed and keeps only jobs
whose location is in Germany (or remote) and whose title matches your target roles.

| kind | boards | read |
|---|---|---|
| workable, greenhouse, ashby, personio, smartrecruiters, teamtailor, recruitee, lever | 18,749 | yes (public JSON/XML feeds) |
| workday, softgarden, join, dvinci | 5,694 | listed only (need page scraping or an account) |

No credentials, no personal data: only public board identifiers and company domains.
