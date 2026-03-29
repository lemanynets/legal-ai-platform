"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  FileText, Scale, Bot, ArrowRight, Clock, Sparkles,
  CreditCard, FileCheck, AlertCircle, FolderOpen, CalendarDays, Zap,
} from "lucide-react";

import { getCurrentSubscription, getDocumentsHistory, type DocumentHistoryItem } from "@/lib/api";
import { getSession, getToken, getUserId, initAuth, type UserSession, updateSessionPlan } from "@/lib/auth";

const QUICK_ACTIONS = [
  { href: "/dashboard/generate",        label: "Генерація документів", icon: FileText, color: "#3b82f6" },
  { href: "/dashboard/full-lawyer",     label: "Повний юрист",         icon: Scale,    color: "#8b5cf6" },
  { href: "/dashboard/analyze",         label: "AI Аналізатор",        icon: Bot,      color: "#10b981" },
  { href: "/dashboard/strategy-studio", label: "Стратегія справи",     icon: Zap,      color: "#f59e0b" },
];

const DOC_TYPE_LABELS: Record<string, string> = {
  pozov_do_sudu: "Позов до суду", pozov_trudovyi: "Трудовий позов",
  appeal_complaint: "Апеляційна скарга", dohovir_kupivli_prodazhu: "Договір купівлі-продажу",
  dohovir_orendi: "Договір оренди", dohovir_nadannia_posluh: "Договір послуг",
  pretenziya: "Претензія", dovirennist: "Довіреність",
};

function docLabel(t: string) { return DOC_TYPE_LABELS[t] ?? t.replace(/_/g, " "); }
function timeAgo(d: string) {
  const mins = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
  if (mins < 2)  return "щойно";
  if (mins < 60) return `${mins} хв тому`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs} год тому`;
  const days = Math.floor(hrs / 24);
  return days < 30 ? `${days} дн тому` : new Date(d).toLocaleDateString("uk-UA", { day: "numeric", month: "short" });
}

export default function DashboardPage() {
  const [session, setSession]         = useState<UserSession | null>(null);
  const [plan, setPlan]               = useState("FREE");
  const [usage, setUsage]             = useState<{ used: number; limit: number | null } | null>(null);
  const [recentDocs, setRecentDocs]   = useState<DocumentHistoryItem[]>([]);
  const [loading, setLoading]         = useState(true);
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
      const sub = await getCurrentSubscription(getToken(), getUserId()).catch(() => null);
      if (active && sub) {
        const next = sub.plan ?? s.plan ?? "FREE";
        setPlan(next); updateSessionPlan(next);
        setUsage({ used: sub.usage?.docs_used ?? 0, limit: sub.usage?.docs_limit ?? null });
      }
      setLoading(false);
      try {
        const hist = await getDocumentsHistory({ page_size: 5 } as any, getToken());
        if (active) setRecentDocs(hist.items ?? []);
      } catch { /**/ } finally { if (active) setDocsLoading(false); }
    }
    void bootstrap();
    return () => { active = false; };
  }, []);

  const greeting = () => {
    const h = new Date().getHours();
    return h < 12 ? "Доброго ранку" : h < 18 ? "Доброго дня" : "Доброго вечора";
  };
  const firstName   = session?.name?.split(/\s+/)[0] ?? session?.email?.split("@")[0] ?? "юристе";
  const usageLimit  = usage?.limit == null ? "∞" : String(usage.limit);
  const usagePct    = usage?.limit ? Math.min(100, (usage.used / usage.limit) * 100) : 0;
  const usageDanger = usage?.limit != null && usage.used >= usage.limit;

  return (
    <div>
      {/* Greeting */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px", gap: "16px", flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#fff", letterSpacing: "-0.03em", marginBottom: "3px" }}>
            {greeting()}, {firstName}
          </h1>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            {new Date().toLocaleDateString("uk-UA", { weekday: "long", day: "numeric", month: "long" })}
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
          <Link href="/dashboard/cases" className="btn btn-secondary btn-sm">+ Нова справа</Link>
          <Link href="/dashboard/generate" className="btn btn-primary btn-sm">Генерувати документ</Link>
        </div>
      </div>

      {/* KPI row */}
      <div className="kpi-row">
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(59,130,246,0.08)", borderColor: "rgba(59,130,246,0.14)" }}>
            <FileText size={17} color="#3b82f6" />
          </div>
          <div className="stat-value">{loading ? "—" : (usage?.used ?? 0)}</div>
          <div className="stat-label">Документів цього місяця</div>
          {usage && (
            <div style={{ marginTop: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "3px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{usage.used} / {usageLimit}</span>
                {usageDanger && (
                  <span style={{ fontSize: "11px", color: "var(--danger)", display: "flex", alignItems: "center", gap: "3px" }}>
                    <AlertCircle size={10} /> Ліміт
                  </span>
                )}
              </div>
              <div className={"usage-bar-wrap" + (usageDanger ? " usage-bar-danger" : "")}>
                <div className="usage-bar-fill" style={{ width: usagePct + "%" }} />
              </div>
            </div>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(212,168,67,0.08)", borderColor: "rgba(212,168,67,0.14)" }}>
            <CreditCard size={17} color="var(--gold-400)" />
          </div>
          <div className="stat-value" style={{ color: "var(--gold-400)" }}>{plan.replace("_", " ")}</div>
          <div className="stat-label">Поточний тариф</div>
          <Link href="/dashboard/billing" className="stat-action-link">Керування <ArrowRight size={11} /></Link>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(139,92,246,0.08)", borderColor: "rgba(139,92,246,0.14)" }}>
            <Scale size={17} color="#8b5cf6" />
          </div>
          <div className="stat-value" style={{ fontSize: "16px", paddingTop: "6px" }}>Судова практика</div>
          <div className="stat-label">Пошук рішень ВСУ</div>
          <Link href="/dashboard/case-law" className="stat-action-link">Відкрити <ArrowRight size={11} /></Link>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "rgba(16,185,129,0.08)", borderColor: "rgba(16,185,129,0.14)" }}>
            <FolderOpen size={17} color="#10b981" />
          </div>
          <div className="stat-value" style={{ fontSize: "16px", paddingTop: "6px" }}>Мої справи</div>
          <div className="stat-label">Управління справами</div>
          <Link href="/dashboard/cases" className="stat-action-link">Відкрити <ArrowRight size={11} /></Link>
        </div>
      </div>

      {/* Quick actions */}
      <div className="quick-strip">
        {QUICK_ACTIONS.map((a) => {
          const Icon = a.icon;
          return (
            <Link key={a.href} href={a.href} className="quick-strip-btn">
              <div className="quick-strip-icon" style={{ background: a.color + "14", border: "1px solid " + a.color + "25" }}>
                <Icon size={17} color={a.color} />
              </div>
              <span className="quick-strip-label">{a.label}</span>
            </Link>
          );
        })}
      </div>

      {/* Main split */}
      <div className="dash-split">

        {/* LEFT */}
        <div className="dash-left">

          {/* Recent docs */}
          <div className="dash-panel">
            <div className="dash-panel-header">
              <span className="dash-panel-title">
                <FileCheck size={13} style={{ color: "var(--gold-400)" }} />
                Останні документи
              </span>
              <Link href="/dashboard/documents" className="dash-panel-link">Всі →</Link>
            </div>
            <div className="dash-panel-body">
              {docsLoading ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", padding: "8px" }}>
                  {[1, 2, 3].map((i) => <div key={i} className="skeleton skeleton-row" />)}
                </div>
              ) : recentDocs.length === 0 ? (
                <div className="empty-inline">
                  <Sparkles size={26} opacity={0.2} />
                  <span>Документів ще немає</span>
                  <Link href="/dashboard/generate" className="btn btn-primary btn-sm">
                    Створити перший документ
                  </Link>
                </div>
              ) : (
                <div>
                  {recentDocs.map((doc) => (
                    <Link key={doc.id} href={"/dashboard/documents?id=" + doc.id} className="recent-doc-row">
                      <div className="recent-doc-icon"><FileText size={13} /></div>
                      <div className="recent-doc-name">
                        <strong>{docLabel(doc.document_type)}</strong>
                        {doc.preview_text && <span>{doc.preview_text.slice(0, 55)}…</span>}
                      </div>
                      <div className="recent-doc-time"><Clock size={10} />{timeAgo(doc.created_at)}</div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Cases */}
          <div className="dash-panel">
            <div className="dash-panel-header">
              <span className="dash-panel-title">
                <FolderOpen size={13} style={{ color: "var(--gold-400)" }} />
                Активні справи
              </span>
              <Link href="/dashboard/cases" className="dash-panel-link">Всі →</Link>
            </div>
            <div className="dash-panel-body">
              <div className="empty-inline">
                <FolderOpen size={26} opacity={0.2} />
                <span>Жодної справи не додано</span>
                <Link href="/dashboard/cases" className="btn btn-primary btn-sm">Додати першу справу</Link>
              </div>
            </div>
          </div>

          {/* Deadlines */}
          <div className="dash-panel">
            <div className="dash-panel-header">
              <span className="dash-panel-title">
                <CalendarDays size={13} style={{ color: "var(--gold-400)" }} />
                Найближчі строки
              </span>
              <Link href="/dashboard/deadlines" className="dash-panel-link">Всі →</Link>
            </div>
            <div className="dash-panel-body">
              <div className="empty-inline">
                <CalendarDays size={26} opacity={0.2} />
                <span>Контрольних строків немає</span>
                <Link href="/dashboard/deadlines" className="btn btn-secondary btn-sm">Створити строк</Link>
              </div>
            </div>
          </div>

        </div>

        {/* RIGHT */}
        <div className="dash-right">

          {/* AI Insight */}
          <div className="ai-insight-card">
            <div className="ai-insight-header"><Sparkles size={12} />AI Рекомендації</div>
            <div className="ai-insight-text">
              Додайте першу справу, щоб AI почав аналізувати строки, ризики та
              рекомендувати наступні дії. Система відстежить процесуальні
              дедлайни автоматично.
            </div>
            <Link href="/dashboard/full-lawyer" className="ai-insight-cta">
              Спробувати Повний юрист <ArrowRight size={11} />
            </Link>
          </div>

          {/* Tariff */}
          <div className="tariff-widget">
            <div className="tariff-plan-row">
              <span className="tariff-plan-name">{plan.replace("_", " ")}</span>
              <span className="tariff-status">● Активний</span>
            </div>
            {(
              [
                ["Генерація", plan === "FREE" ? "5/міс" : plan === "PRO" ? "50/міс" : "∞"],
                ["Судова практика", plan !== "FREE"],
                ["Моніторинг",      plan === "PRO_PLUS"],
                ["Е-Суд",          plan === "PRO_PLUS"],
              ] as [string, string | boolean][]
            ).map(([label, val]) => (
              <div className="tariff-row" key={label}>
                <span className="tariff-row-label">{label}</span>
                <span className={"tariff-row-value " + (val === true ? "tariff-row-yes" : val === false ? "tariff-row-no" : "")}>
                  {val === true ? "Так" : val === false ? "—" : val}
                </span>
              </div>
            ))}
            {usage && (
              <div style={{ marginTop: "10px", paddingTop: "10px", borderTop: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Документи</span>
                  <span style={{ fontSize: "11px", fontWeight: 600, color: usageDanger ? "var(--danger)" : "var(--text-secondary)" }}>
                    {usage.used} / {usageLimit}
                  </span>
                </div>
                <div className={"usage-bar-wrap" + (usageDanger ? " usage-bar-danger" : "")}>
                  <div className="usage-bar-fill" style={{ width: usagePct + "%" }} />
                </div>
              </div>
            )}
            {plan === "FREE" && (
              <Link href="/dashboard/billing" className="btn btn-primary btn-sm w-full" style={{ marginTop: "12px", justifyContent: "center" }}>
                Оновити до PRO
              </Link>
            )}
          </div>

          {/* Strategy CTA */}
          <div style={{ background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.15)", borderRadius: "var(--radius)", padding: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "8px" }}>
              <Zap size={13} color="#a78bfa" />
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#a78bfa", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                Стратегія справи
              </span>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "12px" }}>
              AI аналізує матеріали справи, будує правову стратегію і знаходить релевантну судову практику.
            </p>
            <Link href="/dashboard/strategy-studio" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", padding: "8px 14px", background: "rgba(139,92,246,0.12)", color: "#c4b5fd", border: "1px solid rgba(139,92,246,0.22)", borderRadius: "8px", fontSize: "12px", fontWeight: 600, width: "100%" }}>
              Відкрити Стратегію <ArrowRight size={12} />
            </Link>
          </div>

        </div>
      </div>
    </div>
  );
}
