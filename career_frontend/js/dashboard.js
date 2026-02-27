// ── Chart instances (kept for destroy on refresh) ──────────────────────────
let scatterChart = null;
let riskDonut    = null;

// ── On page load ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderPersonalBanner();   // show user's results first (from sessionStorage)
  loadDashboard();          // then load market data from API
  document.getElementById("refreshBtn").addEventListener("click", loadDashboard);
  document.getElementById("filterFamily").addEventListener("change", loadDashboard);
});

// ═══════════════════════════════════════════════════════════════════════════
// PERSONAL RESULTS BANNER
// Reads the career results saved in sessionStorage when the user submitted
// the form, and renders a personalised summary at the top of the dashboard.
// No extra API call needed — data is already available locally.
// ═══════════════════════════════════════════════════════════════════════════

function renderPersonalBanner() {
  const banner  = document.getElementById("personalBanner");
  const raw     = sessionStorage.getItem("careerResults");
  const payRaw  = sessionStorage.getItem("careerPayload");

  if (!raw) {
    // User came directly to dashboard without doing a search — show a prompt
    banner.classList.remove("hidden");
    banner.innerHTML = `
      <div class="personal-banner personal-banner--empty">
        <div class="personal-banner-empty-inner">
          <div class="personal-banner-empty-icon">🎯</div>
          <div>
            <div class="personal-banner-empty-title">No personal results yet</div>
            <div class="personal-banner-empty-sub">
              Complete the career matching form to see your personalised recommendations here.
            </div>
          </div>
          <a href="form.html" class="btn-primary" style="white-space:nowrap;">Get Matched →</a>
        </div>
      </div>
    `;
    return;
  }

  try {
    const data    = JSON.parse(raw);
    const payload = payRaw ? JSON.parse(payRaw) : {};
    const details = (data.career_details || []).map(normaliseDetail);

    if (!details.length) return;

    const userLabels = {
      "cbc": "CBC Student", "8-4-4": "8-4-4 Student",
      "graduate": "Graduate", "professional": "Professional",
      "postgraduate": "Postgraduate", "diploma": "Diploma Student",
    };
    const userLabel = userLabels[payload.user_type] || "Your";

    banner.classList.remove("hidden");
    banner.innerHTML = `
      <div class="personal-banner">

        <div class="personal-banner-header">
          <div>
            <div class="personal-banner-label">Your Career Matches</div>
            <h2 class="personal-banner-title">
              ${userLabel} Top ${details.length} Career Recommendations
            </h2>
            <p class="personal-banner-sub">
              Based on your skills and goals — see how they compare in the market below
            </p>
          </div>
          <a href="results.html" class="btn-outline-blue">View Full Results →</a>
        </div>

        <div class="personal-cards-grid">
          ${details.map((d, i) => buildPersonalCard(d, i)).join("")}
        </div>

      </div>
    `;
  } catch (e) {
    console.warn("Could not render personal banner:", e);
  }
}

// ── Normalise a career_detail item (handles both field name styles) ────────
function normaliseDetail(d) {
  const ci   = d.career_info  || {};
  const risk = d.risk_profile || {};
  const gap  = d.gap_report   || {};
  const path = d.learning_path || {};
  return {
    rank         : d.rank || 0,
    title        : ci.title        || ci.career       || "Unknown Career",
    career_family: ci.career_family || "",
    match_score  : parseFloat(ci.match_score || 0),
    demand_level : ci.demand_level  || risk.demand_level || "Medium",
    min_education: ci.min_education || "",
    median_wage  : ci.median_wage   || null,
    ai_risk_label: risk.ai_risk_label   || "Medium",
    ai_risk_score: parseFloat(risk.ai_risk_score || 0),
    future_proof : parseFloat(risk.future_proof_score || 0),
    alignment_pct: parseFloat(gap.alignment_pct || 0),
    total_hours  : parseFloat(path.total_hours  || path.est_total_hours || 0),
    gap_count    : gap.gap_count || (gap.top_gaps || []).length || 0,
  };
}

// ── Build a single personal career card ───────────────────────────────────
function buildPersonalCard(d, index) {
  const matchScore  = Math.round(d.match_score);
  const alignScore  = Math.round(d.alignment_pct);
  const fpScore     = Math.round(d.future_proof);
  const wage        = d.median_wage ? `$${Math.round(d.median_wage / 1000)}k` : "—";
  const rankClass   = index === 0 ? "pcard-rank--gold"
                    : index === 1 ? "pcard-rank--silver"
                    : index === 2 ? "pcard-rank--bronze" : "";

  const RISK_COLORS = {
    "Low": "#10b981", "Medium": "#f59e0b", "High": "#ef4444", "Very High": "#db2777"
  };
  const riskColor = RISK_COLORS[d.ai_risk_label] || "#94a3b8";

  // Match score ring
  const circ      = 2 * Math.PI * 20;
  const offset    = circ * (1 - matchScore / 100);
  const ringColor = matchScore >= 75 ? "#10b981" : matchScore >= 50 ? "#f59e0b" : "#ef4444";

  return `
    <div class="personal-card">
      <div class="pcard-top">
        <div class="pcard-rank ${rankClass}">${d.rank}</div>
        <div class="pcard-info">
          <div class="pcard-family">${d.career_family}</div>
          <div class="pcard-title">${d.title}</div>
          <div class="pcard-badges">
            ${riskBadge(d.ai_risk_label)}
            ${demandBadge(d.demand_level)}
          </div>
        </div>
        <div class="pcard-ring">
          <svg viewBox="0 0 50 50" width="50" height="50">
            <circle cx="25" cy="25" r="20" fill="none" stroke="#f1f5f9" stroke-width="4"/>
            <circle cx="25" cy="25" r="20" fill="none"
              stroke="${ringColor}" stroke-width="4"
              stroke-dasharray="${circ}" stroke-dashoffset="${offset}"
              stroke-linecap="round"
              transform="rotate(-90 25 25)"/>
          </svg>
          <div class="pcard-ring-text">${matchScore}%</div>
        </div>
      </div>

      <div class="pcard-stats">
        <div class="pcard-stat">
          <div class="pcard-stat-label">Skill Alignment</div>
          <div class="pcard-stat-bar">
            <div class="pcard-stat-fill" style="width:${alignScore}%;background:${ringColor}"></div>
          </div>
          <div class="pcard-stat-val">${alignScore}%</div>
        </div>
        <div class="pcard-stat">
          <div class="pcard-stat-label">Future-Proof</div>
          <div class="pcard-stat-bar">
            <div class="pcard-stat-fill" style="width:${fpScore}%;background:#3b82f6"></div>
          </div>
          <div class="pcard-stat-val">${fpScore}/100</div>
        </div>
      </div>

      <div class="pcard-footer">
        <span class="pcard-meta">💰 ${wage}</span>
        <span class="pcard-meta">📚 ${Math.round(d.total_hours)}h learning</span>
        <span class="pcard-meta" style="color:${riskColor}">
          ⚡ ${d.ai_risk_score}% AI risk
        </span>
      </div>
    </div>
  `;
}


// ═══════════════════════════════════════════════════════════════════════════
// MARKET DASHBOARD (unchanged logic, same as before)
// ═══════════════════════════════════════════════════════════════════════════

async function loadDashboard() {
  const loading = document.getElementById("dashLoading");
  const content = document.getElementById("dashContent");
  const family  = document.getElementById("filterFamily").value;

  loading.innerHTML = `
    <div class="spinner" style="width:40px;height:40px;border-width:3px;"></div>
    <p class="loading-text">Loading market data…</p>
  `;
  loading.classList.remove("hidden");
  content.classList.add("hidden");

  try {
    const params = family ? `?career_family=${encodeURIComponent(family)}` : "";
    const data   = await apiFetch(API.dashboard() + params);
    renderDashboard(data);
    populateFamilyFilter(data);
    loading.classList.add("hidden");
    content.classList.remove("hidden");
  } catch (err) {
    loading.innerHTML = `
      <div class="alert alert-error" style="max-width:480px;">
        ⚠️ Could not load dashboard data.<br/>
        <small>Make sure your API server is running at <strong>${CONFIG.API_BASE_URL}</strong></small><br/>
        <small style="color:var(--gray-500)">${err.message}</small>
      </div>`;
  }
}

function populateFamilyFilter(data) {
  const sel = document.getElementById("filterFamily");
  if (sel.options.length > 1) return;
  const families = [...new Set((data.sector_risk || []).map(s => s.career_family))].sort();
  families.forEach(f => {
    const opt = document.createElement("option");
    opt.value = f; opt.textContent = f;
    sel.appendChild(opt);
  });
}

function renderDashboard(data) {
  renderKPIs(data.summary || {});
  renderScatterChart(data.scatter_data || []);
  renderRiskDonut(data.risk_dist || {});
  renderSectorList(data.sector_risk || []);
  renderEmergingCareers(data.emerging_careers || []);
  renderTopCareersTable(data.top_careers || []);
}

function renderKPIs(s) {
  document.getElementById("kpiRow").innerHTML = `
    <div class="kpi-card">
      <div class="kpi-label">Total Occupations</div>
      <div class="kpi-value">${s.total_occupations?.toLocaleString() || "—"}</div>
      <div class="kpi-sub">In the database</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Career Families</div>
      <div class="kpi-value">${s.total_career_families || "—"}</div>
      <div class="kpi-sub">Sectors covered</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Avg Future-Proof</div>
      <div class="kpi-value">${s.avg_future_proof || "—"}</div>
      <div class="kpi-sub">Out of 100</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Low AI Risk</div>
      <div class="kpi-value">${s.pct_low_risk || 0}%</div>
      <div class="kpi-sub">Of all occupations</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">High Demand Jobs</div>
      <div class="kpi-value">${s.high_demand_count?.toLocaleString() || "—"}</div>
      <div class="kpi-sub">Strong market outlook</div>
    </div>
  `;
}

function renderScatterChart(rawData) {
  const ctx = document.getElementById("scatterChart").getContext("2d");
  if (scatterChart) scatterChart.destroy();

  const DEMAND_COLORS = {
    "High":   "rgba(37,99,235,0.7)",
    "Medium": "rgba(245,158,11,0.7)",
    "Low":    "rgba(148,163,184,0.7)",
  };

  const datasets = ["High", "Medium", "Low"].map(demand => ({
    label: `${demand} Demand`,
    data: rawData
      .filter(d => d.demand_level === demand)
      .map(d => ({ x: d.ai_risk, y: d.future_proof, label: d.occupation })),
    backgroundColor: DEMAND_COLORS[demand],
    pointRadius: 5,
    pointHoverRadius: 7,
  }));

  scatterChart = new Chart(ctx, {
    type: "scatter",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { font: { family: "DM Sans", size: 12 }, color: "#64748b" },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const d = ctx.raw;
              return ` ${d.label}  |  Risk: ${d.x}%  |  FP: ${d.y}`;
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "AI Replacement Risk (%)", color: "#94a3b8", font: { size: 11 } },
          grid:  { color: "#f1f5f9" },
          ticks: { color: "#94a3b8", font: { size: 10 } },
          min: 0, max: 100,
        },
        y: {
          title: { display: true, text: "Future-Proof Score", color: "#94a3b8", font: { size: 11 } },
          grid:  { color: "#f1f5f9" },
          ticks: { color: "#94a3b8", font: { size: 10 } },
          min: 0, max: 100,
        },
      },
    },
  });
}

function renderRiskDonut(dist) {
  const ctx = document.getElementById("riskDonut").getContext("2d");
  if (riskDonut) riskDonut.destroy();

  const order   = ["Low", "Medium", "High", "Very High"];
  const colors  = ["#10b981", "#f59e0b", "#ef4444", "#db2777"];
  const labels  = order.filter(k => dist[k]);
  const values  = labels.map(k => dist[k] || 0);
  const bgColors = labels.map(k => colors[order.indexOf(k)]);

  riskDonut = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: bgColors,
                   borderWidth: 3, borderColor: "#ffffff" }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: "65%",
      plugins: {
        legend: { position: "bottom",
                  labels: { padding: 14, font: { family: "DM Sans", size: 11 }, color: "#475569" } },
        tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed} occupations` } },
      },
    },
  });
}

function renderSectorList(sectors) {
  const el = document.getElementById("sectorList");
  const RISK_COLORS_MAP = {
    "Low": "#10b981", "Medium": "#f59e0b", "High": "#ef4444", "Very High": "#db2777",
  };
  el.innerHTML = sectors.slice(0, 10).map(s => `
    <div class="sector-row">
      <div class="sector-name">${s.career_family}</div>
      <div class="sector-bar-wrap">
        <div class="sector-bar-fill"
          style="width:${s.avg_ai_risk}%;background:${RISK_COLORS_MAP[s.risk_label] || '#94a3b8'}">
        </div>
      </div>
      <div class="sector-risk-label" style="color:${RISK_COLORS_MAP[s.risk_label] || '#94a3b8'}">
        ${s.avg_ai_risk}%
      </div>
    </div>
  `).join("");
}

function renderEmergingCareers(careers) {
  const el = document.getElementById("emergingList");
  if (!careers.length) {
    el.innerHTML = `<p class="text-muted">No emerging career data available.</p>`;
    return;
  }
  el.innerHTML = careers.map(c => `
    <div class="emerging-item">
      <div>
        <div class="emerging-name">${c.occupation}</div>
        <div class="emerging-family">${c.career_family}</div>
      </div>
      <div class="emerging-scores">
        <span class="fp-chip">FP ${c.future_proof}</span>
        ${demandBadge(c.demand_level)}
      </div>
    </div>
  `).join("");
}

function renderTopCareersTable(careers) {
  const RISK_COLORS_MAP = {
    "Low": "#10b981", "Medium": "#f59e0b", "High": "#ef4444", "Very High": "#db2777"
  };
  const tbody = document.getElementById("topCareersBody");
  tbody.innerHTML = careers.map((c, i) => {
    const wage     = c.median_wage ? `$${Math.round(c.median_wage / 1000)}k` : "—";
    const fp       = Math.round(c.future_proof_score || 0);
    const riskColor = RISK_COLORS_MAP[c.ai_risk_label] || "#94a3b8";
    return `
      <tr>
        <td><span class="rank-num">${i + 1}</span></td>
        <td style="font-weight:600;color:var(--navy)">${c.occupation}</td>
        <td style="color:var(--blue);font-size:0.78rem;font-weight:600">${c.career_family}</td>
        <td>
          <div class="fp-bar">
            <div class="fp-bar-track"><div class="fp-bar-fill" style="width:${fp}%"></div></div>
            <span class="fp-score-num">${fp}</span>
          </div>
        </td>
        <td><span style="color:${riskColor};font-weight:600;font-size:0.8rem">
          ${c.ai_risk_score}% — ${c.ai_risk_label}
        </span></td>
        <td>${demandBadge(c.demand_level)}</td>
        <td style="font-weight:600">${wage}</td>
      </tr>
    `;
  }).join("");
}
