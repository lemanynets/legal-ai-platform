"use client";

import { useState } from "react";
import { updateUserInfo } from "@/lib/api";
import { getToken, getUserId } from "@/lib/auth";

interface LogoUploadProps {
  initialLogoUrl?: string | null;
  onSuccess?: (newUrl: string) => void;
}

export default function LogoUpload({ initialLogoUrl, onSuccess }: LogoUploadProps) {
  const [logoUrl, setLogoUrl] = useState(initialLogoUrl || "");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function handleSave() {
    if (!logoUrl.trim()) return;
    setLoading(true);
    setMessage("");
    try {
      await updateUserInfo({ logo_url: logoUrl.trim() }, getToken(), getUserId());
      setMessage("✅ Логотип успішно збережено");
      if (onSuccess) onSuccess(logoUrl.trim());
    } catch (err) {
      setMessage("❌ Помилка при збереженні логотипу");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="branding-box card-elevated" style={{ padding: 24, background: "rgba(255,255,255,0.02)", marginTop: 24 }}>
      <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, color: "#fff" }}>Брендування документів</h3>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20 }}>
        Вкажіть URL вашого логотипу (PNG або JPG). Він буде доданий у колонтитули експортованих документів DOCX та PDF.
      </p>
      
      <div style={{ display: "flex", gap: 12 }}>
        <input 
          className="form-input" 
          placeholder="https://example.com/logo.png" 
          value={logoUrl}
          onChange={(e) => setLogoUrl(e.target.value)}
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" onClick={handleSave} disabled={loading}>
          {loading ? "Збереження..." : "Зберегти"}
        </button>
      </div>
      
      {message && <p style={{ fontSize: 12, marginTop: 12, color: message.startsWith('✅') ? 'var(--success)' : 'var(--danger)' }}>{message}</p>}
      
      {logoUrl && (
        <div style={{ marginTop: 20 }}>
          <label style={{ fontSize: 11, textTransform: "uppercase", color: "var(--text-muted)", display: "block", marginBottom: 8 }}>Попередній перегляд:</label>
          <div style={{ background: "#fff", padding: 12, borderRadius: 8, display: "inline-block" }}>
            <img src={logoUrl} alt="Logo preview" style={{ maxHeight: 40, maxWidth: 200, objectFit: "contain" }} onError={(e) => (e.currentTarget.style.display = 'none')} />
          </div>
        </div>
      )}
    </div>
  );
}
