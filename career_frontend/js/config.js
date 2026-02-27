/**
 * CareerIQ — API Configuration
 * ─────────────────────────────
 * Change API_BASE_URL to your deployed backend URL when hosting on Render.
 * For local development, leave as https://careeriq-api.onrender.com/
 */

const CONFIG = {
  // ── Change this when you deploy to Render ──────────────────────────────
  API_BASE_URL: "https://careeriq-api.onrender.com/",


  API_V1: "/api/v1",
};

const API = {
  recommend:    () => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/careers/recommend`,
  quick:        () => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/careers/quick`,
  skillsGap:    () => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/skills/gap`,
  courses:      () => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/courses/search`,
  risk:         (occ) => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/risk/score?occupation=${encodeURIComponent(occ)}`,
  dashboard:    () => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/dashboard/`,
  leaderboard:  () => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/risk/leaderboard`,
  occupations:  () => `${CONFIG.API_BASE_URL}${CONFIG.API_V1}/occupations/`,
  health:       () => `${CONFIG.API_BASE_URL}/health`,
};

// ── Shared API helper ──────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

// ── Risk badge helper (shared across pages) ───────────────────────────────
function riskBadge(label) {
  const map = {
    "Low":       { cls: "badge-risk-low",      icon: "🟢" },
    "Medium":    { cls: "badge-risk-medium",    icon: "🟡" },
    "High":      { cls: "badge-risk-high",      icon: "🔴" },
    "Very High": { cls: "badge-risk-veryhigh",  icon: "🔴" },
  };
  const m = map[label] || map["Medium"];
  return `<span class="badge ${m.cls}">${m.icon} ${label} AI Risk</span>`;
}

function demandBadge(label) {
  const map = {
    "High":   "badge-demand-high",
    "Medium": "badge-demand-medium",
    "Low":    "badge-demand-low",
  };
  const cls = map[label] || "badge-demand-medium";
  return `<span class="badge ${cls}">📈 ${label} Demand</span>`;
}

function matchColor(score) {
  if (score >= 75) return "#10b981";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}
