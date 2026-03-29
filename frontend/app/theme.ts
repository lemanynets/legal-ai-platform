export const themeCSS = `
:root {
  --navy-950: #040811;
  --navy-900: #070e1b;
  --navy-800: #0b162a;
  --navy-700: #102142;
  --navy-600: #1a3466;
  --navy-500: #254a8e;
  --gold-500: #c19b3a;
  --gold-400: #d4a843;
  --gold-300: #e8bf60;
  --accent: #3b82f6;
  --accent-glow: rgba(59, 130, 246, 0.4);
  --gold-glow: rgba(212, 168, 67, 0.3);
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #64748b;
  --surface: rgba(255, 255, 255, 0.03);
  --surface-glass: rgba(15, 23, 42, 0.6);
  --surface-hover: rgba(255, 255, 255, 0.06);
  --border: rgba(255, 255, 255, 0.06);
  --border-strong: rgba(255, 255, 255, 0.12);
  --sidebar-w: 260px;
  --topbar-h: 62px;
  --radius: 12px;
  --radius-sm: 8px;
  --radius-lg: 20px;
  --shadow: 0 4px 24px rgba(0,0,0,0.35);
  --shadow-gold: 0 0 20px var(--gold-glow);
  --transition: 0.15s ease;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
a { color: inherit; text-decoration: none; }
html { scroll-behavior: smooth; }
body {
  background: var(--navy-950);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* ─────────────────────────────────────────────────────────────
   LAYOUT
───────────────────────────────────────────────────────────── */
.app-shell { display: flex; min-height: 100vh; }

.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: var(--sidebar-w);
  background: #070e1b;
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  z-index: 100;
  transition: transform 0.25s cubic-bezier(0.4,0,0.2,1);
}

.sidebar-logo {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 16px; border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.sidebar-logo-icon {
  width: 38px; height: 38px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--gold-500), var(--gold-300));
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px var(--gold-glow);
  color: var(--navy-950);
}
.sidebar-logo-text { font-size: 15px; font-weight: 800; color: #fff; letter-spacing: -0.02em; line-height: 1.2; }
.sidebar-logo-sub { font-size: 10px; color: var(--gold-400); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
.sidebar-mobile-close {
  display: none; background: none; border: none;
  color: var(--text-muted); cursor: pointer; padding: 4px;
  margin-left: auto; border-radius: 6px;
}

/* ── Nav ─────────────────────────────────────────────────── */
.sidebar-nav {
  flex: 1; overflow-y: auto; overflow-x: hidden;
  padding: 12px 0;
  display: flex; flex-direction: column;
}
.sidebar-nav::-webkit-scrollbar { width: 3px; }
.sidebar-nav::-webkit-scrollbar-track { background: transparent; }
.sidebar-nav::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }

.nav-link {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; font-size: 13.5px;
  color: var(--text-secondary);
  transition: all 0.15s; text-decoration: none;
  position: relative; cursor: pointer;
  border-radius: 0; white-space: nowrap;
}
.nav-link:hover { color: #fff; background: rgba(255,255,255,0.04); }
.nav-link.active {
  color: #fff;
  background: linear-gradient(90deg, rgba(212,168,67,0.08), transparent);
}
.nav-link.active::before {
  content: ''; position: absolute; left: 0; top: 25%; bottom: 25%;
  width: 3px; background: var(--gold-400); border-radius: 0 3px 3px 0;
}
.nav-link.active-parent {
  color: var(--text-primary);
  background: rgba(212,168,67,0.04);
}
.nav-link-icon {
  width: 20px; flex-shrink: 0; opacity: 0.6;
  display: flex; align-items: center; justify-content: center;
  transition: opacity 0.15s;
}
.nav-link:hover .nav-link-icon,
.nav-link.active .nav-link-icon { opacity: 1; }
.nav-link-label { flex: 1; min-width: 0; }
.nav-badge {
  flex-shrink: 0; margin-left: auto;
  background: var(--gold-500); color: var(--navy-950);
  font-size: 9px; font-weight: 800; padding: 2px 6px;
  border-radius: 100px;
}

/* Accordion subitems */
.nav-accordion { display: block; }
.nav-subitems {
  display: flex; flex-direction: column; gap: 1px;
  margin: 2px 8px 6px 46px;
  padding: 4px 0 4px 12px;
  border-left: 1px solid rgba(255,255,255,0.07);
}
.nav-sublink {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; font-size: 13px;
  color: var(--text-secondary);
  border-radius: 7px; transition: all 0.15s;
  text-decoration: none; white-space: nowrap;
  overflow: hidden;
}
.nav-sublink:hover { color: var(--text-primary); background: rgba(255,255,255,0.05); }
.nav-sublink.active {
  color: var(--gold-400); background: rgba(212,168,67,0.07); font-weight: 600;
}
.nav-sublink-label { flex: 1; overflow: hidden; text-overflow: ellipsis; }
.nav-sub-badge {
  flex-shrink: 0; font-size: 9px; font-weight: 800;
  padding: 2px 5px; border-radius: 100px;
  background: rgba(212,168,67,0.12); color: var(--gold-400);
}

/* ── Sidebar Footer ──────────────────────────────────────── */
.sidebar-footer {
  padding: 16px; border-top: 1px solid var(--border);
  flex-shrink: 0; display: flex; flex-direction: column; gap: 6px;
}
.sidebar-user {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: 9px;
  background: rgba(255,255,255,0.02); border: 1px solid var(--border);
  cursor: pointer; transition: all 0.15s;
}
.sidebar-user:hover { background: rgba(255,255,255,0.05); border-color: var(--border-strong); }
.sidebar-avatar {
  width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--gold-500), var(--gold-300));
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: var(--navy-950);
}
.sidebar-user-info { flex: 1; min-width: 0; overflow: hidden; }
.sidebar-user-name { font-size: 13px; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sidebar-user-plan { font-size: 11px; color: var(--gold-400); font-weight: 600; }
.sidebar-billing-btn {
  color: var(--text-muted); background: none; border: none;
  cursor: pointer; padding: 4px; display: flex; align-items: center;
  border-radius: 6px; transition: 0.15s; flex-shrink: 0;
  text-decoration: none;
}
.sidebar-billing-btn:hover { color: var(--gold-400); background: rgba(212,168,67,0.08); }
.btn-logout {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 8px 10px;
  background: rgba(255,255,255,0.02); border: 1px solid var(--border);
  border-radius: 8px; color: var(--text-muted);
  font-size: 13px; cursor: pointer; transition: 0.15s;
}
.btn-logout:hover { color: var(--danger); background: rgba(239,68,68,0.06); border-color: rgba(239,68,68,0.2); }
.truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── Main content ────────────────────────────────────────── */
.main-content {
  margin-left: var(--sidebar-w); min-height: 100vh;
  display: flex; flex-direction: column; flex: 1;
  background: var(--navy-950);
}
.page-content { padding: 32px 40px; flex: 1; }

/* ── Topbar ──────────────────────────────────────────────── */
.top-bar {
  height: var(--topbar-h); display: flex; align-items: center;
  justify-content: space-between; padding: 0 28px;
  background: rgba(7,14,27,0.85); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 50; gap: 16px; flex-shrink: 0;
}
.top-bar-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.burger-btn {
  display: none; background: none; border: none;
  color: var(--text-secondary); cursor: pointer;
  padding: 6px; border-radius: 7px; transition: 0.15s; flex-shrink: 0;
}
.burger-btn:hover { background: rgba(255,255,255,0.06); color: #fff; }
.breadcrumb { font-size: 13px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
.breadcrumb-sep { opacity: 0.4; }
.breadcrumb-active { color: var(--text-primary); font-weight: 600; }
.top-bar-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.top-bar-search {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.03); padding: 7px 12px;
  border-radius: 8px; border: 1px solid var(--border); width: 240px;
  position: relative; transition: 0.2s;
}
.top-bar-search:focus-within { border-color: rgba(212,168,67,0.25); background: rgba(255,255,255,0.05); }
.search-icon { display: flex; align-items: center; flex-shrink: 0; color: var(--text-muted); }
.search-spinner {
  width: 13px; height: 13px; border: 2px solid rgba(255,255,255,0.1);
  border-top-color: var(--gold-400); border-radius: 50%;
  animation: spin 0.7s linear infinite; display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
.search-input {
  background: none; border: none; color: var(--text-primary);
  font-size: 13px; outline: none; width: 100%;
}
.search-input::placeholder { color: var(--text-muted); }
.search-results {
  position: absolute; top: calc(100% + 8px); left: 0; right: 0;
  background: #0d1a2e; border: 1px solid var(--border-strong);
  border-radius: 12px; box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  z-index: 1000; max-height: 400px; overflow-y: auto;
  animation: fadeInDown 0.12s ease-out;
}
@keyframes fadeInDown { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
.result-section { padding: 8px 0; border-bottom: 1px solid var(--border); }
.result-section:last-child { border-bottom: none; }
.result-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); padding: 0 12px 5px; }
.result-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; transition: 0.12s;
}
.result-item:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.result-meta { margin-left: auto; font-size: 11px; color: var(--text-muted); flex-shrink: 0; }
.notification-btn {
  background: none; border: none; color: var(--text-muted);
  cursor: pointer; padding: 7px; border-radius: 7px;
  display: flex; align-items: center; transition: 0.15s;
}
.notification-btn:hover { color: var(--text-primary); background: rgba(255,255,255,0.06); }

/* ── Alert strip ─────────────────────────────────────────── */
.alert-strip {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 28px; font-size: 13px;
  border-bottom: 1px solid rgba(239,68,68,0.2);
  background: rgba(239,68,68,0.05); color: #fca5a5;
  flex-shrink: 0;
}
.alert-strip-warn {
  background: rgba(245,158,11,0.05);
  border-bottom-color: rgba(245,158,11,0.2);
  color: #fcd34d;
}

/* ─────────────────────────────────────────────────────────────
   CARDS & COMPONENTS
───────────────────────────────────────────────────────────── */
.card-elevated {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow); transition: all 0.2s;
}
.card-hover:hover { transform: translateY(-2px); border-color: var(--border-strong); }

/* Stat card */
.stat-card {
  background: rgba(255,255,255,0.02); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px; transition: 0.2s;
}
.stat-card:hover { border-color: var(--border-strong); }
.stat-icon-wrap {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 12px; border: 1px solid transparent;
}
.stat-value { font-size: 26px; font-weight: 800; color: var(--text-primary); letter-spacing: -0.02em; line-height: 1; margin-bottom: 4px; }
.stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
.stat-action-link {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--gold-400); margin-top: 8px; transition: 0.15s;
}
.stat-action-link:hover { color: var(--gold-300); }

/* KPI row */
.kpi-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 28px; }

/* Dashboard split */
.dash-split { display: grid; grid-template-columns: 1fr 320px; gap: 20px; align-items: start; }
.dash-left { display: flex; flex-direction: column; gap: 20px; }
.dash-right { display: flex; flex-direction: column; gap: 16px; position: sticky; top: calc(var(--topbar-h) + 16px); }

/* Panel */
.dash-panel { background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.dash-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid var(--border);
}
.dash-panel-title { font-size: 13px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.dash-panel-link { font-size: 12px; color: var(--text-muted); transition: 0.15s; }
.dash-panel-link:hover { color: var(--gold-400); }
.dash-panel-body { padding: 8px; }

/* AI insight */
.ai-insight-card {
  background: rgba(30,58,120,0.12);
  border: 1px solid rgba(59,130,246,0.15);
  border-radius: var(--radius); padding: 16px;
  position: relative;
}
.ai-insight-card::before {
  content: ''; position: absolute; left: 0; top: 20%; bottom: 20%;
  width: 3px; background: var(--accent); border-radius: 0 3px 3px 0;
}
.ai-insight-header {
  display: flex; align-items: center; gap: 7px; margin-bottom: 8px;
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #60a5fa;
}
.ai-insight-text { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.ai-insight-cta {
  margin-top: 10px; font-size: 12px; color: #60a5fa; font-weight: 600;
  display: inline-flex; align-items: center; gap: 4px; transition: 0.15s;
}
.ai-insight-cta:hover { color: #93c5fd; }

/* Tariff widget */
.tariff-widget {
  background: rgba(212,168,67,0.04);
  border: 1px solid rgba(212,168,67,0.12);
  border-radius: var(--radius); padding: 16px;
}
.tariff-plan-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.tariff-plan-name { font-size: 20px; font-weight: 800; color: var(--gold-400); letter-spacing: -0.02em; }
.tariff-status { font-size: 11px; font-weight: 600; color: var(--success); }
.tariff-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid var(--border); font-size: 12px; }
.tariff-row:last-child { border-bottom: none; }
.tariff-row-label { color: var(--text-muted); }
.tariff-row-value { font-weight: 600; color: var(--text-secondary); }
.tariff-row-yes { color: var(--success); }
.tariff-row-no { color: var(--text-muted); }
.usage-bar-wrap { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; margin-top: 4px; }
.usage-bar-fill { height: 100%; border-radius: 2px; background: var(--gold-500); transition: width 0.4s ease; }
.usage-bar-danger .usage-bar-fill { background: var(--danger); }

/* Recent doc items */
.recent-doc-row {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: 8px;
  transition: 0.15s; text-decoration: none;
}
.recent-doc-row:hover { background: rgba(255,255,255,0.04); }
.recent-doc-icon {
  width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
  background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.12);
  display: flex; align-items: center; justify-content: center; color: #3b82f6;
}
.recent-doc-name { flex: 1; min-width: 0; }
.recent-doc-name strong { display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.recent-doc-name span { font-size: 11px; color: var(--text-muted); }
.recent-doc-time { font-size: 11px; color: var(--text-muted); white-space: nowrap; display: flex; align-items: center; gap: 3px; }

/* Empty state */
.empty-inline {
  display: flex; flex-direction: column; align-items: center;
  gap: 10px; padding: 28px 20px; color: var(--text-muted);
  font-size: 13px; text-align: center;
}

/* Quick action strip */
.quick-strip { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 28px; }
.quick-strip-btn {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px 10px; background: rgba(255,255,255,0.02);
  border: 1px solid var(--border); border-radius: 10px;
  text-decoration: none; transition: 0.2s; text-align: center;
}
.quick-strip-btn:hover { border-color: var(--border-strong); background: rgba(255,255,255,0.04); transform: translateY(-2px); }
.quick-strip-icon { width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; }
.quick-strip-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); line-height: 1.3; }

/* Section heading */
.section-heading { font-size: 13px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 12px; }
.card-heading { font-size: 14px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }

/* Skeleton */
.skeleton {
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.07) 50%, rgba(255,255,255,0.03) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 6px;
}
.skeleton-row { height: 42px; border-radius: 8px; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ─────────────────────────────────────────────────────────────
   BUTTONS
───────────────────────────────────────────────────────────── */
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 8px; padding: 10px 20px; font-size: 14px; font-weight: 700;
  border: none; border-radius: var(--radius-sm); cursor: pointer;
  transition: all 0.15s; text-decoration: none;
}
.btn-primary {
  background: linear-gradient(135deg, var(--gold-500), var(--gold-300));
  color: var(--navy-950); box-shadow: 0 4px 12px rgba(212,168,67,0.25);
}
.btn-primary:hover { transform: scale(1.02); box-shadow: 0 6px 18px rgba(212,168,67,0.35); }
.btn-secondary { background: rgba(255,255,255,0.05); color: #fff; border: 1px solid var(--border-strong); }
.btn-secondary:hover { background: rgba(255,255,255,0.09); }
.btn-ghost { background: none; color: var(--text-secondary); border: none; }
.btn-ghost:hover { color: var(--text-primary); background: rgba(255,255,255,0.05); }
.btn-sm { padding: 7px 14px; font-size: 12px; }
.btn-xs { padding: 5px 10px; font-size: 11px; border-radius: 6px; }
.w-full { width: 100%; }

/* ─────────────────────────────────────────────────────────────
   BADGES
───────────────────────────────────────────────────────────── */
.badge { padding: 3px 8px; border-radius: 100px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
.badge-gold { background: rgba(212,168,67,0.1); color: var(--gold-400); border: 1px solid rgba(212,168,67,0.25); }
.badge-blue { background: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.25); }
.badge-success { background: rgba(16,185,129,0.1); color: #34d399; border: 1px solid rgba(16,185,129,0.25); }
.badge-muted { background: rgba(255,255,255,0.05); color: var(--text-muted); border: 1px solid var(--border); }

/* ─────────────────────────────────────────────────────────────
   FORMS
───────────────────────────────────────────────────────────── */
.form-label { display: block; font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
.form-input {
  width: 100%; background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 10px 14px; color: var(--text-primary);
  font-size: 14px; transition: all 0.15s; outline: none;
}
.form-input:focus { border-color: rgba(212,168,67,0.4); background: rgba(255,255,255,0.05); }
.form-input::placeholder { color: var(--text-muted); }

/* ─────────────────────────────────────────────────────────────
   MODALS
───────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.75);
  backdrop-filter: blur(8px); display: flex; align-items: center;
  justify-content: center; z-index: 1000; animation: fadeIn 0.2s ease;
}
.modal-content { padding: 32px; width: 100%; max-width: 580px; position: relative; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* ─────────────────────────────────────────────────────────────
   UTILITIES
───────────────────────────────────────────────────────────── */
.grid-2 { display: grid; grid-template-columns: repeat(2,1fr); gap: 20px; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fill,minmax(320px,1fr)); gap: 20px; }
.grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-grow { flex-grow: 1; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.mt-auto { margin-top: auto; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 24px; }
.p-2 { padding: 8px; }
.p-4 { padding: 16px; }
.mx-auto { margin-left: auto; margin-right: auto; }
.max-w-md { max-width: 440px; }
.text-xs { font-size: 12px; }
.text-sm { font-size: 14px; }
.text-lg { font-size: 18px; }
.text-xl { font-size: 20px; }
.font-bold { font-weight: 700; }
.text-center { text-align: center; }
.text-gold { color: var(--gold-400); }
.text-secondary { color: var(--text-secondary); }
.text-muted { color: var(--text-muted); }
.cursor-pointer { cursor: pointer; }

/* ─────────────────────────────────────────────────────────────
   PAGE SECTION HEADER
───────────────────────────────────────────────────────────── */
.section-header { margin-bottom: 28px; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.section-title { font-size: 26px; font-weight: 800; color: #fff; letter-spacing: -0.03em; margin-bottom: 4px; }
.section-subtitle { font-size: 14px; color: var(--text-muted); }

/* ─────────────────────────────────────────────────────────────
   DOCUMENTS PAGE
───────────────────────────────────────────────────────────── */
.document-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(300px,1fr)); gap: 20px; margin-top: 24px; }
.document-card { padding: 20px; display: flex; flex-direction: column; gap: 14px; position: relative; overflow: hidden; }
.doc-type-badge { display: inline-block; align-self: flex-start; padding: 3px 9px; border-radius: 6px; font-size: 11px; font-weight: 700; background: rgba(212,168,67,0.1); color: var(--gold-400); }
.doc-card-title { font-size: 16px; font-weight: 700; color: #fff; }
.doc-card-preview { font-size: 13px; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; min-height: 56px; }
.doc-card-footer { margin-top: auto; padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.doc-date { font-size: 12px; color: var(--text-muted); }
.filter-bar { display: flex; gap: 14px; padding: 16px; margin-top: 20px; align-items: center; background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: var(--radius); }
.filter-group { flex: 1; display: flex; align-items: center; gap: 10px; background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 8px; padding: 0 12px; }
.filter-group input, .filter-group select { background: transparent; border: none; color: #fff; padding: 9px 0; width: 100%; outline: none; font-size: 14px; }
.filter-group select option { background: var(--navy-900); }

/* ─────────────────────────────────────────────────────────────
   TIMELINE
───────────────────────────────────────────────────────────── */
.timeline-container { position: relative; }
.timeline-container::before { content: ''; position: absolute; left: 7px; top: 0; bottom: 0; width: 2px; background: rgba(255,255,255,0.05); }
.timeline-event { position: relative; padding-left: 28px; margin-bottom: 24px; }
.timeline-event:last-child { margin-bottom: 0; }
.timeline-marker { position: absolute; left: 0; top: 4px; width: 15px; height: 15px; border-radius: 50%; background: var(--navy-900); border: 2px solid var(--gold-500); z-index: 1; }
.timeline-content-inner { background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 12px; padding: 16px; transition: all 0.15s; }
.timeline-content-inner:hover { border-color: rgba(212,168,67,0.2); background: rgba(255,255,255,0.03); }

/* ─────────────────────────────────────────────────────────────
   SPACING HELPERS
───────────────────────────────────────────────────────────── */
.space-y-4 > * + * { margin-top: 16px; }
.space-y-2 > * + * { margin-top: 8px; }

/* ─────────────────────────────────────────────────────────────
   MOBILE
───────────────────────────────────────────────────────────── */
.sidebar-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 99; backdrop-filter: blur(2px); }

@media (max-width: 1024px) {
  .sidebar { transform: translateX(-260px); }
  .sidebar.sidebar-open { transform: translateX(0); }
  .sidebar-overlay { display: block; }
  .sidebar-mobile-close { display: flex; }
  .burger-btn { display: flex; }
  .main-content { margin-left: 0; }
  .kpi-row { grid-template-columns: repeat(2,1fr); }
  .dash-split { grid-template-columns: 1fr; }
  .dash-right { position: static; }
  .quick-strip { grid-template-columns: repeat(2,1fr); }
  .top-bar-search { width: 180px; }
}
@media (max-width: 640px) {
  .page-content { padding: 16px; }
  .kpi-row { grid-template-columns: repeat(2,1fr); }
  .top-bar { padding: 0 16px; }
  .top-bar-search { width: 140px; }
}
`;
