"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { login, registerUser, devLogin, isDevAuthEnabled, setSessionFromAccessToken } from "@/lib/auth";
import { createKepChallenge, verifyKepAuth } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [kepLoading, setKepLoading] = useState(false);

  async function handleKepLogin() {
    setKepLoading(true);
    setError("");
    try {
      const challenge = await createKepChallenge({ provider: "local_key", purpose: "login" });
      const payloadJson = JSON.stringify(challenge.challenge_payload);
      const payloadBytes = new TextEncoder().encode(payloadJson);
      const signedPayload = btoa(String.fromCharCode(...payloadBytes));
      // NOTE: real integration should call a KEP SDK/provider here.
      const placeholderSignature = btoa(`${challenge.nonce}:signed`);
      const placeholderCertificate = btoa("demo-kep-certificate");
      const auth = await verifyKepAuth({
        challenge_id: challenge.challenge_id,
        signature: placeholderSignature,
        signed_payload: signedPayload,
        certificate: placeholderCertificate,
        provider: "local_key",
      });
      setSessionFromAccessToken({
        access_token: auth.access_token,
        email: auth.user?.email,
        name: auth.user?.name,
      });
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка КЕП авторизації");
    } finally {
      setKepLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isLogin) {
        // Use devLogin when Supabase is not configured (local dev mode)
        if (isDevAuthEnabled) {
          await devLogin(email, password);
        } else {
          await login(email, password);
        }
      } else {
        if (isDevAuthEnabled) {
          await devLogin(email || "dev@legal-ai.local", password || "dev");
        } else {
          await registerUser(email, password, fullName);
        }
      }
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка");
    } finally {
      setLoading(false);
    }
  }

  const heading = isLogin ? "Юридична AI-Платформа" : "Створення облікового запису";
  const subtitle = isLogin ? "Раді бачити вас знову" : "Створіть акаунт і почніть роботу в чистому просторі авторизації";

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(30,58,110,0.4) 0%, var(--navy-950) 70%)",
      padding: "24px",
    }}>
      {/* Background decoration */}
      <div style={{
        position: "fixed", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0,
      }}>
        <div style={{
          position: "absolute", top: "-20%", left: "50%", transform: "translateX(-50%)",
          width: "800px", height: "600px",
          background: "radial-gradient(ellipse, rgba(212,168,67,0.06) 0%, transparent 70%)",
        }} />
      </div>

      <div style={{ width: "100%", maxWidth: "440px", position: "relative", zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <div style={{
            width: "56px", height: "56px", margin: "0 auto 16px",
            background: "linear-gradient(135deg, var(--gold-500), var(--gold-300))",
            borderRadius: "16px",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "28px",
            boxShadow: "0 8px 24px rgba(212,168,67,0.35)",
          }}>⚖</div>
          <h1 style={{ fontSize: "26px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "6px" }}>
            {heading}
          </h1>
          <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
            {subtitle}
          </p>
          <a
            href="/"
            style={{
              display: "inline-block",
              marginTop: "14px",
              fontSize: "13px",
              color: "var(--gold-400)",
              fontWeight: 600,
            }}
          >
            На головну
          </a>
        </div>

        {/* Card */}
        <div className="card-elevated" style={{ padding: "36px" }}>
          <div style={{ display: "flex", gap: "10px", marginBottom: "24px" }}>
            <button
              className={`btn ${isLogin ? "btn-primary" : "btn-secondary"}`}
              style={{ flex: 1, justifyContent: "center" }}
              onClick={() => { setIsLogin(true); setError(""); }}
            >
              Вхід
            </button>
            <button
              className={`btn ${!isLogin ? "btn-primary" : "btn-secondary"}`}
              style={{ flex: 1, justifyContent: "center" }}
              onClick={() => { setIsLogin(false); setError(""); }}
            >
              Реєстрація
            </button>
          </div>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {!isLogin && (
              <div className="form-group">
                <label className="form-label" htmlFor="fullName">Повне ім'я</label>
                <input
                  id="fullName"
                  type="text"
                  className="form-input"
                  placeholder="Ваше повне ім'я"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  autoComplete="name"
                />
              </div>
            )}
            <div className="form-group">
              <label className="form-label" htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                className="form-input"
                placeholder="ваш@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">Пароль</label>
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={isLogin ? "current-password" : "new-password"}
              />
            </div>

            {error && (
              <div className="alert alert-error">
                <span>⚠</span> {error}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary w-full"
              style={{ marginTop: "4px", height: "48px", fontSize: "15px" }}
              disabled={loading}
            >
              {loading ? (
                <><span className="spinner" style={{ width: 16, height: 16 }} /> {isLogin ? "Вхід..." : "Реєстрація..."}</>
              ) : (isLogin ? "Увійти" : "Створити обліковий запис")}
            </button>
            {isLogin && (
              <button
                type="button"
                className="btn btn-secondary w-full"
                style={{ height: "48px", fontSize: "15px" }}
                disabled={kepLoading || loading}
                onClick={() => void handleKepLogin()}
              >
                {kepLoading ? "Підписую КЕП..." : "Увійти через КЕП"}
              </button>
            )}
          </form>

          <hr className="divider" style={{ margin: "24px 0 20px" }} />

          {isDevAuthEnabled && (
            <div style={{
              background: "rgba(212,168,67,0.08)",
              border: "1px solid rgba(212,168,67,0.25)",
              borderRadius: "8px",
              padding: "12px 14px",
              marginBottom: "16px",
              fontSize: "12px",
              color: "var(--text-muted)",
              lineHeight: 1.6,
            }}>
              <strong style={{ color: "var(--gold-400)" }}>Dev режим</strong> — Supabase не налаштований.<br />
              Введіть будь-який email і пароль (мін. 6 символів).
            </div>
          )}

          <p style={{ fontSize: "13px", color: "var(--text-muted)", textAlign: "center", lineHeight: 1.6 }}>
            Необхідна допомога?{" "}
            <a href="mailto:support@legalai.ua" style={{ color: "var(--gold-400)", fontWeight: 600 }}>
              Зв'яжіться з нами
            </a>
          </p>
        </div>

        <p style={{ textAlign: "center", marginTop: "24px", fontSize: "12px", color: "var(--text-muted)" }}>
          © 2026 Юридична AI-Платформа. Всі права захищені.
        </p>
      </div>
    </div>
  );
}
