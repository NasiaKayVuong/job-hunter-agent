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

1. Open this folder in Claude Code and run `/start` — it reads
   `state/session-log.md` (what happened last time, if anything), checks
   your preferences/resume/connection status, and launches the desktop app
   for you. (First time, or without Claude Code: just run the desktop app
   directly and set your resume/preferences yourself — see "Setup" below.)
2. Ask Claude to find and apply to jobs (or run the `/find-jobs` command).
3. Claude searches, ranks, and — for the roles you approve — drafts tailored
   materials into `applications/<company>-<role>/`.
4. Using the [claude-in-chrome](https://claude.com/chrome) browser extension, Claude
   navigates to the real application page and fills it in. It stops at the review/
   confirm screen every time and hands control back to you.
5. Once you've actually submitted (Claude asks, never assumes), it logs the
   application to the tracker, and can create calendar events for interviews
   and scan your email for status updates.
6. Check the desktop app's Listings, Applications, and Calendar tabs any time
   to see what's tracked — live views of the same Sheet/Calendar Claude reads
   and writes to, not a separate copy.
7. Claude appends a short entry to `state/session-log.md` after any real work
   — so next time (even a different day, even a different machine if you're
   syncing this repo — see "Persistence across sessions" below), running
   `/start` picks the thread back up instead of starting from nothing.

Nothing is ever submitted without you personally clicking the button.

## Persistence across sessions

Everything the tool needs to remember lives in files, not in any particular
Claude conversation — a session must be open to *do* anything (search, draft,
apply), but nothing is lost when it closes:

- **Preferences and resume** — `config/preferences.json`, `data/resume/`.
- **The tracker and listings** — a Google Sheet in your own Drive, not a
  local file, so it's already available from any device once you connect
  Google there.
- **The narrative thread** — `state/session-log.md`, read by `/start` at the
  beginning of every session.

All three are gitignored in this repo (so the public template stays free of
anyone's personal data), which means a plain `git clone` gives you the code
but not your data — that's expected for a fresh setup, but if you want your
*own* data to follow you across your own devices, see below.

### Syncing across devices (optional)

If you want your resume/preferences/session-log to follow you between your
own machines, push your own copy of this repo to a **private** GitHub repo
(never public — see "Privacy" below) and relax `.gitignore` in your copy for
the files you want synced:

```
# In your own private fork's .gitignore, remove or comment out:
config/preferences.json
data/resume/*
state/session-log.md
```

Then commit and push those files as normal, and `git pull` on your other
device before running `/start` there. **Leave `data/google/*` gitignored
everywhere, including your private repo** — that's your live OAuth client
secret and token, and credentials shouldn't ride along in git even privately;
just re-run the Google connect step once per device instead (one-time, low
friction, meaningfully safer). `config/tracker.json` (Sheet/folder IDs) is
fine to sync too since the actual tracker data lives in Drive either way.

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

This opens the dashboard in its own window (via `pywebview`), landing on a
**Get Started** tab with a checklist of the four things a fresh setup needs
(resume, preferences, Google OAuth client, Google connected) — each item
links straight to where you fix it, and it updates live as you go. Google is
optional; the checklist marks it clearly so it's obvious you can skip it. The
Setup tab itself needs no extra packages; the Connections/Applications/
Calendar tabs and the underlying Google features need a few — `pip install
-r requirements.txt` covers all of it, including `pywebview` itself. If you'd
rather skip the desktop window and just use a browser tab, `python
ui/server.py` and open `http://localhost:8787` works the same way with zero
extra packages needed for the Setup tab.

If Google isn't fully connected yet, a second, smaller window also opens
alongside the main one, pointed straight at the Connections tab, so a
first-time user isn't left hunting for it — close it any time, it won't
reappear once Google is connected.

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
2. Under "APIs & Services → OAuth consent screen", if this project's consent
   screen is new, choose **External** user type and fill in the required
   fields (app name, your email) — this puts it in **Testing** status, which
   is fine and expected. Then, under its **"Audience"** (or **"Test users"**)
   section, **add the Google account(s) you'll actually sign in with** —
   including your own, even as the project owner. Skipping this is the #1
   cause of setup failures: without it, sign-in fails with *"Access blocked:
   ... has not completed the Google verification process"* / **Error 403:
   access_denied**, because a Testing-status app only accepts accounts on
   this explicit list. (You do not need to submit the app for Google's
   verification — that's only required to move out of Testing entirely,
   which this personal-use setup never needs to do.)
3. Under "APIs & Services → Credentials", create an **OAuth client ID** of
   type **Desktop app** (or reuse an existing Desktop-app client from that
   project — a second, dedicated client is slightly cleaner since it keeps
   this tool's consent grant separate from anything else using that project,
   but either works). Download the JSON.
4. Upload that JSON file in the desktop app's Connections tab ("1. Google
   OAuth client"), or save it yourself as `data/google/client_secret.json`
   (gitignored — never commit it) — either way works, the upload button
   just saves you finding the file path.
5. `pip install -r requirements.txt`
6. `python auth/google_auth.py` (or click "Connect Google account" in the
   desktop app's Connections tab) — opens a browser for you to authorize.
   Sign in with whichever Google account you want this tool to use — that
   choice is independent of which project/client issued the request. This
   grants: Calendar (read/write your own calendar), Gmail (read-only search
   **plus draft creation** — `gmail.compose`, not `gmail.send`), Sheets
   (read/write), and Drive (read-only browsing + create-only for saving
   drafts). There is no send-email or invite-someone capability anywhere in
   this repo's code — creating a Gmail draft is as far as it goes, you
   always send it yourself — see `CLAUDE.md`.
   - If you connected before this feature existed, you'll need to run this
     step again (or click "Reconnect" in the Connections tab) — the scope
     changed, and your existing token doesn't have draft-creation access
     until you re-authorize.

**If sign-in fails with "Access blocked: ... has not completed the Google
verification process" / Error 403: access_denied** — you (or whoever's
account you're signing in with) isn't on the Test users list yet. Go back to
step 2, add that exact Google account under the OAuth consent screen's Test
users, and try again — no need to touch the client_secret.json or reinstall
anything.

**Using it**, once set up:

- The desktop app's **Connections** tab shows whether you're connected and
  has a one-click "Connect Google account" button (same underlying flow as
  step 6 above).
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

- **Will:** search multiple sources (job boards + company career pages), skip
  anything you've already applied to or passed on, rank matches against your
  resume/preferences, draft a tailored resume and cover letter per role you
  approve, autofill the real application form up to the review screen, and
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
tools/gmail_draft.py         create Gmail drafts with attachments (no send capability, ever)
tools/drive.py               import a resume from Drive; save drafts (create-only);
                              creates/finds the Job Tracker / Resumes / Cover Letters folders
applications/                drafted materials + a log of what was searched/applied to (gitignored)
state/session-log.md         narrative thread across sessions, read by /start (gitignored)
state/session-log.example.md the format/discipline, with placeholder content
.claude/commands/            /start, /find-jobs, /schedule-interview, /sync-status
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
