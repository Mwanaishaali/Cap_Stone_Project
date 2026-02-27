// ── Load results from sessionStorage ─────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const raw = sessionStorage.getItem("careerResults");
  const payloadRaw = sessionStorage.getItem("careerPayload");

  if (!raw) {
    showError("No results found. Please go back and fill in the form.");
    return;
  }

  try {
    const data    = JSON.parse(raw);
    const payload = payloadRaw ? JSON.parse(payloadRaw) : {};
    renderResults(data, payload);
  } catch (e) {
    showError("Failed to load results: " + e.message);
  }
});

function showError(msg) {
  document.getElementById("loadingState").classList.add("hidden");
  document.getElementById("errorState").classList.remove("hidden");
  document.getElementById("errorMsg").textContent = msg;
}

// ── Main render ───────────────────────────────────────────────────────────
function renderResults(data, payload) {
  document.getElementById("loadingState").classList.add("hidden");
  document.getElementById("resultsContent").classList.remove("hidden");

  const details = data.career_details || [];
  const recs    = data.recommendations || [];

  // Subtitle
  const userLabel = {
    "cbc": "CBC Student", "8-4-4": "8-4-4 Student",
    "graduate": "Graduate", "professional": "Professional",
  };
  document.getElementById("resultsSub").textContent =
    `Based on your profile as a ${userLabel[payload.user_type] || "user"} · ${details.length} careers matched · Analysed in ${data.pipeline_ms || 0}ms`;

  // Summary row
  renderSummaryRow(details, data);

  // Career cards
  const list = document.getElementById("careersList");
  list.innerHTML = "";
  details.forEach((d, i) => {
    list.appendChild(buildCareerCard(d, i));
  });
}

// ── Summary row ───────────────────────────────────────────────────────────
function renderSummaryRow(details, data) {
  const row = document.getElementById("summaryRow");
  if (!details.length) return;

  const top       = details[0];
  const avgMatch  = Math.round(details.reduce((s, d) => s + d.career_info.match_score, 0) / details.length);
  const lowRisk   = details.filter(d => ["Low", "Medium"].includes(d.risk_profile.ai_risk_label)).length;
  const topMatch  = Math.round(top.career_info.match_score);

  row.innerHTML = `
    <div class="summary-card">
      <div class="summary-card-label">Top Match</div>
      <div class="summary-card-value">${topMatch}%</div>
      <div class="summary-card-sub">${top.career_info.title}</div>
    </div>
    <div class="summary-card">
      <div class="summary-card-label">Avg Match Score</div>
      <div class="summary-card-value">${avgMatch}%</div>
      <div class="summary-card-sub">Across all ${details.length} careers</div>
    </div>
    <div class="summary-card">
      <div class="summary-card-label">Future-Proof Careers</div>
      <div class="summary-card-value">${lowRisk} of ${details.length}</div>
      <div class="summary-card-sub">Low or Medium AI risk</div>
    </div>
    <div class="summary-card">
      <div class="summary-card-label">Analysis Time</div>
      <div class="summary-card-value">${data.pipeline_ms || "—"}ms</div>
      <div class="summary-card-sub">894 occupations scanned</div>
    </div>
  `;
}

// ── Career card builder ───────────────────────────────────────────────────
function buildCareerCard(d, index) {
  const ci   = d.career_info;
  const risk = d.risk_profile;
  const gap  = d.gap_report;
  const path = d.learning_path;

  const card = document.createElement("div");
  card.className = "career-card";
  card.setAttribute("data-index", index);

  const matchScore  = Math.round(ci.match_score || 70);
  const circumference = 2 * Math.PI * 24;
  const dashOffset    = circumference * (1 - matchScore / 100);
  const strokeColor   = matchColor(matchScore);
  const rankClass     = index === 0 ? "rank-1" : index === 1 ? "rank-2" : index === 2 ? "rank-3" : "";

  card.innerHTML = `
    <!-- Header -->
    <div class="career-card-header" onclick="toggleCard(this)">
      <div class="career-rank ${rankClass}">${d.rank}</div>
      <div class="career-main">
        <div class="career-family">${ci.career_family || ""}</div>
        <div class="career-name">${ci.title}</div>
        <div class="career-badges">
          ${riskBadge(risk.ai_risk_label)}
          ${demandBadge(ci.demand_level)}
          <span class="badge" style="background:#f0fdf4;color:#15803d;">🎓 ${ci.min_education || ""}</span>
        </div>
      </div>
      <div class="career-score">
        <div class="score-ring">
          <svg viewBox="0 0 60 60">
            <circle class="score-ring-bg" cx="30" cy="30" r="24"/>
            <circle class="score-ring-fill"
              cx="30" cy="30" r="24"
              stroke="${strokeColor}"
              stroke-dasharray="${circumference}"
              stroke-dashoffset="${dashOffset}"/>
          </svg>
          <div class="score-ring-text">${matchScore}%</div>
        </div>
        <div class="score-label">Match</div>
      </div>
      <div class="career-chevron">▾</div>
    </div>

    <!-- Body -->
    <div class="career-card-body">
      <div class="career-tabs">
        <button class="career-tab active" data-target="overview-${index}" onclick="switchTab(this)">Overview</button>
        <button class="career-tab" data-target="gap-${index}" onclick="switchTab(this)">Skills Gap</button>
        <button class="career-tab" data-target="path-${index}" onclick="switchTab(this)">Learning Path</button>
      </div>
      <div class="career-tab-content">
        ${buildOverviewPanel(ci, risk, index)}
        ${buildGapPanel(gap, index)}
        ${buildPathPanel(path, index)}
      </div>
    </div>
  `;

  return card;
}

// ── Overview panel ────────────────────────────────────────────────────────
function buildOverviewPanel(ci, risk, idx) {
  const wage = ci.median_wage
    ? `$${Math.round(ci.median_wage / 1000)}k/yr`
    : "N/A";

  return `
    <div id="overview-${idx}" class="tab-panel active">
      <div class="overview-grid">
        <div class="overview-stat">
          <div class="overview-stat-label">Median Wage</div>
          <div class="overview-stat-value">${wage}</div>
        </div>
        <div class="overview-stat">
          <div class="overview-stat-label">Future-Proof Score</div>
          <div class="overview-stat-value">${Math.round(risk.future_proof_score)}/100</div>
        </div>
        <div class="overview-stat">
          <div class="overview-stat-label">AI Risk Score</div>
          <div class="overview-stat-value">${risk.ai_risk_score}%</div>
        </div>
      </div>
      <div class="risk-explanation-box">
        <strong>AI Risk — ${risk.ai_risk_label}:</strong> ${risk.risk_explanation}
      </div>
      <div class="gap-section-title">What you can do to stay ahead</div>
      <ul class="mitigation-list">
        ${risk.mitigation_advice.map(a => `<li>${a}</li>`).join("")}
      </ul>
    </div>
  `;
}

// ── Skills gap panel ──────────────────────────────────────────────────────
function buildGapPanel(gap, idx) {
  if (!gap) return `<div id="gap-${idx}" class="tab-panel"><p class="text-muted">No gap data available.</p></div>`;

  const alignPct    = Math.round(gap.alignment_pct || 0);
  const alignColor  = alignPct >= 75 ? "#10b981" : alignPct >= 50 ? "#f59e0b" : "#ef4444";
  const alignLabel  = alignPct >= 75 ? "Strong match" : alignPct >= 50 ? "Good foundation" : "Needs development";

  const gapRows = (gap.top_gaps || []).slice(0, 8).map(g => buildSkillRow(g, "gap")).join("");
  const strRows = (gap.top_strengths || []).slice(0, 5).map(g => buildSkillRow(g, "strength")).join("");

  return `
    <div id="gap-${idx}" class="tab-panel">
      <div class="alignment-header">
        <div class="alignment-score" style="color:${alignColor}">${alignPct}%</div>
        <div>
          <div class="alignment-label">${alignLabel}</div>
          <div class="alignment-sub">Skill alignment with ${gap.occupation}</div>
        </div>
      </div>

      ${gapRows ? `
        <div class="gap-section-title">Skills to develop (prioritised by importance)</div>
        ${gapRows}
      ` : ""}

      ${strRows ? `
        <div class="gap-section-title">Your existing strengths</div>
        ${strRows}
      ` : ""}
    </div>
  `;
}

function buildSkillRow(g, type) {
  const req     = Math.round((g.required / 7) * 100);
  const cur     = Math.round((g.current  / 7) * 100);
  const isGap   = g.gap > 0;
  const fillCls = type === "strength" ? "match" : (g.gap > 2 ? "gap" : "close");

  return `
    <div class="skill-row">
      <div class="skill-row-name">${g.dimension}</div>
      <div class="skill-row-bar">
        <div class="skill-row-required" style="width:${req}%"></div>
        <div class="skill-row-current ${fillCls}" style="width:${Math.min(cur, req)}%"></div>
      </div>
      <div class="skill-row-score">${g.current.toFixed(1)} / ${g.required.toFixed(1)}</div>
    </div>
  `;
}

// ── Learning path panel ───────────────────────────────────────────────────
function buildPathPanel(path, idx) {
  if (!path || !path.stages.length) {
    return `<div id="path-${idx}" class="tab-panel"><p class="text-muted">No learning path data available.</p></div>`;
  }

  const stages = path.stages.map(s => {
    const courses = s.courses.map(c => `
      <div class="course-card">
        <div class="course-platform">${c.platform}</div>
        <div class="course-title">${c.course_title}</div>
        <div class="course-meta">
          <span class="course-tag">${c.level}</span>
          ${c.is_free ? '<span class="course-tag free">Free</span>' : ""}
          ${c.duration_hours ? `<span class="course-tag">⏱ ${c.duration_hours}h</span>` : ""}
          ${c.skill_match_pct ? `<span class="course-tag">${c.skill_match_pct}% match</span>` : ""}
        </div>
        ${c.url && c.url !== "nan" && c.url !== "None"
          ? `<a class="course-link" href="${c.url}" target="_blank" rel="noopener">Enrol now →</a>`
          : ""}
      </div>
    `).join("");

    return `
      <div class="path-stage">
        <div class="path-stage-header">
          <span class="stage-badge">${s.level}</span>
          <span class="stage-title">${s.title}</span>
          <span class="stage-hours">${s.hours_est}h est.</span>
        </div>
        <div class="courses-grid">
          ${courses || "<p style='padding:12px;color:var(--gray-400);font-size:.875rem;'>No courses matched for this stage.</p>"}
        </div>
      </div>
    `;
  }).join("");

  return `
    <div id="path-${idx}" class="tab-panel">
      <div class="path-stages">${stages}</div>
      <div class="path-total" style="margin-top:16px;">
        📚 Total estimated learning time: <strong>${path.total_hours} hours</strong>
      </div>
    </div>
  `;
}

// ── Expand / collapse card ────────────────────────────────────────────────
function toggleCard(header) {
  const card = header.closest(".career-card");
  card.classList.toggle("expanded");
}

// ── Tab switching ─────────────────────────────────────────────────────────
function switchTab(btn) {
  const panelId = btn.getAttribute("data-target");
  const body    = btn.closest(".career-card-body");

  // Deactivate all tabs and panels in this card
  body.querySelectorAll(".career-tab").forEach(t => t.classList.remove("active"));
  body.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

  // Activate clicked tab and its panel
  btn.classList.add("active");
  const panel = body.querySelector(`#${panelId}`);
  if (panel) panel.classList.add("active");
}
