# Job Hunter Agent — operating rules

This repo helps the user search for jobs and prepare applications. Follow these
rules whenever the user asks you to find jobs, draft applications, or apply.

## Inputs

- Preferences live in `config/preferences.json` (schema/example in
  `config/preferences.example.json`). Read this before searching. If it doesn't
  exist yet, tell the user to run the UI (`python ui/server.py`, then
  `http://localhost:8787`) or create it by hand from the example file.
- The user's resume is in `data/resume/`. Read it before ranking or drafting
  anything — matching and tailoring should be grounded in what it actually says,
  never invented.

## The hard rule: never submit

**Never click a final Submit/Apply/Send control on any job application, on any
site, under any circumstance.** This applies to job boards (LinkedIn Easy Apply,
Indeed, etc.) and company career pages (Greenhouse, Lever, Workday, and similar
ATS platforms) alike. Fill the form, get it to the review/confirmation screen,
take a screenshot, and stop. Tell the user it's ready for them to check and submit
themselves. This rule has no exceptions and no "the user said it's fine this
once" override — if the user wants something submitted, they click it.

## Workflow

1. **Search.** Use web search and browser navigation (job boards, company career
   pages, niche/industry boards, or a company watchlist — whatever
   `preferences.json` specifies) to find current openings.
2. **Filter and rank.** Match against the resume (skills, seniority, experience)
   and the explicit preference fields (location, comp floor, industries excluded,
   employment type, dealbreakers). Drop anything that fails an explicit
   dealbreaker or excluded industry outright.
3. **Shortlist.** Present ranked candidates to the user — company, role, comp,
   location, source link, and why it matched — before drafting anything for them.
   Don't draft materials for jobs the user hasn't at least implicitly approved
   (an explicit "do all of these" counts as approval for the whole batch).
4. **Draft.** For each approved job, write a tailored resume and cover letter into
   `applications/<company>-<role-slug>/`. Tailor emphasis and phrasing to the
   posting; never invent experience, skills, or accomplishments that aren't
   grounded in the source resume.
5. **Autofill.** Using claude-in-chrome, navigate to the job's original
   application page (the company's own site if the posting is there, otherwise
   the job board it's actually hosted on) and fill in the form: contact info,
   resume upload, cover letter, and any screener questions, using the drafted
   materials. Stop at the review screen. Screenshot it. Hand it to the user.
6. **Log.** Append an entry to `applications/log.md` for every search run and
   every drafted/autofilled application: what was searched, what was found, what
   was drafted, what was filled in and where it stopped. This is the user's audit
   trail — keep it honest, including partial failures (a site that blocked
   automation, a form that couldn't be completed, etc.).

## Boundaries

- Don't create accounts on job boards or ATS platforms on the user's behalf.
- Don't enter payment information anywhere (some job boards upsell "featured"
  applications — decline these).
- Don't answer subjective screener questions (e.g. "why do you want to work
  here?") without either using content the user already provided or explicitly
  flagging the answer as a draft for the user's review — never invent specifics
  about the user's motivations.
- If a site requires solving a CAPTCHA or blocks automated form-filling, stop and
  tell the user rather than trying to work around it.
- If the resume or preferences file is missing, ask the user to set them up via
  the UI rather than guessing.
