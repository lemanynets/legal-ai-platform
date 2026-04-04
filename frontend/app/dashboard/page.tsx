"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getCurrentSubscription } from "@/lib/api";
import { getSession, getToken, getUserId, initAuth, type UserSession, updateSessionPlan } from "@/lib/auth";

const QUICK_ACTIONS = [
  { href: "/dashboard/analyze", label: "Аналіз", icon: "RISK" },
  { href: "/dashboard/generate", label: "Генерація", icon: "DOC" },
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

  const firstName = session?.name?.split(/\s+/)[0] ?? "юристе";
  const usagePercent = usage?.limit ? Math.min(100, (usage.used / usage.limit) * 100) : 0;
  const usageLimitLabel = usage?.limit == null ? "∞" : String(usage.limit);

  return (
    <div className="page-content">
      <div className="section-header">
        <div>
          <h1 className="section-title">Вітаю, {firstName}</h1>
          <p className="section-subtitle">Огляд тарифу, лімітів і швидких дій по платформі.</p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span className="badge badge-gold">{plan}</span>
          <Link href="/dashboard/billing" className="btn btn-primary">
            Керування тарифом
          </Link>
        </div>
      </div>

      <div className="grid-4" style={{ marginBottom: "28px" }}>
        <div className="card-elevated" style={{ padding: "20px" }}>
          <div className="section-subtitle">Документів за період</div>
          <div className="section-title" style={{ fontSize: "28px", marginTop: "8px" }}>
            {loading ? "—" : usage?.used ?? 0}
          </div>
          <div style={{ marginTop: "12px" }}>
            <div style={{ height: "6px", borderRadius: "999px", background: "var(--border-strong)", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${usagePercent}%`,
                  background: "var(--gold-500)",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
            <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--text-muted)" }}>
              {usage?.used ?? 0} / {usageLimitLabel}
            </div>
          </div>
        </div>

        <div className="card-elevated" style={{ padding: "20px" }}>
          <div className="section-subtitle">Поточний план</div>
          <div className="section-title" style={{ fontSize: "28px", marginTop: "8px" }}>{plan}</div>
        </div>

        <div className="card-elevated" style={{ padding: "20px" }}>
          <div className="section-subtitle">Судова практика</div>
          <div className="section-title" style={{ fontSize: "28px", marginTop: "8px" }}>ВС</div>
        </div>

        <div className="card-elevated" style={{ padding: "20px" }}>
          <div className="section-subtitle">Моніторинг</div>
          <div className="section-title" style={{ fontSize: "28px", marginTop: "8px" }}>
            {plan === "PRO_PLUS" ? "ON" : "—"}
          </div>
        </div>
      </div>

      <div style={{ marginBottom: "28px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "16px" }}>Швидкі дії</h2>
        <div className="grid-2">
          {QUICK_ACTIONS.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className="card-elevated"
              style={{ padding: "20px", display: "block" }}
            >
              <div style={{ fontSize: "12px", color: "var(--gold-400)", fontWeight: 800, marginBottom: "10px" }}>
                {action.icon}
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700 }}>{action.label}</div>
            </Link>
          ))}
        </div>
      </div>

      <div className="grid-2">
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px" }}>Документи</h2>
          <p className="section-subtitle">Швидкий перехід до архіву та генерації нових документів.</p>
          <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
            <Link href="/dashboard/documents" className="btn btn-secondary">Архів</Link>
            <Link href="/dashboard/generate" className="btn btn-primary">Створити</Link>
          </div>
        </div>

        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px" }}>Акаунт</h2>
          <p className="section-subtitle">Профіль, команда, білінг та звіти в одному місці.</p>
          <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
            <Link href="/dashboard/profile" className="btn btn-secondary">Профіль</Link>
            <Link href="/dashboard/team" className="btn btn-secondary">Команда</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
