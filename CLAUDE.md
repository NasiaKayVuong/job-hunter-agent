# Job Hunter Agent — operating rules

This repo helps the user search for jobs and prepare applications. Follow these
rules whenever the user asks you to find jobs, draft applications, or apply.

## Inputs

- Preferences live in `config/preferences.json` (schema/example in
  `config/preferences.example.json`). Read this before searching. If it doesn't
  exist yet, tell the user to run the desktop app (`python app.py`, or
  `python ui/server.py` for the browser-tab version) and use the Setup tab, or
  create it by hand from the example file.
- The user's resume is in `data/resume/`. Read it before ranking or drafting
  anything — matching and tailoring should be grounded in what it actually says,
  never invented.

## Session continuity

`state/session-log.md` (gitignored — see `state/session-log.example.md` for
the format) is the only memory of prior sessions; a fresh Claude Code session
has no other way to know what happened before. **Read it at the start of any
session that touches this repo**, before searching or drafting anything —
the `/start` command does this automatically. **Append a new dated entry**
(never rewrite prior ones) after any significant work: a search run, a batch
of drafts, a status sync, anything the user would want a future session to
know without re-explaining. Keep entries short — this is a narrative thread
connecting sessions, not a duplicate of `applications/log.md` or the tracker.

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
2. **Dedup before presenting anything.** Read both `python tools/tracker.py
   list` (real applications — any stage, including Rejected/Withdrawn) and
   `python tools/listings.py list` (existing shortlist). Match by company +
   title (fuzzy is fine — "Sr. Full Stack Engineer" and "Senior Full Stack
   Engineer" at the same company is the same listing). Drop anything already
   in the tracker outright — already applied, don't resurface it. For
   something already in Listings: if status is "Passed", drop it too (the
   user already said no); if "New"/"Interested"/"Applied", don't add a
   duplicate row, just skip it in the new results (mention in passing that it
   was already found before, if relevant).
3. **Filter and rank.** Match against the resume (skills, seniority, experience)
   and the explicit preference fields (location, comp floor, industries excluded,
   employment type, dealbreakers). Drop anything that fails an explicit
   dealbreaker or excluded industry outright.
4. **Shortlist.** Present ranked candidates to the user — company, role, comp,
   location, source link, and why it matched — before drafting anything for them.
   Also record each one with `python tools/listings.py add --company ... --title
   ... --location ... --job-type ... --comp-range ... --source ... --url ...
   --match-notes ...` so it shows up in the desktop app's Listings tab, where
   the user can mark it Interested/Passed on their own. Don't draft materials
   for jobs the user hasn't at least implicitly approved (an explicit "do all
   of these" counts as approval for the whole batch; a listing marked
   "Interested" in the Listings tab also counts — check there if the user
   says something like "draft the ones I marked").
   - **Prefer the company's own site for the `--url`.** If a listing was
     found on a job board (LinkedIn, Indeed, etc.), do a quick search for the
     same role on that company's own careers page before logging it. If you
     find the same posting there, use that URL instead of the job board's —
     it's both a better link to hand the user and the site autofill (step 6)
     should target anyway. If you can't find it on the company site (or
     aren't confident it's the same posting), use the job board URL and say
     so rather than guessing. Don't spend more than a quick search on this
     per listing — it's a nice-to-have, not worth stalling the whole
     shortlist over one stubborn company site.
5. **Draft.** For each approved job, write a tailored resume and cover letter into
   `applications/<company>-<role-slug>/`. Tailor emphasis and phrasing to the
   posting; never invent experience, skills, or accomplishments that aren't
   grounded in the source resume.
6. **Autofill.** Using claude-in-chrome, navigate to the job's original
   application page (the company's own site if the posting is there, otherwise
   the job board it's actually hosted on) and fill in the form: contact info,
   resume upload, cover letter, and any screener questions, using the drafted
   materials. Stop at the review screen. Screenshot it. Hand it to the user.
7. **Log.** Append an entry to `applications/log.md` for every search run and
   every drafted/autofilled application: what was searched, what was found, what
   was drafted, what was filled in and where it stopped. This is the user's audit
   trail — keep it honest, including partial failures (a site that blocked
   automation, a form that couldn't be completed, etc.).
8. **Track.** After the user confirms they actually submitted an application
   (never before — an autofilled-but-unsubmitted form isn't a real application),
   record it with `python tools/tracker.py add ...`: company, title, job URL,
   source (the platform/site actually applied on), location, job type
   (remote/hybrid/onsite), which resume and cover letter version were used
   (reference the files in `applications/<company>-<role-slug>/`), and a rough
   skill-match assessment between the JD and the resume (state it as a rough
   judgment, e.g. "7/10 — strong on React/TypeScript, light on the required Go
   experience", never as a precise score). If the user asks you to also save
   the tailored resume/cover letter to Drive (optional — local files under
   `applications/` are the default, this is not required), use
   `python tools/drive.py save-draft --path ... --name ... --kind resume` (or
   `--kind cover_letter`) — this lands in the "Resumes"/"Cover Letters"
   subfolder of the "Job Tracker" Drive folder (see `tools/drive.py`
   `ensure_folders()`), the same folder the tracker Sheet lives in, and always
   creates a new file rather than overwriting anything.

## Calendar and tracking

- **Scheduling an interview.** When the user tells you about a scheduled
  interview (or you find one while scanning email — see below), create a
  calendar event with `python tools/gcal.py create --summary ... --start
  ... --end ...`. Use a clear summary ("Interview: <Company> — <Round>").
  **Never add attendees or send an invite** — the tool has no attendees
  parameter at all, by design. If the user wants to invite someone, tell them
  to do that themselves in Google Calendar.
- **Checking status.** On request (not proactively/automatically), scan for
  application status updates with `python tools/gmail_scan.py scan`. This is
  read-only — it never sends, replies, or modifies anything in Gmail. It
  returns *candidates* with a guessed status (possible interview / rejection /
  offer / unclassified). Treat every guess as unverified: show the candidates
  to the user, ask which ones are real updates and what the actual new stage
  is, and only then call `python tools/tracker.py update-stage --row N --stage
  "..."` for the ones the user confirms. Never auto-update the tracker from a
  guess alone.
- **Using the tracker for better search.** Before ranking a new shortlist, you
  can read the full tracker with `python tools/tracker.py list` and look for
  patterns — which titles, sources, locations, or resume/cover-letter versions
  are correlating with interviews or later stages versus early rejections.
  Mention any pattern you find as a rationale, not as a hard rule (a handful of
  data points is not statistically strong evidence — say so if the sample is
  small).
- The tracker is a Google Sheet inside a "Job Tracker" folder in the user's
  own Drive (folder + Sheet created automatically on first use via
  `tools/drive.py ensure_folders()` and `tools/tracker.py ensure_sheet()`, IDs
  cached in `config/tracker.json`, gitignored). It's meant to be opened and
  edited by the user directly too — don't treat it as a Claude-only data store.
- The desktop app (`python app.py`) is a viewer/input surface, plus a few
  self-service actions that involve no judgment: it can call
  `tools/gmail_scan.py scan` directly (a button, read-only, same keyword
  heuristic Claude uses — no LLM judgment happens there either way) and let
  the user apply `tools/tracker.py update-stage` / `tools/listings.py
  update-status` themselves via dropdowns, instead of asking Claude to do it.
  What it must never do: search job boards, rank/match against the resume,
  draft anything, or autofill an application — anything requiring judgment
  or writing on the user's behalf stays exclusively Claude's job. Don't add
  functionality to `app.py`/`ui/` that crosses that line.

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
- Never add calendar attendees or otherwise send a calendar invite — not
  possible through `tools/gcal.py` by design, and don't work around that
  by calling the Calendar API some other way.
- Gmail access is read-only search (`tools/gmail_scan.py`). Never attempt to
  send, reply to, or modify email — there is no code path for it here, and it
  should stay that way.
- Don't run `tools/gmail_scan.py` or touch the tracker without being asked in
  that session — no proactive/background scanning.
- `tools/drive.py` is create-only and read-only — there is no update/
  overwrite/delete function for Drive files anywhere in this repo. Never edit
  or delete a file in the user's Drive that this tool didn't itself create.
- `tools/listings.py` is a shortlist, not the tracker — a row there being
  "Interested" doesn't mean an application exists yet, and a row being
  "Passed" doesn't need to be deleted (there's no delete function; leave it).
  Only `tools/tracker.py add` creates a real tracked application, and only
  after the user confirms an actual submission.
