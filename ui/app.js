const $ = (id) => document.getElementById(id);
const statusEl = $("status");

function showStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = "status " + kind;
  statusEl.hidden = false;
}

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
  const loc = prefs.locations || {};
  $("remote").checked = !!loc.remote;
  $("hybrid_areas").value = (loc.hybrid_or_onsite_areas || []).join(", ");
  $("relocation").checked = !!loc.open_to_relocation;
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
    locations: {
      remote: $("remote").checked,
      hybrid_or_onsite_areas: splitList($("hybrid_areas").value),
      open_to_relocation: $("relocation").checked,
    },
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

  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    showStatus("Saved. Ask Claude to find jobs whenever you're ready.", "ok");
    await loadExisting();
    fileInput.value = "";
  } catch (err) {
    showStatus("Failed to save: " + err.message, "err");
  }
});

// ---------- Tabs ----------

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = true));
    btn.classList.add("active");
    $("panel-" + btn.dataset.tab).hidden = false;
    if (btn.dataset.tab === "connections") loadGoogleStatus();
    if (btn.dataset.tab === "applications") loadApplications();
    if (btn.dataset.tab === "calendar") loadCalendar();
  });
});

// ---------- Connections ----------

async function loadGoogleStatus() {
  const el = $("google-status");
  const btn = $("google-connect-btn");
  el.textContent = "Checking…";
  try {
    const res = await fetch("/api/google/status");
    const data = await res.json();
    if (!data.installed) {
      el.textContent = "Not installed. Run: pip install -r requirements.txt";
      btn.disabled = true;
    } else if (!data.client_secret_present) {
      el.textContent = "No OAuth client set up yet. See README.md → Calendar and tracking.";
      btn.textContent = "Connect Google account";
      btn.disabled = false;
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

// ---------- Applications ----------

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
        r.location, r.job_type, r.skill_match, r.current_stage,
      ];
      for (const c of cells) {
        const td = document.createElement("td");
        td.textContent = c || "";
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
  } catch (e) {
    empty.textContent = "Couldn't load applications: " + e.message;
    empty.hidden = false;
  }
}

$("refresh-applications-btn").addEventListener("click", loadApplications);

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
