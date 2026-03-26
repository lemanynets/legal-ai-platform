"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getCurrentSubscription } from "@/lib/api";
import { getSession, getToken, getUserId, initAuth, type UserSession, updateSessionPlan } from "@/lib/auth";

const QUICK_ACTIONS = [
  { href: "/dashboard/generate", label: "Генерація документа", icon: "DOC" },
  { href: "/dashboard/full-lawyer", label: "Повний юрист", icon: "AI" },
  { href: "/dashboard/analyze", label: "Аналіз контракту", icon: "RISK" },
  { href: "/dashboard/calculators", label: "Калькулятори", icon: "CALC" },
];

export default function DashboardPage() {
  const [session, setSession] = useState<UserSession | null>(null);
  const [plan, setPlan] = useState("FREE");
  const [usage, setUsage] = useState<{ used: number; limit: number | null } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function bootstrap(): Promise<void> {
      await initAuth();
      const currentSession = getSession();
      if (!active) return;

      setSession(currentSession);
      setPlan(currentSession?.plan ?? "FREE");

      if (!currentSession) {
        setLoading(false);
        return;
      }

      const subscription = await getCurrentSubscription(getToken(), getUserId()).catch(() => null);
      if (!active) return;

      if (subscription) {
        const nextPlan = subscription.plan ?? currentSession.plan ?? "FREE";
        setPlan(nextPlan);
        updateSessionPlan(nextPlan);
        setUsage({
          used: subscription.usage?.docs_used ?? 0,
          limit: subscription.usage?.docs_limit ?? null,
        });
      }

      setLoading(false);
    }

    void bootstrap();
    return () => {
      active = false;
    };
  }, []);

  const greeting = (): string => {
    const hour = new Date().getHours();
    if (hour < 12) return "Доброго ранку";
    if (hour < 18) return "Доброго дня";
    return "Доброго вечора";
  };

  const firstName = session?.name?.split(/\s+/)[0] ?? "юристе";
  const usageLimitLabel = usage?.limit == null ? "∞" : String(usage.limit);
  const usagePercent = usage?.limit ? Math.min(100, (usage.used / usage.limit) * 100) : 0;

  return (
    <div>
      <div className="section-header">
        <div>
          <h1 className="section-title">
            {greeting()}, {firstName}
          </h1>
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

      <div className="grid-4" style={{ marginBottom: "28px" }}>
        <div className="stat-card">
          <div className="stat-icon">DOC</div>
          <div className="stat-value">{loading ? "—" : usage?.used ?? 0}</div>
          <div className="stat-label">Документів цього періоду</div>
          {usage && (
            <div style={{ marginTop: "8px" }}>
              <div style={{ height: "4px", background: "var(--border-strong)", borderRadius: "2px", overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: `${usagePercent}%`,
                    borderRadius: "2px",
                    background: usage.limit !== null && usage.used >= usage.limit ? "var(--danger)" : "var(--gold-500)",
                    transition: "width 0.4s ease",
                  }}
                />
              </div>
              <div className="text-xs text-muted" style={{ marginTop: "4px" }}>
                {usage.used} / {usageLimitLabel} ліміт
              </div>
            </div>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-icon">PLAN</div>
          <div className="stat-value">{plan}</div>
          <div className="stat-label">Поточний тариф</div>
          <Link href="/dashboard/billing" className="text-xs text-gold" style={{ marginTop: "6px" }}>
            Керування підпискою
          </Link>
        </div>

        <div className="stat-card">
          <div className="stat-icon">LAW</div>
          <div className="stat-value">ВС</div>
          <div className="stat-label">Судова практика</div>
          <div className="text-xs text-muted" style={{ marginTop: "6px" }}>
            Верховний Суд і пов’язані позиції
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">MON</div>
          <div className="stat-value">{plan === "PRO_PLUS" ? "ON" : "—"}</div>
          <div className="stat-label">Реєстровий моніторинг</div>
          <Link href="/dashboard/monitoring" className="text-xs text-gold" style={{ marginTop: "6px" }}>
            Відкрити моніторинг
          </Link>
        </div>
      </div>

      <div style={{ marginBottom: "28px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "14px", color: "var(--text-primary)" }}>
          Швидкі дії
        </h2>
        <div className="grid-4">
          {QUICK_ACTIONS.map((action) => (
            <Link key={action.href} href={action.href} className="card-elevated card-hover" style={{ padding: "20px", textDecoration: "none" }}>
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "12px",
                  fontSize: "12px",
                  fontWeight: 800,
                  color: "var(--gold-400)",
                  background: "rgba(212,168,67,0.1)",
                  border: "1px solid rgba(212,168,67,0.18)",
                }}
              >
                {action.icon}
              </div>
              <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>{action.label}</div>
            </Link>
          ))}
        </div>
      </div>

      <div className="grid-2">
        <div className="card-elevated" style={{ padding: "24px" }}>
          <div className="flex justify-between items-center mb-4">
            <h2 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>Останні документи</h2>
            <Link href="/dashboard/documents" className="text-sm text-gold">
              Усі
            </Link>
          </div>
          <div style={{ color: "var(--text-muted)", fontSize: "13px", paddingTop: "8px", textAlign: "center" }}>
            Історія документів доступна у відповідному розділі.
            <br />
            <Link href="/dashboard/generate" style={{ color: "var(--gold-400)", fontWeight: 600 }}>
              Перейти до генерації
            </Link>
          </div>
        </div>

        <div className="card-elevated" style={{ padding: "24px" }}>
          <div className="flex justify-between items-center mb-4">
            <h2 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>Ваш план</h2>
            <Link href="/dashboard/billing" className="text-sm text-gold">
              Змінити
            </Link>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {[
              { label: "Тариф", value: plan },
              { label: "Статус", value: "Активний" },
              { label: "Генерація документів", value: plan === "FREE" ? "5/міс" : plan === "PRO" ? "50/міс" : "∞" },
              { label: "Судова практика", value: plan !== "FREE" ? "Так" : "PRO+" },
              { label: "Реєстровий моніторинг", value: plan === "PRO_PLUS" ? "Так" : "PRO+" },
            ].map(({ label, value }) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>{label}</span>
                <span style={{ fontSize: "13px", fontWeight: 600, color: value === "Так" ? "var(--success)" : "var(--text-secondary)" }}>
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
    </div>
  );
}
