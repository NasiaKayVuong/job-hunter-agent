const $ = (id) => document.getElementById(id);
const statusEl = $("status");

function showStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = "status " + kind;
  statusEl.hidden = false;
}

// ---------- Wide/compact layout toggle ----------

function applyWidthMode(wide) {
  document.querySelector(".app").classList.toggle("wide", wide);
  $("toggle-width-btn").textContent = wide ? "⤡ Compact view" : "⤢ Expand view";
}

(function initWidthMode() {
  let wide = false;
  try {
    wide = localStorage.getItem("jha-wide-view") === "1";
  } catch (e) {
    // localStorage unavailable — default to compact, no big deal.
  }
  applyWidthMode(wide);
})();

$("toggle-width-btn").addEventListener("click", () => {
  const nowWide = !document.querySelector(".app").classList.contains("wide");
  applyWidthMode(nowWide);
  try {
    localStorage.setItem("jha-wide-view", nowWide ? "1" : "0");
  } catch (e) {
    // Fine if this doesn't persist — it still works for the current session.
  }
});

// ---------- Light/dark theme toggle ----------
// Defaults to following the OS/browser preference (no attribute set); once
// toggled, pins an explicit choice (data-theme="light"|"dark") that wins
// over the system preference, persisted across reloads.

function applyThemeMode(theme) {
  if (theme) {
    document.documentElement.setAttribute("data-theme", theme);
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  const isDark = theme ? theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  $("toggle-theme-btn").textContent = isDark ? "☀️ Light" : "🌙 Dark";
}

(function initThemeMode() {
  let theme = null;
  try {
    theme = localStorage.getItem("jha-theme"); // "light" | "dark" | null (follow system)
  } catch (e) {
    // localStorage unavailable — just follow the system preference.
  }
  applyThemeMode(theme);
})();

$("toggle-theme-btn").addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  const currentIsDark = current ? current === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  const next = currentIsDark ? "light" : "dark";
  applyThemeMode(next);
  try {
    localStorage.setItem("jha-theme", next);
  } catch (e) {
    // Fine if this doesn't persist — it still works for the current session.
  }
});

function splitList(value) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function splitLines(value) {
  return value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

function fillForm(prefs) {
  if (!prefs) return;
  $("target_titles").value = (prefs.target_titles || []).join(", ");
  $("seniority").value = prefs.seniority || "";
  if (prefs.experience_years_tolerance != null) {
    $("experience_years_tolerance").value = prefs.experience_years_tolerance;
  }
  const loc = prefs.locations || {};
  $("remote").checked = !!loc.remote;
  $("hybrid_areas").value = (loc.hybrid_or_onsite_areas || []).join(", ");
  $("relocation").checked = !!loc.open_to_relocation;
  $("work_authorization").value = prefs.work_authorization || "";
  const comp = prefs.compensation || {};
  if (comp.floor != null) $("comp_floor").value = comp.floor;
  if (comp.flexible_down_to != null) $("comp_flex").value = comp.flexible_down_to;
  const et = prefs.employment_type || [];
  $("et_full_time").checked = et.includes("full_time");
  $("et_contract").checked = et.includes("contract");
  $("et_part_time").checked = et.includes("part_time");
  $("industries_excluded").value = (prefs.industries_excluded || []).join(", ");
  $("industries_preferred").value = (prefs.industries_preferred || []).join(", ");
  $("dealbreakers").value = (prefs.dealbreakers || []).join("\n");
  const src = prefs.sources || {};
  $("src_boards").checked = src.job_boards !== false;
  $("src_company").checked = src.company_career_pages !== false;
  $("niche_boards").value = (src.niche_boards || []).join(", ");
  $("company_watchlist").value = (src.company_watchlist || []).join(", ");
  $("notes").value = prefs.notes || "";
}

async function loadExisting() {
  try {
    const res = await fetch("/api/preferences");
    if (res.ok) {
      const data = await res.json();
      fillForm(data.preferences);
      if (data.resume_filename) {
        $("resume-current").textContent = "Current resume on file: " + data.resume_filename;
      } else {
        $("resume-current").textContent = "No resume uploaded yet.";
      }
    }
  } catch (e) {
    // First run, nothing saved yet — fine.
  }
}

function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function buildPreferences() {
  return {
    target_titles: splitList($("target_titles").value),
    seniority: $("seniority").value.trim(),
    experience_years_tolerance: $("experience_years_tolerance").value
      ? Number($("experience_years_tolerance").value)
      : 3,
    locations: {
      remote: $("remote").checked,
      hybrid_or_onsite_areas: splitList($("hybrid_areas").value),
      open_to_relocation: $("relocation").checked,
    },
    work_authorization: $("work_authorization").value,
    compensation: {
      currency: "USD",
      floor: $("comp_floor").value ? Number($("comp_floor").value) : null,
      flexible_down_to: $("comp_flex").value ? Number($("comp_flex").value) : null,
      basis: "base salary",
    },
    employment_type: [
      $("et_full_time").checked ? "full_time" : null,
      $("et_contract").checked ? "contract" : null,
      $("et_part_time").checked ? "part_time" : null,
    ].filter(Boolean),
    industries_excluded: splitList($("industries_excluded").value),
    industries_preferred: splitList($("industries_preferred").value),
    dealbreakers: splitLines($("dealbreakers").value),
    sources: {
      job_boards: $("src_boards").checked,
      company_career_pages: $("src_company").checked,
      niche_boards: splitList($("niche_boards").value),
      company_watchlist: splitList($("company_watchlist").value),
    },
    notes: $("notes").value.trim(),
  };
}

$("setup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = { preferences: buildPreferences() };

  const fileInput = $("resume");
  if (fileInput.files && fileInput.files[0]) {
    const file = fileInput.files[0];
    const dataUrl = await readFileAsDataURL(file);
    payload.resume = {
      filename: file.name,
      data_base64: dataUrl.split(",")[1],
    };
  }

  const saveStatusEl = $("save-status");
  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    showStatus("Saved. Ask Claude to find jobs whenever you're ready.", "ok");
    saveStatusEl.textContent = "✓ Saved";
    saveStatusEl.className = "status-line ok-text";
    saveStatusEl.hidden = false;
    await loadExisting();
    fileInput.value = "";
  } catch (err) {
    showStatus("Failed to save: " + err.message, "err");
    saveStatusEl.textContent = "✗ Failed to save: " + err.message;
    saveStatusEl.className = "status-line err-text";
    saveStatusEl.hidden = false;
  }
});

// ---------- Tabs ----------

function switchTab(tabName) {
  const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
  if (!btn) return;
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = true));
  btn.classList.add("active");
  $("panel-" + tabName).hidden = false;
  if (tabName === "getting-started") loadGettingStarted();
  if (tabName === "connections") loadGoogleStatus();
  if (tabName === "listings") loadListings();
  if (tabName === "applications") loadApplications();
  if (tabName === "calendar") loadCalendar();
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

document.querySelectorAll(".gs-jump").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// A guide window (opened by app.py) may load with ?tab=connections etc.
// to land directly on the right tab instead of Get Started.
(function initialTabFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("tab");
  if (requested && document.querySelector(`.tab-btn[data-tab="${requested}"]`)) {
    switchTab(requested);
  } else {
    loadGettingStarted();
  }
})();

// ---------- Connections ----------

async function fetchGoogleStatus() {
  const res = await fetch("/api/google/status");
  return res.json();
}

async function loadGoogleStatus() {
  const secretEl = $("client-secret-status");
  const el = $("google-status");
  const btn = $("google-connect-btn");
  secretEl.textContent = "Checking…";
  el.textContent = "Checking…";
  try {
    const data = await fetchGoogleStatus();
    if (!data.installed) {
      secretEl.textContent = "Google packages not installed. Run: pip install -r requirements.txt";
      el.textContent = "—";
      btn.disabled = true;
      return;
    }
    secretEl.textContent = data.client_secret_present
      ? "✓ Client secret on file"
      : "Not uploaded yet — see steps above.";
    if (!data.client_secret_present) {
      el.textContent = "Upload a client secret first (step 1 above).";
      btn.textContent = "Connect Google account";
      btn.disabled = true;
    } else if (data.connected) {
      el.textContent = "✓ Connected";
      btn.textContent = "Reconnect";
      btn.disabled = false;
    } else {
      el.textContent = "Client set up, not yet authorized.";
      btn.textContent = "Connect Google account";
      btn.disabled = false;
    }
  } catch (e) {
    el.textContent = "Couldn't check status: " + e.message;
  }
}

$("google-connect-btn").addEventListener("click", async () => {
  const btn = $("google-connect-btn");
  btn.disabled = true;
  btn.textContent = "Waiting on browser authorization…";
  try {
    const res = await fetch("/api/google/connect", { method: "POST" });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    showStatus("Google account connected.", "ok");
  } catch (e) {
    showStatus("Connection failed: " + e.message, "err");
  } finally {
    btn.disabled = false;
    await loadGoogleStatus();
  }
});

$("upload-client-secret-btn").addEventListener("click", async () => {
  const fileInput = $("client-secret-file");
  const btn = $("upload-client-secret-btn");
  if (!fileInput.files || !fileInput.files[0]) {
    showStatus("Choose a client_secret.json file first.", "err");
    return;
  }
  btn.disabled = true;
  try {
    const dataUrl = await readFileAsDataURL(fileInput.files[0]);
    const res = await fetch("/api/google/client-secret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data_base64: dataUrl.split(",")[1] }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    showStatus("Client secret saved.", "ok");
    fileInput.value = "";
    await loadGoogleStatus();
  } catch (e) {
    showStatus("Upload failed: " + e.message, "err");
  } finally {
    btn.disabled = false;
  }
});

// ---------- Get Started ----------

function setChecklistItem(id, ok, detail) {
  const li = $(id);
  const mark = li.querySelector(".checklist-mark");
  const detailEl = li.querySelector(".checklist-detail");
  mark.textContent = ok ? "✓" : "○";
  mark.className = "checklist-mark " + (ok ? "ok-text" : "");
  detailEl.textContent = detail || "";
  return ok;
}

async function loadGettingStarted() {
  $("gs-summary").textContent = "Checking…";
  try {
    const [prefsRes, googleData] = await Promise.all([
      fetch("/api/preferences").then((r) => r.json()),
      fetchGoogleStatus().catch(() => ({ installed: false, client_secret_present: false, connected: false })),
    ]);

    const hasResume = !!prefsRes.resume_filename;
    const prefs = prefsRes.preferences;
    const hasPrefs = !!(prefs && prefs.target_titles && prefs.target_titles.length);

    let done = 0;
    if (setChecklistItem("gs-resume", hasResume, hasResume ? prefsRes.resume_filename : "No resume on file yet.")) done++;
    if (setChecklistItem("gs-preferences", hasPrefs, hasPrefs ? "Target: " + prefs.target_titles.join(", ") : "Not filled in yet.")) done++;
    if (setChecklistItem("gs-client-secret", !!googleData.client_secret_present, googleData.client_secret_present ? "Uploaded." : "Optional — needed for Calendar/Gmail/Sheets/Drive features.")) done++;
    if (setChecklistItem("gs-connected", !!googleData.connected, googleData.connected ? "Connected." : "Not connected yet.")) done++;

    const required = hasResume && hasPrefs;
    $("gs-summary").textContent = required
      ? "✓ Core setup complete — you're ready to search for jobs through Claude. Google features are optional."
      : `${done} of 4 steps complete.`;
  } catch (e) {
    $("gs-summary").textContent = "Couldn't check status: " + e.message;
  }
}

// ---------- Applications ----------

const STAGE_OPTIONS = [
  "Applied", "Phone Screen", "Technical", "Onsite", "Offer", "Rejected", "Withdrawn",
];

function stageSelect(row, currentStage) {
  const select = document.createElement("select");
  const options = STAGE_OPTIONS.includes(currentStage) || !currentStage
    ? STAGE_OPTIONS
    : [currentStage, ...STAGE_OPTIONS];
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if (opt === currentStage) o.selected = true;
    select.appendChild(o);
  }
  select.addEventListener("change", async () => {
    select.disabled = true;
    try {
      const res = await fetch("/api/applications/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row, stage: select.value }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      showStatus(`Updated to "${select.value}".`, "ok");
    } catch (e) {
      showStatus("Couldn't update stage: " + e.message, "err");
    } finally {
      select.disabled = false;
    }
  });
  return select;
}

async function loadApplications() {
  const tbody = document.querySelector("#applications-table tbody");
  const empty = $("applications-empty");
  tbody.innerHTML = "";
  empty.hidden = true;
  try {
    const res = await fetch("/api/applications");
    const data = await res.json();
    if (data.error) {
      empty.textContent = data.error;
      empty.hidden = false;
      return;
    }
    const rows = data.applications || [];
    if (rows.length === 0) {
      empty.hidden = false;
      return;
    }
    for (const r of rows) {
      const tr = document.createElement("tr");
      const cells = [
        r.date_applied, r.company, r.title, r.source,
        r.location, r.job_type, r.skill_match,
      ];
      for (const c of cells) {
        const td = document.createElement("td");
        td.textContent = c || "";
        tr.appendChild(td);
      }
      const stageTd = document.createElement("td");
      stageTd.appendChild(stageSelect(r.row, r.current_stage));
      tr.appendChild(stageTd);
      const linkTd = document.createElement("td");
      if (r.job_url) {
        const a = document.createElement("a");
        a.href = r.job_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Open";
        linkTd.appendChild(a);
      }
      tr.appendChild(linkTd);
      tbody.appendChild(tr);
    }
  } catch (e) {
    empty.textContent = "Couldn't load applications: " + e.message;
    empty.hidden = false;
  }
}

$("refresh-applications-btn").addEventListener("click", loadApplications);

// ---------- Email status scan (read-only) ----------

$("scan-email-btn").addEventListener("click", async () => {
  const btn = $("scan-email-btn");
  const list = $("email-scan-list");
  const empty = $("email-scan-empty");
  list.innerHTML = "";
  empty.hidden = true;
  btn.disabled = true;
  btn.textContent = "Scanning…";
  try {
    const days = $("scan-days-select").value;
    const res = await fetch("/api/gmail/scan?days=" + encodeURIComponent(days));
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    const candidates = data.candidates || [];
    if (candidates.length === 0) {
      empty.textContent = `Nothing found in the last ${days} days.`;
      empty.hidden = false;
      return;
    }
    for (const c of candidates) {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${c.subject || "(no subject)"}</strong><br>
        <span class="hint">${c.from} — ${c.date}</span><br>
        <span class="hint">${c.snippet}</span><br>
        <em>Guess: ${c.guessed_status}</em>`;
      list.appendChild(li);
    }
  } catch (e) {
    empty.textContent = "Couldn't scan email: " + e.message;
    empty.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Scan email for updates";
  }
});

// ---------- Listings ----------

const LISTING_STATUS_OPTIONS = ["New", "Interested", "Passed", "Applied"];

function listingStatusSelect(row, currentStatus) {
  const select = document.createElement("select");
  for (const opt of LISTING_STATUS_OPTIONS) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if (opt === currentStatus) o.selected = true;
    select.appendChild(o);
  }
  select.addEventListener("change", async () => {
    select.disabled = true;
    try {
      const res = await fetch("/api/listings/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row, status: select.value }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      showStatus(`Marked "${select.value}".`, "ok");
    } catch (e) {
      showStatus("Couldn't update status: " + e.message, "err");
    } finally {
      select.disabled = false;
    }
  });
  return select;
}

async function loadListings() {
  const tbody = document.querySelector("#listings-table tbody");
  const empty = $("listings-empty");
  tbody.innerHTML = "";
  empty.hidden = true;
  try {
    const res = await fetch("/api/listings");
    const data = await res.json();
    if (data.error) {
      empty.textContent = data.error;
      empty.hidden = false;
      return;
    }
    const rows = data.listings || [];
    if (rows.length === 0) {
      empty.hidden = false;
      return;
    }
    for (const r of rows) {
      const tr = document.createElement("tr");
      const cells = [r.date_found, r.company, r.title, r.location, r.job_type, r.comp_range, r.source, r.match_notes];
      for (const c of cells) {
        const td = document.createElement("td");
        td.textContent = c || "";
        tr.appendChild(td);
      }
      const statusTd = document.createElement("td");
      statusTd.appendChild(listingStatusSelect(r.row, r.status));
      tr.appendChild(statusTd);
      const linkTd = document.createElement("td");
      if (r.url) {
        const a = document.createElement("a");
        a.href = r.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Open";
        linkTd.appendChild(a);
      }
      tr.appendChild(linkTd);
      tbody.appendChild(tr);
    }
  } catch (e) {
    empty.textContent = "Couldn't load listings: " + e.message;
    empty.hidden = false;
  }
}

$("refresh-listings-btn").addEventListener("click", loadListings);

// ---------- Calendar ----------

async function loadCalendar() {
  const list = $("calendar-list");
  const empty = $("calendar-empty");
  list.innerHTML = "";
  empty.hidden = true;
  try {
    const res = await fetch("/api/calendar/upcoming");
    const data = await res.json();
    if (data.error) {
      empty.textContent = data.error;
      empty.hidden = false;
      return;
    }
    const events = data.events || [];
    if (events.length === 0) {
      empty.hidden = false;
      return;
    }
    for (const ev of events) {
      const li = document.createElement("li");
      const when = new Date(ev.start).toLocaleString();
      li.innerHTML = `<strong>${ev.summary || "(no title)"}</strong><br><span class="hint">${when}</span>`;
      if (ev.html_link) {
        const a = document.createElement("a");
        a.href = ev.html_link;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = " Open in Calendar";
        li.appendChild(a);
      }
      list.appendChild(li);
    }
  } catch (e) {
    empty.textContent = "Couldn't load calendar: " + e.message;
    empty.hidden = false;
  }
}

$("refresh-calendar-btn").addEventListener("click", loadCalendar);

// ---------- Drive resume import ----------

$("import-drive-btn").addEventListener("click", async () => {
  const picker = $("drive-picker");
  const list = $("drive-picker-list");
  picker.hidden = false;
  list.innerHTML = "<li>Searching Drive…</li>";
  try {
    const res = await fetch("/api/drive/resumes");
    const data = await res.json();
    if (data.error) {
      list.innerHTML = `<li>${data.error}</li>`;
      return;
    }
    const files = data.files || [];
    if (files.length === 0) {
      list.innerHTML = "<li>No resume-like files found in Drive.</li>";
      return;
    }
    list.innerHTML = "";
    for (const f of files) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "secondary";
      btn.textContent = `${f.name} (${new Date(f.modifiedTime).toLocaleDateString()})`;
      btn.addEventListener("click", () => importDriveResume(f.id));
      li.appendChild(btn);
      list.appendChild(li);
    }
  } catch (e) {
    list.innerHTML = `<li>Couldn't search Drive: ${e.message}</li>`;
  }
});

async function importDriveResume(fileId) {
  try {
    const res = await fetch("/api/drive/import-resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: fileId }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    showStatus(`Imported "${data.saved_as}" from Drive.`, "ok");
    $("drive-picker").hidden = true;
    await loadExisting();
  } catch (e) {
    showStatus("Import failed: " + e.message, "err");
  }
}

loadExisting();
