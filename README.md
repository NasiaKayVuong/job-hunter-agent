# Job Hunter Agent

A starter kit for running your job search through [Claude Code](https://claude.com/claude-code):
search job boards and company career pages, filter listings against your resume and
your stated preferences, draft a tailored resume/cover letter per role, and fill out
the actual application on the original site (job board or, where possible, the
company's own careers page) up to the review screen — **it never clicks the final
Submit/Apply button for you.** You always review and submit yourself.

## How it works

There are two halves, deliberately separate:

- **The desktop app** (`python app.py`) is one window where *you* manage
  everything: set your resume/preferences, connect your Google account, and
  view your tracked applications and upcoming interviews. It never searches,
  scrapes, drafts, or applies to anything by itself.
- **Claude** (via Claude Code, opened on this same folder) does the actual
  work: searching job boards and company career pages, ranking matches
  against your resume/preferences, drafting tailored materials, filling out
  real application forms, and — once you confirm you've submitted — logging
  it to the tracker.

1. Run the desktop app and set your resume/preferences (and, optionally,
   connect Google for Calendar/Gmail/Sheets/Drive — see "Calendar and
   tracking" below).
2. Open this folder in Claude Code and ask it to find and apply to jobs (or
   run the `/find-jobs` command).
3. Claude searches, ranks, and — for the roles you approve — drafts tailored
   materials into `applications/<company>-<role>/`.
4. Using the [claude-in-chrome](https://claude.com/chrome) browser extension, Claude
   navigates to the real application page and fills it in. It stops at the review/
   confirm screen every time and hands control back to you.
5. Once you've actually submitted (Claude asks, never assumes), it logs the
   application to the tracker, and can create calendar events for interviews
   and scan your email for status updates.
6. Check the desktop app's Applications and Calendar tabs any time to see
   what's tracked — it's a live view of the same Sheet/Calendar Claude reads
   and writes to, not a separate copy.

Nothing is ever submitted without you personally clicking the button.

## Setup

**Requirements:** Python 3.9+, Claude Code, and the
[claude-in-chrome](https://claude.com/chrome) browser extension connected to
Claude Code if you want the autofill step (search and drafting work without
it).

```
git clone <this-repo-url>
cd job-hunter-agent
python app.py
```

This opens the dashboard in its own window (via `pywebview`). The Setup tab
needs no extra packages; the Connections/Applications/Calendar tabs and the
underlying Google features need a few — `pip install -r requirements.txt`
covers all of it, including `pywebview` itself. If you'd rather skip the
desktop window and just use a browser tab, `python ui/server.py` and open
`http://localhost:8787` works the same way with zero extra packages needed
for the Setup tab.

In the Setup tab: upload your resume (PDF or DOCX) — or use "Import from
Drive instead" once Google is connected — and fill in your preferences:
target role/level, locations, comp floor, industries to include/exclude,
employment type, and any dealbreakers. Click Save. This writes:

- `data/resume/` — your uploaded resume file
- `config/preferences.json` — your preferences (see `config/preferences.example.json`
  for the schema if you'd rather edit it by hand)

Both are **gitignored** — your resume and preferences never get committed or pushed.

Then open this folder in Claude Code and say something like:

> Find roles matching my resume and preferences and show me a shortlist before
> drafting anything.

or run the bundled command:

```
/find-jobs
```

## Calendar and tracking (optional)

Lets Claude create calendar events for interviews and keep an application
tracker (a Google Sheet) — company, source, location, job type, which resume/
cover letter version you used, a rough skill-match note, and the current
stage, updated as each round progresses. Everything lives in a **"Job
Tracker"** folder created in your own Drive, with **"Resumes"** and **"Cover
Letters"** subfolders that drafts get saved into if you ask Claude to push
them to Drive, and the tracker Sheet itself in the top-level folder.

This is a standalone OAuth setup, independent of any Google connector you may
already have wired into Claude itself (a Claude.ai first-party connector, or
your own custom MCP server) — those aren't reachable by a plain local script,
so this repo needs its own.

**One-time setup:**

1. In the [Google Cloud Console](https://console.cloud.google.com/), either
   create a new project, or **reuse one you already have** (e.g. one you set
   up for another personal Google integration) — either is fine. Enable the
   **Google Calendar API**, **Gmail API**, **Google Sheets API**, and
   **Google Drive API** in it (some may already be enabled if you're reusing
   a project).
2. Under "APIs & Services → Credentials", create an **OAuth client ID** of
   type **Desktop app** (or reuse an existing Desktop-app client from that
   project — a second, dedicated client is slightly cleaner since it keeps
   this tool's consent grant separate from anything else using that project,
   but either works). Download the JSON.
3. Save it as `data/google/client_secret.json` (gitignored — never commit it).
4. `pip install -r requirements.txt`
5. `python auth/google_auth.py` (or click "Connect Google account" in the
   desktop app's Connections tab) — opens a browser for you to authorize.
   Sign in with whichever Google account you want this tool to use — that
   choice is independent of which project/client issued the request. This
   grants: Calendar (read/write your own calendar), Gmail (**read-only**
   search), Sheets (read/write), and Drive (read-only browsing + create-only
   for saving drafts). There is no send-email or invite-someone capability
   anywhere in this repo's code — see `CLAUDE.md`.

**Using it**, once set up:

- The desktop app's **Connections** tab shows whether you're connected and
  has a one-click "Connect Google account" button (same underlying flow as
  step 5 above).
- The **Listings** tab shows jobs Claude has found during a search, before
  you've decided to apply — mark ones **Interested** or **Passed** right
  there, then tell Claude to draft materials for whatever you marked
  Interested.
- The **Applications** tab shows a live table of everything actually tracked
  (i.e. submitted). Its **Stage** column is an editable dropdown — changing it
  updates the same Sheet Claude reads, no need to ask Claude for a routine
  status bump.
- The **Calendar** tab shows your next 30 days of interviews (read-only).
- In Applications, **"Scan email for updates"** reads recent email (read-only
  — never sends or modifies anything) for likely interview/rejection/offer
  messages and shows you the candidates with a rough keyword guess at what
  each one is — read them yourself and use the Stage dropdown to actually
  update the tracker. This is the same tool `/sync-status` uses; the button
  just lets you do it yourself without asking Claude. Note: **the desktop app
  has no live connection to Claude** — it can run this one read-only scan and
  let you apply status changes, but it can't itself search jobs, draft
  anything, or decide what an email means; that judgment stays with you or
  with Claude in a chat.
- In Setup, "Import from Drive instead" lets you pick your resume from Drive
  rather than uploading a local file.
- Ask Claude to schedule an interview, or run `/schedule-interview` — creates
  a calendar event (never with attendees; if you want to invite someone,
  do that yourself in Google Calendar).
- Ask Claude to check for updates, or run `/sync-status` for the same
  email-scan-then-confirm flow as the button above, driven through chat
  instead.
- The tracker itself is a normal Google Sheet (with a second "Listings" tab)
  in the "Job Tracker" folder in your own Drive — open it, edit it, or add
  rows by hand any time; Claude and the desktop app both read and write to
  the same sheet, not a separate copy.
- Claude can look at the tracker's history to help decide what to search for
  next — which titles, sources, or resume/cover-letter versions are actually
  getting responses.

## What Claude will and won't do on its own

- **Will:** search multiple sources (job boards + company career pages), rank matches
  against your resume/preferences, draft a tailored resume and cover letter per role
  you approve, autofill the real application form up to the review screen, and
  (if you set up the optional Google integration) create calendar events and
  log/read the application tracker and listings.
- **Won't:** click Submit/Apply, create accounts on your behalf, send a
  calendar invite to anyone, send or reply to any email, or send anything
  without showing you first. Every autofilled application is left open for
  your own review and submission; every tracker status change from a scanned
  email is confirmed by you first — by Claude in chat, or by you directly in
  the desktop app.
- The desktop app itself never searches, ranks, or drafts anything — it can
  run one read-only email scan and let you apply status changes yourself, but
  the judgment calls stay with Claude or with you.
- Read `CLAUDE.md` for the exact operating rules Claude follows in this repo.

## Repo layout

```
app.py                       desktop app entry point (python app.py)
config/preferences.json      your saved preferences (gitignored)
config/preferences.example.json   the schema/template, with placeholder values
config/tracker.json          your tracker's Sheet + Drive folder IDs (gitignored)
config/tracker.example.json  the schema note/template
data/resume/                 your uploaded resume (gitignored)
data/google/                 your OAuth client secret + token (gitignored)
ui/                          the dashboard (server.py + index.html/app.js/style.css)
auth/google_auth.py          shared Google OAuth helper (Calendar, Gmail-read, Sheets, Drive)
tools/gcal.py                create/list calendar events (no attendees, ever)
tools/tracker.py             read/write the application tracker (Google Sheet)
tools/listings.py            read/write candidate listings (2nd tab, same Sheet)
tools/gmail_scan.py          read-only email scan for status updates
tools/drive.py               import a resume from Drive; save drafts (create-only);
                              creates/finds the Job Tracker / Resumes / Cover Letters folders
applications/                drafted materials + a log of what was searched/applied to (gitignored)
.claude/commands/            /find-jobs, /schedule-interview, /sync-status
CLAUDE.md                    operating rules for Claude in this repo
```

## Privacy

Your resume and preferences live only on your machine (`data/` and
`config/preferences.json` are gitignored). Job search and drafting use Claude's
normal tools; the autofill step uses your own logged-in browser session via
claude-in-chrome — no separate account or credential is stored by this repo.

If you set up the optional Google integration, your OAuth client secret and
token live in `data/google/` (gitignored) and are used only for your own
Calendar, Gmail (read-only), Sheets, and Drive access — nothing is sent to any
third-party server. The tracker Sheet and any saved drafts live in a "Job
Tracker" folder in your own Google Drive, not anywhere this repo controls; the
desktop app only ever displays what's there, it doesn't copy it elsewhere.
