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
    showStatus("Saved. You can close this tab and open the folder in Claude Code.", "ok");
    await loadExisting();
    fileInput.value = "";
  } catch (err) {
    showStatus("Failed to save: " + err.message, "err");
  }
});

loadExisting();
