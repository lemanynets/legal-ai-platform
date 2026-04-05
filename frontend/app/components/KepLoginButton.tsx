"use client";

/**
 * KepLoginButton — авторизація через електронний цифровий ключ (КЕП/ЕЦП)
 *
 * Використовує бібліотеку ІІТ EndUser JS (EU.js) для читання КЕП-контейнерів
 * та формування PKCS#7 підпису.
 *
 * Підтримувані формати: .jks .pfx .p12 .dat (IIT-контейнер)
 * Підтримувані провайдери: ПриватБанк, МВС АЦСК, Дія, Укртелеком АЦСК, КНЕДП
 *
 * Флоу:
 *   1. Отримати nonce від /api/auth/kep/challenge
 *   2. Зчитати КЕП через IIT EndUser JS
 *   3. Підписати nonce → PKCS#7 підпис
 *   4. Надіслати certificate_pem + signed_data_b64 на /api/auth/kep/verify
 *   5. Отримати JWT і зберегти сесію
 */

import { useRef, useState } from "react";
import { persistSessionFromToken } from "@/lib/auth";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

// Типи для IIT EndUser JS (глобальна змінна після завантаження скрипта)
declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    EndUser: any;
  }
}

interface KepLoginButtonProps {
  onSuccess: () => void;
  onError: (msg: string) => void;
}

export default function KepLoginButton({ onSuccess, onError }: KepLoginButtonProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"idle" | "reading" | "signing" | "verifying">("idle");
  const [password, setPassword] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");

  const stepLabels: Record<string, string> = {
    idle: "",
    reading: "Читаємо КЕП...",
    signing: "Підписуємо...",
    verifying: "Верифікуємо...",
  };

  /** Динамічно завантажуємо IIT EU.js зі CDN */
  async function loadIitLibrary(): Promise<void> {
    if (typeof window !== "undefined" && typeof window.EndUser !== "undefined") return;
    await new Promise<void>((resolve, reject) => {
      const existing = document.getElementById("iit-eu-script");
      if (existing) { resolve(); return; }
      const script = document.createElement("script");
      script.id = "iit-eu-script";
      // Офіційна CDN-адреса IIT EndUser JS (v2)
      script.src = "https://iit.com.ua/download/productfiles/EU.js";
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Не вдалося завантажити IIT бібліотеку"));
      document.head.appendChild(script);
    });
  }

  async function handleKepLogin() {
    const file = fileRef.current?.files?.[0];
    if (!file) { onError("Оберіть файл КЕП-ключа"); return; }
    if (!password) { onError("Введіть пароль від КЕП"); return; }

    setLoading(true);
    try {
      // ── 1. Завантажуємо IIT бібліотеку ────────────────────────────────────
      setStep("reading");
      await loadIitLibrary();

      // ── 2. Зчитуємо КЕП файл ──────────────────────────────────────────────
      const fileBytes = await file.arrayBuffer();
      const keyData = new Uint8Array(fileBytes);

      const euSign = new window.EndUser(null, window.EndUser?.FormType?.None ?? 0);
      await euSign.IsInitialized();

      // Зчитуємо приватний ключ
      await euSign.ReadPrivateKey(keyData, password, null);

      // Витягуємо інформацію про власника
      const ownerInfo = await euSign.GetOwnCertificate();

      // Конвертуємо сертифікат у PEM
      const certBytes: Uint8Array = await euSign.GetOwnCertificateAsBytes();
      const certBase64 = btoa(String.fromCharCode(...certBytes));
      const certPem = `-----BEGIN CERTIFICATE-----\n${certBase64.match(/.{1,64}/g)?.join("\n")}\n-----END CERTIFICATE-----`;

      // ── 3. Отримуємо nonce від сервера ────────────────────────────────────
      const challengeRes = await fetch(`${BACKEND_URL}/api/auth/kep/challenge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!challengeRes.ok) throw new Error("Не вдалося отримати nonce від сервера");
      const challenge = await challengeRes.json();

      // ── 4. Підписуємо nonce КЕП-ключем ───────────────────────────────────
      setStep("signing");
      const nonceBytes = Uint8Array.from(atob(challenge.nonce), (c) => c.charCodeAt(0));
      // SignData повертає base64 PKCS#7 підпис
      const signedB64: string = await euSign.SignData(nonceBytes, true);

      // ── 5. Відправляємо на сервер для верифікації ─────────────────────────
      setStep("verifying");
      const verifyRes = await fetch(`${BACKEND_URL}/api/auth/kep/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nonce_id: challenge.nonce_id,
          certificate_pem: certPem,
          signed_data_b64: signedB64,
          owner_info: ownerInfo ?? {},
        }),
      });

      if (!verifyRes.ok) {
        const err = await verifyRes.json().catch(() => ({}));
        throw new Error(err.detail || "Верифікація КЕП не вдалася");
      }

      const data = await verifyRes.json();
      // Зберігаємо сесію
      await persistSessionFromToken(data.access_token, data.user);
      onSuccess();

    } catch (err) {
      onError(err instanceof Error ? err.message : "Помилка авторизації через КЕП");
    } finally {
      setLoading(false);
      setStep("idle");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <button
        type="button"
        className="btn btn-secondary"
        style={{
          width: "100%",
          height: "44px",
          justifyContent: "center",
          gap: "8px",
          border: "1px solid rgba(212,168,67,0.3)",
          color: "var(--gold-400)",
          fontSize: "14px",
        }}
        onClick={() => setExpanded((p) => !p)}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
        Увійти з КЕП / ЕЦП
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2"
          style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "0.2s" }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {expanded && (
        <div style={{
          background: "rgba(212,168,67,0.04)",
          border: "1px solid rgba(212,168,67,0.15)",
          borderRadius: "10px",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: 0, lineHeight: 1.5 }}>
            Підтримується: <strong style={{ color: "var(--text-secondary)" }}>.jks .pfx .p12 .dat</strong>
            <br />Провайдери: ПриватБанк, Дія, МВС АЦСК, Укртелеком АЦСК, КНЕДП
          </p>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: "12px" }}>Файл ключа</label>
            <div
              style={{
                border: "1px dashed rgba(212,168,67,0.3)",
                borderRadius: "8px",
                padding: "10px 14px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "13px",
                color: fileName ? "var(--text-primary)" : "var(--text-muted)",
                background: "rgba(255,255,255,0.02)",
              }}
              onClick={() => fileRef.current?.click()}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              {fileName || "Оберіть файл .jks / .pfx / .p12 / .dat"}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".jks,.pfx,.p12,.dat,.pk8,.zs2"
              style={{ display: "none" }}
              onChange={(e) => setFileName(e.target.files?.[0]?.name || "")}
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: "12px" }}>Пароль від КЕП</label>
            <input
              type="password"
              className="form-input"
              placeholder="Пароль захисту ключа"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="off"
              style={{ fontSize: "14px" }}
            />
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center", height: "42px" }}
            onClick={handleKepLogin}
            disabled={loading || !fileName || !password}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 14, height: 14 }} />
                {stepLabels[step] || "Обробка..."}
              </>
            ) : (
              "Підписати та увійти"
            )}
          </button>

          <p style={{ fontSize: "11px", color: "var(--text-muted)", margin: 0, textAlign: "center" }}>
            Ключ обробляється локально у браузері.
            Приватний ключ не передається на сервер.
          </p>
        </div>
      )}
    </div>
  );
}
