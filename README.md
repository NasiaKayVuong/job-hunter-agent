# Job Hunter Agent

A starter kit for running your job search through [Claude Code](https://claude.com/claude-code):
search job boards and company career pages, filter listings against your resume and
your stated preferences, draft a tailored resume/cover letter per role, and fill out
the actual application on the original site (job board or, where possible, the
company's own careers page) up to the review screen — **it never clicks the final
Submit/Apply button for you.** You always review and submit yourself.

## How it works

1. You set your preferences and upload your resume through a small local web UI.
2. You open this folder in Claude Code and ask it to find and apply to jobs (or run
   the `/find-jobs` command).
3. Claude searches, ranks, and — for the roles you approve — drafts tailored
   materials into `applications/<company>-<role>/`.
4. Using the [claude-in-chrome](https://claude.com/chrome) browser extension, Claude
   navigates to the real application page and fills it in. It stops at the review/
   confirm screen every time and hands control back to you.

Nothing is ever submitted without you personally clicking the button.

## Setup

**Requirements:** Python 3.9+ (used only for the local preferences/resume UI — no
extra packages needed), Claude Code, and the [claude-in-chrome](https://claude.com/chrome)
browser extension connected to Claude Code if you want the autofill step (search and
drafting work without it).

```
git clone <this-repo-url>
cd job-hunter-agent
python ui/server.py
```

Open `http://localhost:8787` in your browser. Upload your resume (PDF or DOCX) and
fill in your preferences — target role/level, locations, comp floor, industries to
include/exclude, employment type, and any dealbreakers. Click Save. This writes:

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

## What Claude will and won't do on its own

- **Will:** search multiple sources (job boards + company career pages), rank matches
  against your resume/preferences, draft a tailored resume and cover letter per role
  you approve, and autofill the real application form up to the review screen.
- **Won't:** click Submit/Apply, create accounts on your behalf, or send anything
  without showing you first. Every autofilled application is left open for your
  own review and submission.
- Read `CLAUDE.md` for the exact operating rules Claude follows in this repo.

## Repo layout

```
config/preferences.json      your saved preferences (gitignored)
config/preferences.example.json   the schema/template, with placeholder values
data/resume/                 your uploaded resume (gitignored)
ui/                          the local preferences/resume UI (server.py + static files)
applications/                drafted materials + a log of what was searched/applied to (gitignored)
.claude/commands/find-jobs.md   the /find-jobs slash command
CLAUDE.md                    operating rules for Claude in this repo
```

## Privacy

Your resume and preferences live only on your machine (`data/` and
`config/preferences.json` are gitignored). Job search and drafting use Claude's
normal tools; the autofill step uses your own logged-in browser session via
claude-in-chrome — no separate account or credential is stored by this repo.
