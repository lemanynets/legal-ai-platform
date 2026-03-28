"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  FileText,
  Bot,
  Scale,
  Calculator,
  TrendingUp,
  CreditCard,
  BookOpen,
  Activity,
  Clock,
  ArrowRight,
  FileCheck,
  AlertCircle,
  Sparkles,
} from "lucide-react";

import { getCurrentSubscription, getDocumentsHistory, type DocumentHistoryItem } from "@/lib/api";
import { getSession, getToken, getUserId, initAuth, type UserSession, updateSessionPlan } from "@/lib/auth";

// ---------------------------------------------------------------------------
// Quick actions
// ---------------------------------------------------------------------------
const QUICK_ACTIONS = [
  { href: "/dashboard/generate",    label: "Генерація документа", icon: FileText,    color: "#3b82f6" },
  { href: "/dashboard/full-lawyer", label: "Повний юрист",        icon: Scale,       color: "#8b5cf6" },
  { href: "/dashboard/analyze",     label: "AI Аналізатор",       icon: Bot,         color: "#10b981" },
  { href: "/dashboard/calculators", label: "Калькулятори",        icon: Calculator,  color: "#f59e0b" },
];

// ---------------------------------------------------------------------------
// Doc type → Ukrainian label
// ---------------------------------------------------------------------------
const DOC_TYPE_LABELS: Record<string, string> = {
  pozov_do_sudu: "Позов до суду",
  pozov_trudovyi: "Трудовий позов",
  appeal_complaint: "Апеляційна скарга",
  zaява_do_sudu: "Заява до суду",
  skarha_administratyvna: "Адміністративна скарга",
  dohovir_kupivli_prodazhu: "Договір купівлі-продажу",
  dohovir_orendi: "Договір оренди",
  dohovir_nadannia_posluh: "Договір послуг",
  pretenziya: "Претензія",
  dovirennist: "Довіреність",
};

function docTypeLabel(type: string): string {
  return DOC_TYPE_LABELS[type] ?? type;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return "щойно";
  if (mins < 60) return `${mins} хв тому`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} год тому`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days} дн тому`;
  return new Date(dateStr).toLocaleDateString("uk-UA", { day: "numeric", month: "short" });
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------
export default function DashboardPage() {
  const [session, setSession] = useState<UserSession | null>(null);
  const [plan, setPlan] = useState("FREE");
  const [usage, setUsage] = useState<{ used: number; limit: number | null } | null>(null);
  const [recentDocs, setRecentDocs] = useState<DocumentHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [docsLoading, setDocsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      await initAuth();
      const s = getSession();
      if (!active) return;
      setSession(s);
      setPlan(s?.plan ?? "FREE");

      if (!s) { setLoading(false); return; }

      // Subscription + usage
      const sub = await getCurrentSubscription(getToken(), getUserId()).catch(() => null);
      if (active && sub) {
        const next = sub.plan ?? s.plan ?? "FREE";
        setPlan(next);
        updateSessionPlan(next);
        setUsage({ used: sub.usage?.docs_used ?? 0, limit: sub.usage?.docs_limit ?? null });
      }
      setLoading(false);

      // Recent documents (last 5)
      try {
        const hist = await getDocumentsHistory({ page_size: 5 } as any, getToken());
        if (active) setRecentDocs(hist.items ?? []);
      } catch { /* ignore */ } finally { if (active) setDocsLoading(false); }
    }

    void bootstrap();
    return () => { active = false; };
  }, []);

  const greeting = (): string => {
    const h = new Date().getHours();
    if (h < 12) return "Доброго ранку";
    if (h < 18) return "Доброго дня";
    return "Доброго вечора";
  };

  const firstName = session?.name?.split(/\s+/)[0] ?? "юристе";
  const usageLimitLabel = usage?.limit == null ? "∞" : String(usage.limit);
  const usagePercent = usage?.limit ? Math.min(100, (usage.used / usage.limit) * 100) : 0;
  const usageDanger = usage?.limit != null && usage.used >= usage.limit;

  return (
    <div>
      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="section-header">
        <div>
          <h1 className="section-title">{greeting()}, {firstName}</h1>
          <p className="section-subtitle">Огляд поточного тарифу, лімітів і швидких дій.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span className={`badge ${plan === "FREE" ? "badge-muted" : plan === "PRO" ? "badge-blue" : "badge-gold"}`}>
            {plan}
          </span>
          {plan === "FREE" && (
            <Link href="/dashboard/billing" className="btn btn-primary btn-sm">
              Оновити план
            </Link>
          )}
        </div>
      </div>

      {/* ── Stat cards ───────────────────────────────────────────────── */}
      <div className="grid-4" style={{ marginBottom: "28px" }}>

        {/* Документи */}
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(59,130,246,0.1)", borderColor: "rgba(59,130,246,0.18)" }}>
            <FileText size={20} color="#3b82f6" />
          </div>
          <div className="stat-value">{loading ? "—" : usage?.used ?? 0}</div>
          <div className="stat-label">Документів цього місяця</div>
          {usage && (
            <div style={{ marginTop: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                <span className="text-xs text-muted">{usage.used} / {usageLimitLabel}</span>
                {usageDanger && (
                  <span style={{ fontSize: "11px", color: "var(--danger)", display: "flex", alignItems: "center", gap: "3px" }}>
                    <AlertCircle size={11} /> Ліміт
                  </span>
                )}
              </div>
              <div style={{ height: "4px", background: "var(--border-strong)", borderRadius: "2px", overflow: "hidden" }}>
                <div style={{
                  height: "100%", width: `${usagePercent}%`, borderRadius: "2px",
                  background: usageDanger ? "var(--danger)" : "var(--gold-500)",
                  transition: "width 0.4s ease",
                }} />
              </div>
            </div>
          )}
        </div>

        {/* Тариф */}
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(212,168,67,0.1)", borderColor: "rgba(212,168,67,0.2)" }}>
            <CreditCard size={20} color="var(--gold-400)" />
          </div>
          <div className="stat-value">{plan}</div>
          <div className="stat-label">Поточний тариф</div>
          <Link href="/dashboard/billing" className="stat-action-link">
            Керування підпискою <ArrowRight size={12} />
          </Link>
        </div>

        {/* Судова практика */}
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(139,92,246,0.1)", borderColor: "rgba(139,92,246,0.18)" }}>
            <BookOpen size={20} color="#8b5cf6" />
          </div>
          <div className="stat-value">ВС</div>
          <div className="stat-label">Судова практика</div>
          <Link href="/dashboard/case-law" className="stat-action-link">
            Відкрити практику <ArrowRight size={12} />
          </Link>
        </div>

        {/* Моніторинг */}
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(16,185,129,0.1)", borderColor: "rgba(16,185,129,0.18)" }}>
            <Activity size={20} color="#10b981" />
          </div>
          <div className="stat-value" style={{ color: plan === "PRO_PLUS" ? "var(--success)" : "var(--text-muted)" }}>
            {plan === "PRO_PLUS" ? "Активний" : "PRO+"}
          </div>
          <div className="stat-label">Реєстровий моніторинг</div>
          <Link href="/dashboard/monitoring" className="stat-action-link">
            {plan === "PRO_PLUS" ? "Переглянути" : "Дізнатися більше"} <ArrowRight size={12} />
          </Link>
        </div>
      </div>

      {/* ── Quick actions ─────────────────────────────────────────────── */}
      <div style={{ marginBottom: "28px" }}>
        <h2 className="section-heading">Швидкі дії</h2>
        <div className="grid-4">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <Link key={action.href} href={action.href} className="card-elevated card-hover quick-action-card">
                <div className="quick-action-icon" style={{
                  background: `${action.color}18`,
                  border: `1px solid ${action.color}30`,
                }}>
                  <Icon size={22} color={action.color} />
                </div>
                <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
                  {action.label}
                </div>
                <div className="quick-action-arrow">
                  <ArrowRight size={14} color={action.color} />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* ── Bottom grid ───────────────────────────────────────────────── */}
      <div className="grid-2">

        {/* Останні документи — реальні дані */}
        <div className="card-elevated" style={{ padding: "24px" }}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="card-heading">
              <FileCheck size={16} style={{ color: "var(--gold-400)" }} />
              Останні документи
            </h2>
            <Link href="/dashboard/documents" className="text-sm text-gold">
              Усі
            </Link>
          </div>

          {docsLoading ? (
            <div className="docs-skeleton">
              {[1,2,3].map(i => <div key={i} className="skeleton-row" />)}
            </div>
          ) : recentDocs.length === 0 ? (
            <div className="empty-state">
              <Sparkles size={32} opacity={0.3} />
              <p>Документів ще немає</p>
              <Link href="/dashboard/generate" className="btn btn-primary btn-sm">
                Створити перший документ
              </Link>
            </div>
          ) : (
            <div className="recent-docs-list">
              {recentDocs.map((doc) => (
                <Link key={doc.id} href={`/dashboard/documents?id=${doc.id}`} className="recent-doc-item">
                  <div className="recent-doc-icon">
                    <FileText size={14} />
                  </div>
                  <div className="recent-doc-info">
                    <div className="recent-doc-type">{docTypeLabel(doc.document_type)}</div>
                    {doc.preview_text && (
                      <div className="recent-doc-preview">{doc.preview_text.slice(0, 60)}…</div>
                    )}
                  </div>
                  <div className="recent-doc-meta">
                    <Clock size={11} />
                    {timeAgo(doc.created_at)}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Ваш план */}
        <div className="card-elevated" style={{ padding: "24px" }}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="card-heading">
              <TrendingUp size={16} style={{ color: "var(--gold-400)" }} />
              Ваш план
            </h2>
            <Link href="/dashboard/billing" className="text-sm text-gold">
              Змінити
            </Link>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {[
              { label: "Тариф",                   value: plan, highlight: true },
              { label: "Статус",                  value: "Активний" },
              { label: "Генерація документів",    value: plan === "FREE" ? "5/міс" : plan === "PRO" ? "50/міс" : "Необмежено" },
              { label: "Судова практика",         value: plan !== "FREE" ? "Так" : "—" },
              { label: "Реєстровий моніторинг",   value: plan === "PRO_PLUS" ? "Так" : "—" },
              { label: "Е-Суд інтеграція",        value: plan === "PRO_PLUS" ? "Так" : "—" },
            ].map(({ label, value, highlight }) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>{label}</span>
                <span style={{
                  fontSize: "13px", fontWeight: 600,
                  color: value === "Так" ? "var(--success)"
                       : value === "—" ? "var(--text-muted)"
                       : highlight ? "var(--gold-400)"
                       : "var(--text-secondary)",
                }}>
                  {value}
                </span>
              </div>
            ))}
          </div>

          {plan === "FREE" && (
            <Link href="/dashboard/billing" className="btn btn-primary w-full" style={{ marginTop: "20px" }}>
              Оновити до PRO
            </Link>
          )}
        </div>
      </div>

      <style jsx>{`
        .section-heading {
          font-size: 15px; font-weight: 700;
          margin-bottom: 14px; color: var(--text-primary);
        }
        .card-heading {
          font-size: 15px; font-weight: 700;
          color: var(--text-primary);
          display: flex; align-items: center; gap: 8px;
        }
        .stat-icon-wrap {
          width: 44px; height: 44px; border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          margin-bottom: 14px; border: 1px solid transparent;
        }
        .stat-action-link {
          display: flex; align-items: center; gap: 4px;
          font-size: 12px; color: var(--gold-400);
          margin-top: 8px; text-decoration: none;
          transition: 0.15s;
        }
        .stat-action-link:hover { color: var(--gold-300); }

        /* Quick action card */
        .quick-action-card {
          padding: 20px; text-decoration: none;
          display: flex; flex-direction: column; gap: 8px;
          position: relative; overflow: hidden;
        }
        .quick-action-icon {
          width: 48px; height: 48px; border-radius: 14px;
          display: flex; align-items: center; justify-content: center;
          margin-bottom: 4px;
        }
        .quick-action-arrow {
          position: absolute; top: 18px; right: 18px;
          opacity: 0; transition: 0.2s;
          transform: translateX(-4px);
        }
        .quick-action-card:hover .quick-action-arrow {
          opacity: 1; transform: none;
        }

        /* Recent docs */
        .recent-docs-list { display: flex; flex-direction: column; gap: 4px; }
        .recent-doc-item {
          display: flex; align-items: center; gap: 10px;
          padding: 9px 12px; border-radius: 10px;
          text-decoration: none; transition: 0.15s;
        }
        .recent-doc-item:hover { background: rgba(255,255,255,0.04); }
        .recent-doc-icon {
          width: 30px; height: 30px; border-radius: 8px;
          background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.15);
          display: flex; align-items: center; justify-content: center;
          color: #3b82f6; flex-shrink: 0;
        }
        .recent-doc-info { flex: 1; min-width: 0; }
        .recent-doc-type {
          font-size: 13px; font-weight: 600; color: var(--text-primary);
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .recent-doc-preview {
          font-size: 11px; color: var(--text-muted);
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
          margin-top: 2px;
        }
        .recent-doc-meta {
          display: flex; align-items: center; gap: 4px;
          font-size: 11px; color: var(--text-muted);
          flex-shrink: 0; white-space: nowrap;
        }

        /* Skeleton */
        .docs-skeleton { display: flex; flex-direction: column; gap: 8px; }
        .skeleton-row {
          height: 44px; border-radius: 10px;
          background: linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.07) 50%, rgba(255,255,255,0.04) 100%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

        /* Empty state */
        .empty-state {
          display: flex; flex-direction: column; align-items: center;
          gap: 12px; padding: 24px 16px; color: var(--text-muted);
          font-size: 13px; text-align: center;
        }
      `}</style>
    </div>
  );
}
