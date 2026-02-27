// ── CBC track/pathway data ────────────────────────────────────────────────
const CBC_PATHWAYS = {
  "STEM": ["Applied Science", "Pure Science", "Technical Studies"],
  "Social Sciences": ["Languages & Literature", "Humanities & Business Studies"],
  "Arts and Sports Science": ["Arts", "Sports"],
};

// ── Step management ───────────────────────────────────────────────────────
let currentStep = 1;

function showStep(n) {
  document.querySelectorAll(".form-step").forEach(s => s.classList.remove("active"));
  document.querySelector(`.form-step[data-step="${n}"]`).classList.add("active");

  // Update progress circles
  document.querySelectorAll(".progress-step").forEach(s => {
    const sn = parseInt(s.dataset.step);
    s.classList.remove("active", "done");
    if (sn === n) s.classList.add("active");
    else if (sn < n) s.classList.add("done");
  });

  // Update connectors
  document.querySelectorAll(".progress-connector").forEach((c, i) => {
    c.classList.toggle("done", i + 1 < n);
  });

  currentStep = n;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Step 1 → 2 ───────────────────────────────────────────────────────────
document.getElementById("step1Next").addEventListener("click", () => {
  const selected = document.querySelector('input[name="user_type"]:checked');
  if (!selected) {
    alert("Please select your education level to continue.");
    return;
  }
  buildDynamicFields(selected.value);
  showStep(2);
});

// ── Step 2 → 3 ───────────────────────────────────────────────────────────
document.getElementById("step2Next").addEventListener("click", () => {
  showStep(3);
});
document.getElementById("step2Back").addEventListener("click", () => showStep(1));
document.getElementById("step3Back").addEventListener("click", () => showStep(2));

// ── Optional fields toggle ────────────────────────────────────────────────
document.getElementById("toggleOptional").addEventListener("click", function () {
  const fields = document.getElementById("optionalFields");
  fields.classList.toggle("hidden");
  this.textContent = fields.classList.contains("hidden")
    ? "＋ Add optional details (interests & soft skills)"
    : "－ Hide optional details";
});

// ── Dynamic fields builder ────────────────────────────────────────────────
function buildDynamicFields(userType) {
  const container = document.getElementById("dynamicFields");
  const title     = document.getElementById("step2Title");
  const desc      = document.getElementById("step2Desc");

  container.innerHTML = "";

  if (userType === "cbc") {
    title.textContent = "Tell us about your CBC studies";
    desc.textContent  = "Select your track and pathway.";
    container.innerHTML = `
      <div class="fields-group">
        <div class="field">
          <label class="field-label" for="cbc_track">Track <span class="field-required">*</span></label>
          <select id="cbc_track" name="track" class="field-select" onchange="updatePathways(this.value)">
            <option value="">Select your track…</option>
            ${Object.keys(CBC_PATHWAYS).map(t => `<option value="${t}">${t}</option>`).join("")}
          </select>
        </div>
        <div class="field" id="pathwayField" style="display:none;">
          <label class="field-label" for="cbc_pathway">Pathway <span class="field-required">*</span></label>
          <select id="cbc_pathway" name="pathway" class="field-select">
            <option value="">Select your pathway…</option>
          </select>
        </div>
      </div>`;
  } else if (userType === "8-4-4") {
    title.textContent = "Tell us about your KCSE subjects";
    desc.textContent  = "Enter the subjects you studied or are currently studying.";
    container.innerHTML = `
      <div class="fields-group">
        <div class="field">
          <label class="field-label" for="subject_combination">
            Subject combination <span class="field-required">*</span>
          </label>
          <input
            type="text"
            id="subject_combination"
            name="subject_combination"
            class="field-input"
            placeholder="e.g. Mathematics, Physics, Chemistry, Biology"
          />
          <div class="field-hint">Separate subjects with commas.</div>
        </div>
      </div>`;
  } else if (userType === "graduate") {
    title.textContent = "Tell us about your degree";
    desc.textContent  = "This helps us match careers to your qualification level.";
    container.innerHTML = `
      <div class="fields-group">
        <div class="field">
          <label class="field-label" for="degree_programme">
            Degree programme <span class="field-required">*</span>
          </label>
          <input
            type="text"
            id="degree_programme"
            name="degree_programme"
            class="field-input"
            placeholder="e.g. BSc Computer Science, BA Economics, BEd Mathematics"
          />
        </div>
      </div>`;
  } else if (userType === "professional") {
    title.textContent = "Tell us about your career";
    desc.textContent  = "We'll use this to find transition and growth opportunities.";
    container.innerHTML = `
      <div class="fields-group">
        <div class="field">
          <label class="field-label" for="industry">
            Current industry <span class="field-required">*</span>
          </label>
          <input
            type="text"
            id="industry"
            name="industry"
            class="field-input"
            placeholder="e.g. Finance, Healthcare, ICT, Education, Telecommunications"
          />
        </div>
        <div class="field">
          <label class="field-label" for="major">
            Specialisation / Role
          </label>
          <input
            type="text"
            id="major"
            name="major"
            class="field-input"
            placeholder="e.g. Software Engineer, Accountant, Nurse, Project Manager"
          />
        </div>
      </div>`;
  }
}

// ── CBC pathway updater ───────────────────────────────────────────────────
function updatePathways(track) {
  const pf  = document.getElementById("pathwayField");
  const sel = document.getElementById("cbc_pathway");
  if (!track) { pf.style.display = "none"; return; }
  pf.style.display = "block";
  sel.innerHTML = `<option value="">Select your pathway…</option>` +
    (CBC_PATHWAYS[track] || []).map(p => `<option value="${p}">${p}</option>`).join("");
}

// ── Collect form data ─────────────────────────────────────────────────────
function collectFormData() {
  const form = document.getElementById("careerForm");
  const fd   = new FormData(form);
  const data = {};
  for (const [k, v] of fd.entries()) {
    data[k] = v;
  }

  // Merge text fields not in FormData correctly
  ["skills", "career_goals", "interests", "soft_skills"].forEach(id => {
    const el = document.getElementById(id);
    if (el) data[id] = el.value;
  });

  return {
    user_type:           data.user_type || "graduate",
    skills:              data.skills || "",
    career_goals:        data.career_goals || "",
    interests:           data.interests || "",
    soft_skills:         data.soft_skills || "",
    // CBC
    track:               data.track || undefined,
    pathway:             data.pathway || undefined,
    // 8-4-4
    subject_combination: data.subject_combination || undefined,
    // Graduate
    degree_programme:    data.degree_programme || undefined,
    // Professional
    industry:            data.industry || undefined,
    major:               data.major || undefined,
    // Recommendation settings
    n_recommendations:   5,
    courses_per_gap:     2,
  };
}

// ── Form submission ───────────────────────────────────────────────────────
document.getElementById("careerForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const errorEl  = document.getElementById("formError");
  const submitBtn = document.getElementById("submitBtn");
  const submitText = document.getElementById("submitText");
  const spinner   = document.getElementById("submitSpinner");

  // Validate
  const skills = document.getElementById("skills").value.trim();
  const goals  = document.getElementById("career_goals").value.trim();
  if (!skills && !goals) {
    errorEl.textContent = "Please enter at least your skills or career goals.";
    errorEl.classList.remove("hidden");
    return;
  }
  errorEl.classList.add("hidden");

  // Loading state
  submitText.classList.add("hidden");
  spinner.classList.remove("hidden");
  submitBtn.disabled = true;

  const payload = collectFormData();

  try {
    const result = await apiFetch(API.recommend(), {
      method: "POST",
      body: JSON.stringify(payload),
    });

    // Save to sessionStorage and navigate to results
    sessionStorage.setItem("careerResults", JSON.stringify(result));
    sessionStorage.setItem("careerPayload",  JSON.stringify(payload));
    window.location.href = "results.html";

  } catch (err) {
    errorEl.textContent = `Something went wrong: ${err.message}. Make sure the API server is running.`;
    errorEl.classList.remove("hidden");
    submitText.classList.remove("hidden");
    spinner.classList.add("hidden");
    submitBtn.disabled = false;
  }
});
