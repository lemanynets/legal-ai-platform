"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getCurrentSubscription } from "@/lib/api";
import { getSession, getToken, initAuth, logout, updateSessionPlan, type UserSession } from "@/lib/auth";

type NavItem = {
  section?: string;
  href?: string;
  id?: string;
  icon?: string;
  label?: string;
  badge?: string;
  subItems?: { href: string; label: string; badge?: string }[];
};

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", icon: "⬡", label: "Головна (Дашборд)" },
  
  { 
    id: "workspace", icon: "📁", label: "Мої Справи",
    subItems: [
      { href: "/dashboard/cases", label: "Усі справи" },
      { href: "/dashboard/documents", label: "Архів Документів" },
      { href: "/dashboard/knowledge-base", label: "База знань", badge: "NEW" },
    ]
  },

  { 
    id: "ai_tools", icon: "⚡", label: "AI Юрист",
    subItems: [
       { href: "/dashboard/generate", label: "Драфтер (Документи)" },
       { href: "/dashboard/auto-process", label: "Автообробка (Пакет)", badge: "PRO+" },
       { href: "/dashboard/analyze", label: "AI Аналізатор (Усі види)" },
    ]
  },
  
  { 
    id: "legal_tools", icon: "🔎", label: "Інструменти",
    subItems: [
       { href: "/dashboard/case-law", label: "Судова практика" },
       { href: "/dashboard/registries", label: "Реєстр судових справ", badge: "NEW" },
       { href: "/dashboard/monitoring", label: "Контрагенти та Моніторинг", badge: "PRO+" },
       { href: "/dashboard/calendar", label: "Календар та Строки" },
    ]
  },


  { href: "/dashboard/e-court", icon: "🏛️", label: "Е-Суд", badge: "PRO+" },
  
  { 
    id: "settings", icon: "⚙️", label: "Управління",
    subItems: [
      { href: "/dashboard/profile", label: "Налаштування акаунта" },
      { href: "/dashboard/reports", label: "Аналітика та Звіти" },
      { href: "/dashboard/team", label: "Моя команда" },
      { href: "/dashboard/forum", label: "Форум юристів", badge: "NEW" },
    ]
  }
];

const PLAN_LABELS: Record<string, string> = {
  FREE: "FREE",
  PRO: "PRO",
  PRO_PLUS: "PRO+",
  TEAM: "TEAM",
};

function planBadgeText(plan: string): string {
  return PLAN_LABELS[plan] || plan || "FREE";
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<UserSession | null>(null);
  const [plan, setPlan] = useState("FREE");
  
  const [expandedMenus, setExpandedMenus] = useState<Record<string, boolean>>({
    drafter: false, analyst: false, radar: false, settings: false
  });

  const toggleMenu = (id: string) => {
    setExpandedMenus(prev => ({ ...prev, [id]: !prev[id] }));
  };

  useEffect(() => {
    NAV_ITEMS.forEach(item => {
      if (item.subItems && item.subItems.some(sub => pathname === sub.href)) {
        setExpandedMenus(prev => ({ ...prev, [item.id!]: true }));
      }
    });
  }, [pathname]);

  useEffect(() => {
    let isActive = true;

    async function bootstrap(): Promise<void> {
      await initAuth();
      const currentSession = getSession();
      if (!isActive) return;

      setSession(currentSession);
      setPlan(currentSession?.plan ?? "FREE");

      if (!currentSession) return;

      const subscription = await getCurrentSubscription(currentSession.token, currentSession.user_id).catch(() => null);
      if (!isActive || !subscription) return;

      const nextPlan = subscription.plan || currentSession.plan || "FREE";
      setPlan(nextPlan);
      updateSessionPlan(nextPlan);
      setSession((previous) => (previous ? { ...previous, plan: nextPlan } : previous));
    }

    void bootstrap();

    return () => {
      isActive = false;
    };
  }, []);

  const displayEmail = session?.email || null;
  const displayName = useMemo(() => displayEmail?.split("@")[0] || "Користувач", [displayEmail]);
  const avatarLetter = displayName[0]?.toUpperCase() || "U";

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults(null);
      setShowResults(false);
      return;
    }
    const timer = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const { globalSearch } = await import("@/lib/api");
        const results = await globalSearch(searchQuery, getToken());
        setSearchResults(results);
        setShowResults(true);
      } catch (err) { console.error(err); }
      finally { setSearchLoading(false); }
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const onLogout = async (): Promise<void> => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="app-shell" onClick={() => setShowResults(false)}>
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">⚖</div>
          <div className="sidebar-header-text">
            <div className="sidebar-logo-text">LEGAL AI</div>
            <div className="sidebar-logo-sub">Леманинець та партнери</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item, index) => {
            if (item.section) {
              return (
                <div key={`${item.section}-${index}`} className="nav-section-label">
                  {item.section}
                </div>
              );
            }

            if (item.subItems) {
               const isOpen = expandedMenus[item.id!];
               const hasActiveChild = item.subItems.some(s => pathname === s.href);
               return (
                 <div key={item.id} className="nav-accordion">
                   <div 
                     className={`nav-link ${hasActiveChild && !isOpen ? "active-parent" : ""}`}
                     onClick={() => toggleMenu(item.id!)}
                     style={{ cursor: 'pointer', justifyContent: 'space-between' }}
                   >
                     <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                       <span className="nav-link-icon">{item.icon}</span>
                       <span className="nav-link-label">{item.label}</span>
                     </div>
                     <span style={{ fontSize: '10px', opacity: isOpen ? 0.9 : 0.3, transform: isOpen ? 'rotate(180deg)' : 'none', transition: '0.2s', paddingRight: '8px' }}>▼</span>
                   </div>
                   {isOpen && (
                     <div className="nav-subitems">
                       {item.subItems.map(subItem => {
                         const active = pathname === subItem.href;
                         return (
                           <Link key={subItem.href} href={subItem.href} className={`nav-sublink ${active ? "active" : ""}`}>
                             <span className="nav-sublink-label">{subItem.label}</span>
                             {subItem.badge && <span className="nav-badge" style={{ transform: 'scale(0.8)', marginLeft: 'auto' }}>{subItem.badge}</span>}
                           </Link>
                         );
                       })}
                     </div>
                   )}
                 </div>
               );
            }

            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href!} className={`nav-link ${active ? "active" : ""}`}>
                <span className="nav-link-icon">{item.icon}</span>
                <span className="nav-link-label">{item.label}</span>
                {item.badge && <span className="nav-badge">{item.badge}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user" onClick={() => router.push("/dashboard/billing")}>
            <div className="sidebar-avatar">{avatarLetter}</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-name truncate">{displayName}</div>
              <div className="sidebar-user-plan">{planBadgeText(plan)}</div>
            </div>
          </div>
          <button onClick={onLogout} className="btn-logout" title="Вийти">
            🚪
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="top-bar">
          <div className="top-bar-left">
            <div className="breadcrumb">
              Dashboard / <span className="breadcrumb-active">{pathname.split("/").pop()}</span>
            </div>
          </div>
          <div className="top-bar-right">
            <div className="top-bar-search" onClick={(e) => e.stopPropagation()}>
              <span className="search-icon">{searchLoading ? "⌛" : "🔍"}</span>
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
                  {searchResults.cases.length > 0 && (
                    <div className="result-section">
                      <div className="result-label">Справи</div>
                      {searchResults.cases.map((c: any) => (
                        <div key={c.id} className="result-item" onClick={() => { router.push(`/dashboard/cases?id=${c.id}`); setShowResults(false); }}>
                          <span className="text-gold">📁</span> {c.title} <span className="text-muted ml-2">{c.number}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {searchResults.documents.length > 0 && (
                    <div className="result-section">
                      <div className="result-label">Документи</div>
                      {searchResults.documents.map((d: any) => (
                        <div key={d.id} className="result-item" onClick={() => { router.push(`/dashboard/documents?id=${d.id}`); setShowResults(false); }}>
                          📄 {d.type}
                        </div>
                      ))}
                    </div>
                  )}
                  {searchResults.forum.length > 0 && (
                    <div className="result-section">
                      <div className="result-label">Форум</div>
                      {searchResults.forum.map((p: any) => (
                        <div key={p.id} className="result-item" onClick={() => { router.push(`/dashboard/forum/post/${p.id}`); setShowResults(false); }}>
                          💬 {p.title}
                        </div>
                      ))}
                    </div>
                  )}
                  {!searchResults.cases.length && !searchResults.documents.length && !searchResults.forum.length && (
                    <div className="p-4 text-center text-muted text-xs">Нічого не знайдено</div>
                  )}
                </div>
              )}
            </div>
            <div className="notification-bell">🔔</div>
          </div>
        </header>
        <div className="page-content">{children}</div>
      </main>

      <style jsx>{`
        .sidebar {
          width: 260px;
        }
        .sidebar-header-text {
          display: flex;
          flex-direction: column;
        }
        .btn-logout {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 18px;
          opacity: 0.5;
          transition: opacity 0.2s;
        }
        .btn-logout:hover {
          opacity: 1;
        }
        .sidebar-user-info {
          flex: 1;
          overflow: hidden;
        }
        
        .nav-accordion { margin-bottom: 2px; }
        .nav-subitems { padding: 4px 0 4px 34px; display: flex; flex-direction: column; gap: 4px; border-left: 1px solid rgba(255,255,255,0.06); margin-left: 28px; margin-top: 4px; margin-bottom: 8px; }
        .nav-sublink { display: flex; align-items: center; padding: 8px 16px; font-size: 13px; color: #cbd5e1 !important; text-decoration: none !important; border-radius: 8px; transition: 0.2s; }
        .nav-sublink:hover { color: #fff !important; background: rgba(255,255,255,0.03); }
        .nav-sublink.active { color: var(--gold-400) !important; background: rgba(212,168,67,0.05); font-weight: 600; text-shadow: 0 0 10px rgba(212,168,67,0.3); }
        .active-parent { color: #fff; border-left: 2px solid var(--gold-500); padding-left: 22px; background: rgba(212,168,67,0.05); }

        .top-bar {
          height: 64px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 32px;
          background: rgba(11, 22, 40, 0.4);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          position: sticky;
          top: 0;
          z-index: 50;
        }
        .breadcrumb {
          font-size: 13px;
          color: var(--text-muted);
        }
        .breadcrumb-active {
          color: var(--text-primary);
          font-weight: 600;
          text-transform: capitalize;
        }
        .top-bar-right {
          display: flex;
          align-items: center;
          gap: 24px;
        }
        .top-bar-search {
          display: flex;
          align-items: center;
          gap: 10px;
          background: rgba(255, 255, 255, 0.04);
          padding: 6px 16px;
          border-radius: 100px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          width: 300px;
          position: relative;
        }
        .search-results {
          position: absolute;
          top: calc(100% + 12px);
          left: 0;
          right: 0;
          background: #0b1628;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 16px;
          box-shadow: 0 20px 50px rgba(0,0,0,0.5);
          overflow: hidden;
          z-index: 1000;
          max-height: 440px;
          overflow-y: auto;
          animation: fadeIn 0.15s ease-out;
        }
        .result-section {
          padding: 12px 0;
          border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .result-section:last-child { border-bottom: none; }
        .result-label {
          font-size: 10px;
          font-weight: 800;
          text-transform: uppercase;
          color: #64748b;
          padding: 0 16px 8px;
          letter-spacing: 1px;
        }
        .result-item {
          padding: 10px 16px;
          font-size: 13px;
          color: #94a3b8;
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .result-item:hover {
          background: rgba(255,255,255,0.05);
          color: #fff;
        }
        .ml-2 { margin-left: 8px; }
        .search-icon {
          font-size: 14px;
          opacity: 0.5;
        }
        .search-input {
          background: none;
          border: none;
          color: #fff;
          font-size: 13px;
          outline: none;
          width: 100%;
        }
        .notification-bell {
          font-size: 18px;
          cursor: pointer;
          opacity: 0.7;
        }
        .notification-bell:hover {
          opacity: 1;
        }
      `}</style>
    </div>
  );
}
