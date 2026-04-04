"use client";

import { useState, useEffect } from "react";
import { getToken, getUserId } from "@/lib/auth";
import { getUserInfo, updateUserInfo, getCompanyByCode } from "@/lib/api";

export default function ProfilePage() {
  const [entityType, setEntityType] = useState<"individual" | "legal_entity">("individual");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  
  const [loading, setLoading] = useState(true);
  const [loadingCompany, setLoadingCompany] = useState(false);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    try {
      const data = await getUserInfo(getToken(), getUserId());
      setEntityType((data.entity_type as "individual" | "legal_entity") || "individual");
      setFullName(data.full_name || "");
      setCompanyName(data.company || "");
      setTaxId(data.tax_id || "");
      setAddress(data.address || "");
      setPhone(data.phone || "");
    } catch (err) {
      console.error(err);
      setError("Не вдалося завантажити профіль.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAutoFill() {
    if (!taxId || taxId.length < 8) {
      setError("Введіть коректний код ЄДРПОУ для пошуку.");
      return;
    }
    setLoadingCompany(true);
    setError("");
    setInfo("");
    try {
      const company: any = await getCompanyByCode(taxId, getToken(), getUserId());
      setCompanyName(company.full_name || company.short_name || "");
      setAddress(company.address || "");
      if (company.ceo) {
        setFullName(company.ceo);
      }
      setInfo("Реєстраційні дані компанії завантажено. Не забудьте натиснути 'Зберегти профіль'.");
    } catch (err) {
      setError("Помилка завантаження даних з ЄДР. Перевірте код.");
    } finally {
      setLoadingCompany(false);
    }
  }

  async function onSave() {
    setSaving(true);
    setInfo("");
    setError("");
    try {
      await updateUserInfo({
        entity_type: entityType,
        full_name: fullName,
        company: companyName,
        tax_id: taxId,
        address: address,
        phone: phone
      }, getToken(), getUserId());
      setInfo("Профіль успішно оновлено.");
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
          <h1 className="hero-title white">Особистий кабінет</h1>
          <p className="hero-subtitle">Вкажіть дані для автоматичного формування договорів та реквізитів у документах.</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card-elevated glass-card branding-form-card">
          <h2 className="section-small-title mb-8">Реквізити суб'єкта</h2>
          
          <div className="flex flex-col gap-6">
            <div className="input-group">
              <label>Тип особи</label>
              <div style={{ display: "flex", gap: "10px" }}>
                <button 
                  className={`btn ${entityType === "individual" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setEntityType("individual")}
                >Фізична особа / ФОП</button>
                <button 
                  className={`btn ${entityType === "legal_entity" ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setEntityType("legal_entity")}
                >Юридична особа</button>
              </div>
            </div>

            <div className="input-group">
              <label>{entityType === "legal_entity" ? "ЄДРПОУ" : "РНОКПП (ІПН)"}</label>
              <div style={{ display: "flex", gap: "10px" }}>
                <input 
                  type="text" 
                  style={{ flex: 1 }}
                  placeholder={entityType === "legal_entity" ? "12345678" : "1234567890"}
                  value={taxId} 
                  onChange={e => setTaxId(e.target.value)} 
                />
                {entityType === "legal_entity" && (
                  <button 
                    className="btn btn-secondary" 
                    onClick={handleAutoFill}
                    disabled={loadingCompany}
                    style={{ whiteSpace: "nowrap" }}
                  >
                    {loadingCompany ? "Пошук..." : "Заповнити з ЄДР"}
                  </button>
                )}
              </div>
            </div>

            {entityType === "legal_entity" && (
              <div className="input-group">
                <label>Повна назва Юридичної особи</label>
                <input 
                  type="text" 
                  placeholder="ТОВ 'Компанія'"
                  value={companyName} 
                  onChange={e => setCompanyName(e.target.value)} 
                />
              </div>
            )}

            <div className="input-group">
              <label>{entityType === "legal_entity" ? "ПІБ директора (керівника)" : "ПІБ (Повне ім'я фізичної особи)"}</label>
              <input 
                type="text" 
                placeholder={entityType === "legal_entity" ? "Керівник Іван Іванович" : "Іванов Іван Іванович"}
                value={fullName} 
                onChange={e => setFullName(e.target.value)} 
              />
            </div>

            <div className="input-group">
              <label>Юридична адреса / Адреса реєстрації</label>
              <input 
                type="text" 
                placeholder="м. Київ, вул. Хрещатик, 1"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>Контактний телефон</label>
              <input 
                type="text" 
                placeholder="+380 50 123 4567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
          </div>

          <div style={{ marginTop: '40px' }}>
            {info && <div className="alert-success-minimal mb-4">{info}</div>}
            {error && <div className="alert-error-minimal mb-4">{error}</div>}
            <button className="btn btn-gold w-full btn-lg" onClick={onSave} disabled={saving}>
              {saving ? "Збереження..." : "Зберегти профіль"}
            </button>
          </div>
        </div>

        <div className="card-elevated doc-preview-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
           <h2 className="card-mini-label white mb-2">Як це використовується?</h2>
           <p className="text-secondary text-sm">Вказані вами дані автоматично підтягуються під час складання позовних заяв, договорів, або адвокатських запитів системою Legal AI.</p>
           
           <div className="docx-preview-mockup" style={{ minHeight: 'auto', padding: '20px' }}>
              <div className="text-xs text-muted mb-2">Приклад "Шапка позову":</div>
              <div style={{ padding: '15px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                 <strong style={{ color: '#fff' }}>Позивач:</strong><br/>
                 <span className="text-sm text-secondary">
                   {entityType === "legal_entity" ? (companyName || "ТОВ 'Назва'") : (fullName || "ПІБ")}
                   <br/>
                   ЄДРПОУ/ІПН: {taxId || "XXXXXX"}
                   <br/>
                   Адреса: {address || "Вкажіть адресу"}
                   <br/>
                   Тел.: {phone || "Вкажіть телефон"}
                 </span>
              </div>
           </div>
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
        
        .alert-success-minimal { padding: 12px; background: rgba(16,185,129,0.1); border-left: 3px solid #10b981; color: #10b981; font-size: 13px; font-weight: 700; border-radius: 0 8px 8px 0; }
        .alert-error-minimal { padding: 12px; background: rgba(239,68,68,0.1); border-left: 3px solid #ef4444; color: #ef4444; font-size: 13px; font-weight: 700; border-radius: 0 8px 8px 0; }
      `}</style>
    </div>
  );
}
