"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  LayoutDashboard, FolderOpen, FileText, Zap, FilePlus, ScanSearch,
  Search, BookOpen, Users2, Scale, BarChart3, MessageSquare, Settings,
  Gavel, CalendarDays, Calculator, Landmark, ChevronDown, LogOut,
  Bell, CreditCard, X, Menu, Target, Database, Clock, UserCircle,
  BarChart2, SlidersHorizontal, FileStack,
} from "lucide-react";

import { getCurrentSubscription } from "@/lib/api";
import { getSession, getToken, initAuth, logout, updateSessionPlan, type UserSession } from "@/lib/auth";

// ---------------------------------------------------------------------------
// Route → Ukrainian name
// ---------------------------------------------------------------------------
const ROUTE_NAMES: Record<string, string> = {
  dashboard: "Головна",
  cases: "Мої справи",
  documents: "Документи",
  "knowledge-base": "База знань",
  knowledge: "База знань",
  generate: "Генерація документів",
  "auto-process": "Автообробка",
  analyze: "AI Аналізатор",
  "case-law": "Судова практика",
  registries: "Реєстри",
  monitoring: "Моніторинг",
  calendar: "Календар",
  deadlines: "Строки",
  "e-court": "Е-Суд",
  profile: "Профіль",
  reports: "Звіти",
  team: "Команда",
  forum: "Форум юристів",
  billing: "Тариф і оплата",
  calculators: "Калькулятори",
  "full-lawyer": "Повний юрист",
  "strategy-studio": "Стратегія Студіо",
  audit: "Аудит",
  "decision-analysis": "Аналіз рішень",
  settings: "Налаштування",
};

// ---------------------------------------------------------------------------
// Navigation tree
// ---------------------------------------------------------------------------
type SubItem = { href: string; label: string; badge?: string };
type NavItem =
  | { type: "link"; href: string; icon: React.ReactNode; label: string; badge?: string }
  | { type: "group"; id: string; icon: React.ReactNode; label: string; subItems: SubItem[] };

const NAV_ITEMS: NavItem[] = [
  {
    type: "link",
    href: "/dashboard",
    icon: <LayoutDashboard size={17} />,
    label: "Головна",
  },
  {
    type: "group",
    id: "workspace",
    icon: <FolderOpen size={17} />,
    label: "Справи",
    subItems: [
      { href: "/dashboard/cases",     label: "Всі справи" },
      { href: "/dashboard/documents", label: "Документи" },
    ],
  },
  {
    type: "group",
    id: "ai_tools",
    icon: <Zap size={17} />,
    label: "AI Інструменти",
    subItems: [
      { href: "/dashboard/generate",        label: "Генерація документів" },
      { href: "/dashboard/analyze",         label: "AI Аналізатор" },
      { href: "/dashboard/strategy-studio", label: "Стратегія" },
      { href: "/dashboard/full-lawyer",     label: "Повний юрист" },
      { href: "/dashboard/auto-process",    label: "Автообробка", badge: "PRO+" },
    ],
  },
  {
    type: "group",
    id: "research",
    icon: <Search size={17} />,
    label: "Дослідження",
    subItems: [
      { href: "/dashboard/case-law",          label: "Судова практика" },
      { href: "/dashboard/registries",        label: "Реєстри",         badge: "NEW" },
      { href: "/dashboard/monitoring",        label: "Моніторинг",      badge: "PRO+" },
      { href: "/dashboard/knowledge-base",    label: "База знань",      badge: "NEW" },
      { href: "/dashboard/decision-analysis", label: "Аналіз рішень" },
    ],
  },
  {
    type: "group",
    id: "control",
    icon: <CalendarDays size={17} />,
    label: "Контроль",
    subItems: [
      { href: "/dashboard/calendar",    label: "Календар" },
      { href: "/dashboard/deadlines",   label: "Строки" },
      { href: "/dashboard/calculators", label: "Калькулятори" },
    ],
  },
  {
    type: "link",
    href: "/dashboard/e-court",
    icon: <Landmark size={17} />,
    label: "Е-Суд",
    badge: "PRO+",
  },
  {
    type: "group",
    id: "management",
    icon: <Settings size={17} />,
    label: "Управління",
    subItems: [
      { href: "/dashboard/profile",   label: "Профіль" },
      { href: "/dashboard/billing",   label: "Тариф і оплата" },
      { href: "/dashboard/team",      label: "Команда" },
      { href: "/dashboard/reports",   label: "Звіти" },
      { href: "/dashboard/settings",  label: "Налаштування" },
    ],
  },
  {
    type: "link",
    href: "/dashboard/forum",
    icon: <MessageSquare size={17} />,
    label: "Форум",
    badge: "NEW",
  },
];

const PLAN_LABELS: Record<string, string> = {
  FREE: "FREE", PRO: "PRO", PRO_PLUS: "PRO+", TEAM: "TEAM",
};

// ---------------------------------------------------------------------------
// AppShell
// ---------------------------------------------------------------------------
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<UserSession | null>(null);
  const [plan, setPlan] = useState("FREE");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [expandedMenus, setExpandedMenus] = useState<Record<string, boolean>>({
    workspace: false, ai_tools: false, research: false, control: false, management: false,
  });

  const toggleMenu = (id: string) =>
    setExpandedMenus((prev) => ({ ...prev, [id]: !prev[id] }));

  // Auto-expand active group
  useEffect(() => {
    NAV_ITEMS.forEach((item) => {
      if (item.type === "group" && item.subItems.some((s) => pathname.startsWith(s.href))) {
        setExpandedMenus((prev) => ({ ...prev, [item.id]: true }));
      }
    });
  }, [pathname]);

  useEffect(() => setSidebarOpen(false), [pathname]);

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
    [session?.email],
  );
  const avatarLetter = displayName[0]?.toUpperCase() || "U";
  const planLabel = PLAN_LABELS[plan] || plan || "FREE";

  // Search
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

  const onLogout = async () => {
    if (!window.confirm("Вийти з акаунта?")) return;
    await logout();
    router.push("/login");
  };

  const routeSlug = pathname.split("/").filter(Boolean).pop() ?? "dashboard";
  const breadcrumbName = ROUTE_NAMES[routeSlug] ?? routeSlug;

  return (
    <div className="app-shell" onClick={() => setShowResults(false)}>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside className={`sidebar${sidebarOpen ? " sidebar-open" : ""}`}>
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <Scale size={20} color="var(--navy-950)" />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="sidebar-logo-text">LEGAL AI</div>
            <div className="sidebar-logo-sub">Електронний юрист</div>
          </div>
          <button className="sidebar-mobile-close" onClick={() => setSidebarOpen(false)}>
            <X size={16} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => {
            if (item.type === "link") {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`nav-link${active ? " active" : ""}`}
                >
                  <span className="nav-link-icon">{item.icon}</span>
                  <span className="nav-link-label">{item.label}</span>
                  {item.badge && <span className="nav-badge">{item.badge}</span>}
                </Link>
              );
            }

            const isOpen = expandedMenus[item.id];
            const hasActive = item.subItems.some((s) => pathname.startsWith(s.href));
            return (
              <div key={item.id} className="nav-accordion">
                <div
                  className={`nav-link${hasActive && !isOpen ? " active-parent" : ""}`}
                  onClick={() => toggleMenu(item.id)}
                  style={{ justifyContent: "space-between" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span className="nav-link-icon">{item.icon}</span>
                    <span className="nav-link-label">{item.label}</span>
                  </div>
                  <ChevronDown
                    size={13}
                    style={{
                      flexShrink: 0,
                      opacity: isOpen ? 0.8 : 0.3,
                      transform: isOpen ? "rotate(180deg)" : "none",
                      transition: "transform 0.2s, opacity 0.2s",
                      marginRight: "4px",
                    }}
                  />
                </div>
                {isOpen && (
                  <div className="nav-subitems">
                    {item.subItems.map((sub) => {
                      const active = pathname.startsWith(sub.href);
                      return (
                        <Link
                          key={sub.href}
                          href={sub.href}
                          className={`nav-sublink${active ? " active" : ""}`}
                        >
                          <span className="nav-sublink-label">{sub.label}</span>
                          {sub.badge && (
                            <span className="nav-sub-badge">{sub.badge}</span>
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
          <div
            className="sidebar-user"
            onClick={() => router.push("/dashboard/profile")}
            title="Профіль"
          >
            <div className="sidebar-avatar">{avatarLetter}</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-name truncate">{displayName}</div>
              <div className="sidebar-user-plan">{planLabel}</div>
            </div>
            <Link
              href="/dashboard/billing"
              onClick={(e) => e.stopPropagation()}
              className="sidebar-billing-btn"
              title="Тариф"
            >
              <CreditCard size={14} />
            </Link>
          </div>
          <button onClick={onLogout} className="btn-logout">
            <LogOut size={14} />
            <span>Вийти</span>
          </button>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main className="main-content">
        {/* Topbar */}
        <header className="top-bar">
          <div className="top-bar-left">
            <button className="burger-btn" onClick={() => setSidebarOpen(true)}>
              <Menu size={19} />
            </button>
            <nav className="breadcrumb">
              <Link href="/dashboard" style={{ color: "var(--text-muted)" }}>Дашборд</Link>
              {routeSlug !== "dashboard" && (
                <>
                  <span className="breadcrumb-sep">/</span>
                  <span className="breadcrumb-active">{breadcrumbName}</span>
                </>
              )}
            </nav>
          </div>

          <div className="top-bar-right">
            {/* Search */}
            <div className="top-bar-search" onClick={(e) => e.stopPropagation()}>
              <span className="search-icon">
                {searchLoading
                  ? <span className="search-spinner" />
                  : <Search size={13} />}
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
                <div className="search-results">
                  {searchResults.cases?.length > 0 && (
                    <div className="result-section">
                      <div className="result-label">Справи</div>
                      {searchResults.cases.map((c: any) => (
                        <div key={c.id} className="result-item"
                          onClick={() => { router.push(`/dashboard/cases?id=${c.id}`); setShowResults(false); }}>
                          <FolderOpen size={12} style={{ color: "var(--gold-400)", flexShrink: 0 }} />
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
                        <div key={d.id} className="result-item"
                          onClick={() => { router.push(`/dashboard/documents?id=${d.id}`); setShowResults(false); }}>
                          <FileText size={12} style={{ flexShrink: 0 }} />
                          <span>{d.title || d.type}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {!searchResults.cases?.length && !searchResults.documents?.length && (
                    <div style={{ padding: "16px", textAlign: "center", fontSize: "13px", color: "var(--text-muted)" }}>
                      Нічого не знайдено
                    </div>
                  )}
                </div>
              )}
            </div>

            <button className="notification-btn" title="Сповіщення">
              <Bell size={17} />
            </button>
          </div>
        </header>

        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}
