"use client";

import { useState, useEffect } from "react";
import { getToken, getUserId } from "@/lib/auth";
import { getUserInfo, updateUserInfo } from "@/lib/api";

export default function SettingsPage() {
  const [logoUrl, setLogoUrl] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(true);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const data = await getUserInfo(getToken(), getUserId());
      setLogoUrl(data.logo_url || "");
      setCompanyName(data.company || "");
      setFullName(data.full_name || "");
    } catch (err) {
      console.error(err);
      setError("Не вдалося завантажити профіль.");
    } finally {
      setLoading(false);
    }
  }

  async function onSave() {
    setSaving(true);
    setInfo("");
    setError("");
    try {
      await updateUserInfo({
        logo_url: logoUrl,
        company: companyName,
        full_name: fullName
      }, getToken(), getUserId());
      setInfo("Налаштування брендингу успішно оновлено.");
    } catch (err) {
      setError("Помилка при збереженні профілю.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: "100px" }}>
       <div className="spinner" />
    </div>
  );

  return (
    <div className="page-content animate-fade-in branding-v2">
      <div className="section-header-row mb-12">
        <div>
          <span className="badge badge-gold mb-4">Ексклюзивна послуга (PRO+)</span>
          <h1 className="hero-title white">Брендування простору</h1>
          <p className="hero-subtitle">Налаштуйте White-labeling, щоб ваші документи виглядали професійно та відповідали корпоративному стилю.</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card-elevated glass-card branding-form-card">
          <h2 className="section-small-title mb-8">Реквізити бренду</h2>
          
          <div className="flex flex-col gap-6">
            <div className="input-group">
              <label>Логотип (URL посилання)</label>
              <input 
                type="text" 
                placeholder="https://cloud.com/logo.png" 
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
              />
              <div className="input-hint">Рекомендується прозорий PNG або білий логотип на темному фоні.</div>
            </div>

            <div className="input-group">
              <label>Повна назва Юрфірми / АБ</label>
              <input 
                type="text" 
                placeholder="ТОВ 'Юридична Компанія Гранд'" 
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>Ваше ім'я (для підписів)</label>
              <input 
                type="text" 
                placeholder="Адвокат Іванов І.І." 
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
          </div>

          <div style={{ marginTop: '40px' }}>
            {info && <div className="alert-success-minimal mb-4">{info}</div>}
            {error && <div className="alert-error-minimal mb-4">{error}</div>}
            <button className="btn btn-gold w-full btn-lg" onClick={onSave} disabled={saving}>
              {saving ? "Збереження..." : "Застосувати зміни"}
            </button>
          </div>
        </div>

        <div className="card-elevated doc-preview-card">
           <h2 className="card-mini-label white mb-6">Попередній перегляд (Preview)</h2>
           <div className="docx-preview-mockup">
              <div className="docx-header">
                <div className="docx-logo-wrap">
                  {logoUrl ? (
                    <img src={logoUrl} alt="Logo" className="docx-logo-img" />
                  ) : (
                    <div className="docx-logo-placeholder">Ваш логотип тут</div>
                  )}
                </div>
              </div>
              <div className="docx-body-mock">
                 <div className="docx-line long" />
                 <div className="docx-line center mb-8" />
                 <div className="docx-line" />
                 <div className="docx-line" />
                 <div className="docx-line short" />
                 <div className="docx-line mt-12" />
                 <div className="docx-line" />
              </div>
              <div className="docx-footer-mock text-xs text-muted" style={{ textAlign: 'right', marginTop: '40px' }}>
                 Документ згенеровано: {new Date().toLocaleDateString()}
              </div>
           </div>
           <p className="text-xs text-muted mt-6 text-center">
             * Цей попередній перегляд показує приблизне розташування логотипа в DOCX/PDF файлах.
           </p>
        </div>
      </div>

      <style jsx>{`
        .branding-v2 { max-width: 1200px; margin: 0 auto; color: #fff; }
        .branding-form-card { padding: 40px; border-radius: 32px; }
        .input-group label { display: block; font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1.5px; }
        .input-group input { width: 100%; padding: 14px 20px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; color: #fff; outline: none; transition: all 0.2s; font-size: 15px; }
        .input-group input:focus { border-color: var(--gold-500); background: rgba(255,255,255,0.06); box-shadow: 0 0 15px rgba(212,168,67,0.1); }
        .input-hint { font-size: 11px; color: #475569; margin-top: 8px; font-weight: 600; }
        
        .doc-preview-card { padding: 40px; background: rgba(15,23,42,0.6); border-radius: 32px; border: 1px dashed rgba(255,255,255,0.1); }
        .docx-preview-mockup { background: #fff; border-radius: 4px; padding: 40px; color: #334155; box-shadow: 0 10px 40px rgba(0,0,0,0.4); min-height: 400px; }
        .docx-header { border-bottom: 1px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: flex-end; }
        .docx-logo-wrap { height: 50px; display: flex; align-items: center; justify-content: center; }
        .docx-logo-img { max-height: 50px; max-width: 150px; }
        .docx-logo-placeholder { border: 2px dashed #cbd5e1; color: #94a3b8; padding: 10px 20px; font-size: 12px; font-weight: 700; border-radius: 6px; }
        
        .docx-line { height: 8px; background: #f1f5f9; margin-bottom: 12px; border-radius: 4px; }
        .docx-line.long { width: 100%; }
        .docx-line.short { width: 60%; }
        .docx-line.center { width: 40%; margin-left: auto; margin-right: auto; height: 12px; background: #e2e8f0; }
        
        .alert-success-minimal { padding: 12px; background: rgba(16,185,129,0.1); border-left: 3px solid #10b981; color: #10b981; font-size: 13px; font-weight: 700; border-radius: 0 8px 8px 0; }
        .alert-error-minimal { padding: 12px; background: rgba(239,68,68,0.1); border-left: 3px solid #ef4444; color: #ef4444; font-size: 13px; font-weight: 700; border-radius: 0 8px 8px 0; }
      `}</style>
    </div>
  );
}
