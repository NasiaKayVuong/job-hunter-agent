---
description: Search for jobs matching your resume/preferences, shortlist them, then draft and autofill applications you approve.
---

Follow the workflow in `CLAUDE.md` end to end:

1. Read `config/preferences.json` and the resume in `data/resume/`. If either is
   missing, tell the user to run `python ui/server.py` and set them up first.
2. Search job boards and company career pages per the preferences' `sources`
   settings. Filter out anything hitting an excluded industry or a dealbreaker.
3. Present a ranked shortlist (company, role, comp, location, link, why it
   matched) and wait for the user to say which ones to pursue.
4. For each approved job, draft a tailored resume and cover letter into
   `applications/<company>-<role-slug>/`.
5. Use claude-in-chrome to autofill the real application on its original site,
   stopping at the review screen — never click Submit/Apply.
6. Log everything to `applications/log.md`.
