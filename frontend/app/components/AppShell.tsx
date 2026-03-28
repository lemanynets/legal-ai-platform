"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  LayoutDashboard,
  FolderOpen,
  FileStack,
  BookOpen,
  Zap,
  FileText,
  Layers,
  ScanSearch,
  Search,
  Library,
  Users2,
  Scale,
  BarChart3,
  MessageSquare,
  Settings,
  Gavel,
  CalendarDays,
  Calculator,
  Landmark,
  BrainCircuit,
  ChevronDown,
  LogOut,
  Bell,
  UserCircle,
  CreditCard,
  Wrench,
  ShieldCheck,
  X,
  Menu,
} from "lucide-react";

import { getCurrentSubscription } from "@/lib/api";
import {
  getSession,
  getToken,
  initAuth,
  logout,
  updateSessionPlan,
  type UserSession,
} from "@/lib/auth";

// ---------------------------------------------------------------------------
// Route → Ukrainian name mapping (виправляє breadcrumb)
// ---------------------------------------------------------------------------
const ROUTE_NAMES: Record<string, string> = {
  dashboard: "Головна",
  cases: "Мої справи",
  documents: "Архів документів",
  "knowledge-base": "База знань",
  knowledge: "База знань",
  generate: "Генерація документів",
  "auto-process": "Автообробка",
  analyze: "AI Аналізатор",
  "case-law": "Судова практика",
  registries: "Реєстр справ",
  monitoring: "Моніторинг",
  calendar: "Календар та строки",
  deadlines: "Строки",
  "e-court": "Е-Суд",
  profile: "Налаштування акаунта",
  reports: "Аналітика та звіти",
  team: "Моя команда",
  forum: "Форум юристів",
  billing: "Тарифи та підписки",
  calculators: "Калькулятори",
  "full-lawyer": "Повний юрист",
  "strategy-studio": "Стратегія Студіо",
  audit: "Аудит",
  "decision-analysis": "Аналіз рішення",
  settings: "Налаштування",
};

// ---------------------------------------------------------------------------
// Navigation structure
// ---------------------------------------------------------------------------
type SubItem = { href: string; label: string; badge?: string };
type NavItem =
  | { type: "link"; href: string; icon: React.ReactNode; label: string; badge?: string }
  | { type: "group"; id: string; icon: React.ReactNode; label: string; subItems: SubItem[] };

const NAV_ITEMS: NavItem[] = [
  {
    type: "link",
    href: "/dashboard",
    icon: <LayoutDashboard size={18} />,
    label: "Головна",
  },

  // ── Моя робота ────────────────────────────────────────────────────────────
  {
    type: "group",
    id: "workspace",
    icon: <FolderOpen size={18} />,
    label: "Мої справи",
    subItems: [
      { href: "/dashboard/cases",    label: "Усі справи" },
      { href: "/dashboard/documents", label: "Архів документів" },
    ],
  },

  // ── AI інструменти ────────────────────────────────────────────────────────
  {
    type: "group",
    id: "ai_tools",
    icon: <Zap size={18} />,
    label: "AI Юрист",
    subItems: [
      { href: "/dashboard/generate",      label: "Генерація документів" },
      { href: "/dashboard/full-lawyer",   label: "Повний юрист" },
      { href: "/dashboard/analyze",       label: "AI Аналізатор" },
      { href: "/dashboard/auto-process",  label: "Автообробка",  badge: "PRO+" },
      { href: "/dashboard/strategy-studio", label: "Стратегія Студіо" },
    ],
  },

  // ── Дослідження ──────────────────────────────────────────────────────────
  {
    type: "group",
    id: "research",
    icon: <Search size={18} />,
    label: "Дослідження",
    subItems: [
      { href: "/dashboard/case-law",     label: "Судова практика" },
      { href: "/dashboard/registries",   label: "Реєстр справ",      badge: "NEW" },
      { href: "/dashboard/monitoring",   label: "Моніторинг",         badge: "PRO+" },
      { href: "/dashboard/knowledge-base", label: "База знань",       badge: "NEW" },
      { href: "/dashboard/decision-analysis", label: "Аналіз рішення" },
    ],
  },

  // ── Контроль строків ─────────────────────────────────────────────────────
  {
    type: "group",
    id: "control",
    icon: <CalendarDays size={18} />,
    label: "Контроль",
    subItems: [
      { href: "/dashboard/calendar",    label: "Календар та строки" },
      { href: "/dashboard/deadlines",   label: "Строки" },
      { href: "/dashboard/calculators", label: "Калькулятори" },
    ],
  },

  // ── Е-Суд (standalone, PRO+) ─────────────────────────────────────────────
  {
    type: "link",
    href: "/dashboard/e-court",
    icon: <Landmark size={18} />,
    label: "Е-Суд",
    badge: "PRO+",
  },

  // ── Налаштування та команда ───────────────────────────────────────────────
  {
    type: "group",
    id: "management",
    icon: <Settings size={18} />,
    label: "Управління",
    subItems: [
      { href: "/dashboard/profile",  label: "Профіль та акаунт" },
      { href: "/dashboard/team",     label: "Моя команда" },
      { href: "/dashboard/reports",  label: "Аналітика та звіти" },
      { href: "/dashboard/audit",    label: "Аудит" },
      { href: "/dashboard/settings", label: "Налаштування", badge: "PRO+" },
    ],
  },

  // ── Спільнота ─────────────────────────────────────────────────────────────
  {
    type: "link",
    href: "/dashboard/forum",
    icon: <MessageSquare size={18} />,
    label: "Форум юристів",
    badge: "NEW",
  },
];

const PLAN_LABELS: Record<string, string> = {
  FREE: "FREE",
  PRO: "PRO",
  PRO_PLUS: "PRO+",
  TEAM: "TEAM",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<UserSession | null>(null);
  const [plan, setPlan] = useState("FREE");
  const [sidebarOpen, setSidebarOpen] = useState(false); // mobile burger

  // Accordion state — ключі відповідають type:"group" id
  const [expandedMenus, setExpandedMenus] = useState<Record<string, boolean>>({
    workspace: false,
    ai_tools: false,
    research: false,
    control: false,
    management: false,
  });

  const toggleMenu = (id: string) =>
    setExpandedMenus((prev) => ({ ...prev, [id]: !prev[id] }));

  // Auto-expand group that contains active route
  useEffect(() => {
    NAV_ITEMS.forEach((item) => {
      if (item.type === "group" && item.subItems.some((s) => pathname === s.href)) {
        setExpandedMenus((prev) => ({ ...prev, [item.id]: true }));
      }
    });
  }, [pathname]);

  // Close mobile sidebar on route change
  useEffect(() => setSidebarOpen(false), [pathname]);

  // Bootstrap auth + subscription
  useEffect(() => {
    let active = true;
    async function bootstrap() {
      await initAuth();
      const s = getSession();
      if (!active) return;
      setSession(s);
      setPlan(s?.plan ?? "FREE");
      if (!s) return;
      const sub = await getCurrentSubscription(s.token, s.user_id).catch(() => null);
      if (!active || !sub) return;
      const next = sub.plan || s.plan || "FREE";
      setPlan(next);
      updateSessionPlan(next);
      setSession((prev) => (prev ? { ...prev, plan: next } : prev));
    }
    void bootstrap();
    return () => { active = false; };
  }, []);

  const displayName = useMemo(
    () => session?.email?.split("@")[0] || "Користувач",
    [session?.email]
  );
  const avatarLetter = displayName[0]?.toUpperCase() || "U";
  const planLabel = PLAN_LABELS[plan] || plan || "FREE";

  // Global search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (searchQuery.length < 2) { setSearchResults(null); setShowResults(false); return; }
    const t = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const { globalSearch } = await import("@/lib/api");
        const r = await globalSearch(searchQuery, getToken());
        setSearchResults(r);
        setShowResults(true);
      } catch { /* ignore */ } finally { setSearchLoading(false); }
    }, 400);
    return () => clearTimeout(t);
  }, [searchQuery]);

  // Logout з підтвердженням
  const onLogout = async () => {
    if (!window.confirm("Вийти з акаунта?")) return;
    await logout();
    router.push("/login");
  };

  // Breadcrumb: останній сегмент → Ukrainian name
  const routeSlug = pathname.split("/").filter(Boolean).pop() ?? "dashboard";
  const breadcrumbName = ROUTE_NAMES[routeSlug] ?? routeSlug;

  // ── Sidebar rendering ──────────────────────────────────────────────────
  const sidebarContent = (
    <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Scale size={22} color="var(--navy-950)" />
        </div>
        <div className="sidebar-header-text">
          <div className="sidebar-logo-text">LEGAL AI</div>
          <div className="sidebar-logo-sub">Леманинець та партнери</div>
        </div>
        {/* Mobile close */}
        <button className="sidebar-mobile-close" onClick={() => setSidebarOpen(false)}>
          <X size={18} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => {
          if (item.type === "link") {
            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} className={`nav-link ${active ? "active" : ""}`}>
                <span className="nav-link-icon">{item.icon}</span>
                <span className="nav-link-label">{item.label}</span>
                {item.badge && <span className="nav-badge">{item.badge}</span>}
              </Link>
            );
          }

          // type === "group"
          const isOpen = expandedMenus[item.id];
          const hasActive = item.subItems.some((s) => pathname === s.href);
          return (
            <div key={item.id} className="nav-accordion">
              <div
                className={`nav-link ${hasActive && !isOpen ? "active-parent" : ""}`}
                onClick={() => toggleMenu(item.id)}
                style={{ cursor: "pointer", justifyContent: "space-between" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span className="nav-link-icon">{item.icon}</span>
                  <span className="nav-link-label">{item.label}</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    marginRight: "8px",
                    opacity: isOpen ? 0.9 : 0.35,
                    transform: isOpen ? "rotate(180deg)" : "none",
                    transition: "transform 0.2s, opacity 0.2s",
                    flexShrink: 0,
                  }}
                />
              </div>
              {isOpen && (
                <div className="nav-subitems">
                  {item.subItems.map((sub) => {
                    const active = pathname === sub.href;
                    return (
                      <Link key={sub.href} href={sub.href} className={`nav-sublink ${active ? "active" : ""}`}>
                        <span className="nav-sublink-label">{sub.label}</span>
                        {sub.badge && (
                          <span className="nav-badge" style={{ transform: "scale(0.8)", marginLeft: "auto" }}>
                            {sub.badge}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-user" onClick={() => router.push("/dashboard/profile")} title="Профіль">
          <div className="sidebar-avatar">{avatarLetter}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name truncate">{displayName}</div>
            <div className="sidebar-user-plan">{planLabel}</div>
          </div>
          <Link
            href="/dashboard/billing"
            onClick={(e) => e.stopPropagation()}
            className="sidebar-billing-btn"
            title="Тарифи"
          >
            <CreditCard size={15} />
          </Link>
        </div>
        <button onClick={onLogout} className="btn-logout" title="Вийти">
          <LogOut size={16} />
          <span>Вийти</span>
        </button>
      </div>
    </aside>
  );

  return (
    <div className="app-shell" onClick={() => setShowResults(false)}>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {sidebarContent}

      <main className="main-content">
        {/* Topbar */}
        <header className="top-bar">
          <div className="top-bar-left">
            {/* Mobile burger */}
            <button className="burger-btn" onClick={() => setSidebarOpen(true)}>
              <Menu size={20} />
            </button>
            <div className="breadcrumb">
              <span className="breadcrumb-root">Дашборд</span>
              {routeSlug !== "dashboard" && (
                <>
                  <span className="breadcrumb-sep"> / </span>
                  <span className="breadcrumb-active">{breadcrumbName}</span>
                </>
              )}
            </div>
          </div>

          <div className="top-bar-right">
            {/* Search */}
            <div className="top-bar-search" onClick={(e) => e.stopPropagation()}>
              <span className="search-icon">
                {searchLoading ? (
                  <span className="search-spinner" />
                ) : (
                  <Search size={14} opacity={0.5} />
                )}
              </span>
              <input
                type="text"
                placeholder="Швидкий пошук..."
                className="search-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => searchQuery.length >= 2 && setShowResults(true)}
              />
              {showResults && searchResults && (
                <div className="search-results card-elevated">
                  {searchResults.cases?.length > 0 && (
                    <div className="result-section">
                      <div className="result-label">Справи</div>
                      {searchResults.cases.map((c: any) => (
                        <div key={c.id} className="result-item" onClick={() => { router.push(`/dashboard/cases?id=${c.id}`); setShowResults(false); }}>
                          <FolderOpen size={13} style={{ color: "var(--gold-400)", flexShrink: 0 }} />
                          <span>{c.title}</span>
                          {c.number && <span className="result-meta">{c.number}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                  {searchResults.documents?.length > 0 && (
                    <div className="result-section">
                      <div className="result-label">Документи</div>
                      {searchResults.documents.map((d: any) => (
                        <div key={d.id} className="result-item" onClick={() => { router.push(`/dashboard/documents?id=${d.id}`); setShowResults(false); }}>
                          <FileText size={13} style={{ flexShrink: 0 }} />
                          <span>{d.title || d.type}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {searchResults.forum?.length > 0 && (
                    <div className="result-section">
                      <div className="result-label">Форум</div>
                      {searchResults.forum.map((p: any) => (
                        <div key={p.id} className="result-item" onClick={() => { router.push(`/dashboard/forum/post/${p.id}`); setShowResults(false); }}>
                          <MessageSquare size={13} style={{ flexShrink: 0 }} />
                          <span>{p.title}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {!searchResults.cases?.length && !searchResults.documents?.length && !searchResults.forum?.length && (
                    <div className="p-4 text-center text-muted text-xs">Нічого не знайдено</div>
                  )}
                </div>
              )}
            </div>

            {/* Notifications — функціональна кнопка */}
            <button className="notification-btn" title="Сповіщення (скоро)">
              <Bell size={18} />
            </button>
          </div>
        </header>

        <div className="page-content">{children}</div>
      </main>

      <style jsx>{`
        /* ── Sidebar ─────────────────────────────────────────── */
        .sidebar {
          width: 260px;
        }
        .sidebar-header-text {
          display: flex;
          flex-direction: column;
          flex: 1;
          min-width: 0;
        }
        .sidebar-mobile-close {
          display: none;
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 4px;
          margin-left: auto;
        }

        /* ── Accordion ───────────────────────────────────────── */
        .nav-accordion { margin-bottom: 2px; }
        .nav-subitems {
          padding: 4px 0 4px 34px;
          display: flex;
          flex-direction: column;
          gap: 2px;
          border-left: 1px solid rgba(255,255,255,0.06);
          margin-left: 28px;
          margin-top: 2px;
          margin-bottom: 6px;
        }
        .nav-sublink {
          display: flex;
          align-items: center;
          padding: 7px 14px;
          font-size: 13px;
          color: #cbd5e1 !important;
          text-decoration: none !important;
          border-radius: 8px;
          transition: 0.15s;
          gap: 6px;
        }
        .nav-sublink:hover { color: #fff !important; background: rgba(255,255,255,0.04); }
        .nav-sublink.active {
          color: var(--gold-400) !important;
          background: rgba(212,168,67,0.07);
          font-weight: 600;
          text-shadow: 0 0 10px rgba(212,168,67,0.25);
        }
        .active-parent {
          color: #fff;
          border-left: 2px solid var(--gold-500);
          padding-left: 22px;
          background: rgba(212,168,67,0.04);
        }

        /* ── Sidebar footer ──────────────────────────────────── */
        .sidebar-user-info { flex: 1; overflow: hidden; min-width: 0; }
        .sidebar-billing-btn {
          color: var(--text-muted);
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px;
          display: flex;
          align-items: center;
          border-radius: 6px;
          transition: 0.15s;
          flex-shrink: 0;
        }
        .sidebar-billing-btn:hover { color: var(--gold-400); background: rgba(212,168,67,0.08); }
        .btn-logout {
          display: flex;
          align-items: center;
          gap: 8px;
          width: 100%;
          margin-top: 8px;
          padding: 9px 12px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 10px;
          color: var(--text-muted);
          font-size: 13px;
          cursor: pointer;
          transition: 0.15s;
          text-align: left;
        }
        .btn-logout:hover {
          color: var(--danger);
          background: rgba(239,68,68,0.06);
          border-color: rgba(239,68,68,0.2);
        }

        /* ── Topbar ──────────────────────────────────────────── */
        .top-bar {
          height: 62px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 28px;
          background: rgba(11, 22, 40, 0.5);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid rgba(255,255,255,0.06);
          position: sticky;
          top: 0;
          z-index: 50;
          gap: 16px;
        }
        .top-bar-left {
          display: flex;
          align-items: center;
          gap: 12px;
          min-width: 0;
        }
        .burger-btn {
          display: none;
          background: none;
          border: none;
          color: var(--text-secondary);
          cursor: pointer;
          padding: 6px;
          border-radius: 8px;
          transition: 0.15s;
          flex-shrink: 0;
        }
        .burger-btn:hover { background: rgba(255,255,255,0.06); color: #fff; }
        .breadcrumb {
          font-size: 13px;
          color: var(--text-muted);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .breadcrumb-root { color: var(--text-muted); }
        .breadcrumb-sep { color: var(--text-muted); opacity: 0.5; }
        .breadcrumb-active {
          color: var(--text-primary);
          font-weight: 600;
        }
        .top-bar-right {
          display: flex;
          align-items: center;
          gap: 16px;
          flex-shrink: 0;
        }

        /* ── Search ──────────────────────────────────────────── */
        .top-bar-search {
          display: flex;
          align-items: center;
          gap: 10px;
          background: rgba(255,255,255,0.04);
          padding: 6px 14px;
          border-radius: 100px;
          border: 1px solid rgba(255,255,255,0.08);
          width: 280px;
          position: relative;
          transition: 0.2s;
        }
        .top-bar-search:focus-within {
          border-color: rgba(212,168,67,0.3);
          background: rgba(255,255,255,0.06);
        }
        .search-icon { display: flex; align-items: center; flex-shrink: 0; }
        .search-spinner {
          width: 14px; height: 14px;
          border: 2px solid rgba(255,255,255,0.15);
          border-top-color: var(--gold-400);
          border-radius: 50%;
          animation: spin 0.7s linear infinite;
          display: inline-block;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .search-input {
          background: none; border: none; color: #fff;
          font-size: 13px; outline: none; width: 100%;
        }
        .search-input::placeholder { color: var(--text-muted); }

        /* ── Search results ──────────────────────────────────── */
        .search-results {
          position: absolute;
          top: calc(100% + 10px);
          left: 0; right: 0;
          background: #0d1a2e;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 14px;
          box-shadow: 0 20px 50px rgba(0,0,0,0.6);
          overflow: hidden;
          z-index: 1000;
          max-height: 420px;
          overflow-y: auto;
          animation: fadeIn 0.12s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
        .result-section {
          padding: 10px 0;
          border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .result-section:last-child { border-bottom: none; }
        .result-label {
          font-size: 10px; font-weight: 800; text-transform: uppercase;
          color: #64748b; padding: 0 14px 6px; letter-spacing: 1px;
        }
        .result-item {
          display: flex; align-items: center; gap: 8px;
          padding: 8px 14px; font-size: 13px;
          color: #94a3b8; cursor: pointer;
          transition: 0.15s;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .result-item:hover { background: rgba(255,255,255,0.05); color: #fff; }
        .result-meta { margin-left: auto; font-size: 11px; color: var(--text-muted); flex-shrink: 0; }

        /* ── Notification btn ────────────────────────────────── */
        .notification-btn {
          background: none; border: none;
          color: var(--text-muted);
          cursor: pointer; padding: 7px;
          border-radius: 10px;
          display: flex; align-items: center;
          transition: 0.15s;
        }
        .notification-btn:hover { color: #fff; background: rgba(255,255,255,0.06); }

        /* ── Mobile ──────────────────────────────────────────── */
        .sidebar-overlay { display: none; }

        @media (max-width: 1024px) {
          .sidebar {
            position: fixed;
            left: -260px;
            transition: left 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 200;
          }
          .sidebar.sidebar-open { left: 0; }
          .sidebar-overlay {
            display: block;
            position: fixed; inset: 0;
            background: rgba(0,0,0,0.55);
            z-index: 199;
            backdrop-filter: blur(2px);
          }
          .sidebar-mobile-close { display: flex; }
          .burger-btn { display: flex; }
          .main-content { margin-left: 0 !important; }
          .top-bar-search { width: 200px; }
        }

        @media (max-width: 640px) {
          .top-bar { padding: 0 16px; }
          .top-bar-search { width: 160px; }
          .page-content { padding: 16px !important; }
        }
      `}</style>
    </div>
  );
}
