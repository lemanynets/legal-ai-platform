"use client";

import { FormEvent, useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import { getTeamUsers, type TeamUsersResponse, updateTeamUserRole } from "@/lib/api";

const ROLES = [
  { value: "owner", label: "Власник" },
  { value: "admin", label: "Адміністратор" },
  { value: "lawyer", label: "Юрист" },
  { value: "analyst", label: "Аналітик" },
  { value: "viewer", label: "Гість" },
];

export default function TeamPage() {
  const [targetUserId, setTargetUserId] = useState("");
  const [targetRole, setTargetRole] = useState("lawyer");
  const [targetEmail, setTargetEmail] = useState("");
  const [targetFullName, setTargetFullName] = useState("");
  const [targetCompany, setTargetCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [team, setTeam] = useState<TeamUsersResponse | null>(null);

  useEffect(() => { void loadTeam(); }, []);

  async function loadTeam(): Promise<void> {
    setLoading(true); setError(""); setInfo("");
    try {
      const result = await getTeamUsers(getToken(), getUserId());
      setTeam(result);
    } catch (err) {
      setError(String(err));
      setTeam(null);
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!targetUserId.trim()) {
      setError("ID користувача обов'язковий.");
      return;
    }
    setSaving(true); setError(""); setInfo("");
    try {
      const result = await updateTeamUserRole(
        {
          target_user_id: targetUserId.trim(),
          role: targetRole,
          email: targetEmail.trim() || undefined,
          full_name: targetFullName.trim() || undefined,
          company: targetCompany.trim() || undefined
        },
        getToken(),
        getUserId()
      );
      setInfo(`Роль користувача ${result.item.user_id} змінена на ${result.item.role}.`);
      setTargetUserId(""); setTargetEmail(""); setTargetFullName(""); setTargetCompany("");
      await loadTeam();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  const roleLabel = (r: string) => ROLES.find(opt => opt.value === r)?.label || r;
  const roleBadge = (r: string) => {
    if (r === "owner") return "badge-gold";
    if (r === "admin") return "badge-blue";
    if (r === "lawyer") return "badge-success";
    return "badge-muted";
  };

  return (
    <div>
      <div className="section-header">
        <div>
          <h1 className="section-title">Команда та доступ</h1>
          <p className="section-subtitle">Керування учасниками воркспейсу та їх ролями</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={loadTeam} disabled={loading}>
          {loading ? "Оновлення..." : "↻ Оновити список"}
        </button>
      </div>

      {info && <div className="card-elevated" style={{ padding: "12px 16px", marginBottom: "16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}>✓ {info}</div>}
      {error && <div className="preflight-block" style={{ marginBottom: 16 }}><span style={{ color: "var(--danger)" }}>⚠ {error}</span></div>}

      <div className="grid-2" style={{ gap: 20 }}>
        {/* Update Role Form */}
        <div className="card-elevated" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: "var(--text-primary)" }}>👤 Редагувати роль</h2>
          <form onSubmit={onSubmit}>
            <div style={{ marginBottom: 12 }}>
              <label className="form-label">ID користувача <span style={{ color: "var(--danger)" }}>*</span></label>
              <input className="form-input" value={targetUserId} onChange={(e) => setTargetUserId(e.target.value)} required placeholder="user-uuid-..." />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label className="form-label">Роль</label>
              <select className="form-input" value={targetRole} onChange={(e) => setTargetRole(e.target.value)}>
                {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            <div className="grid-2" style={{ marginBottom: 12 }}>
              <div>
                <label className="form-label">Email</label>
                <input className="form-input" value={targetEmail} onChange={(e) => setTargetEmail(e.target.value)} placeholder="mail@example.com" />
              </div>
              <div>
                <label className="form-label">Повне ім'я</label>
                <input className="form-input" value={targetFullName} onChange={(e) => setTargetFullName(e.target.value)} placeholder="Іван Іванов" />
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label className="form-label">Компанія</label>
              <input className="form-input" value={targetCompany} onChange={(e) => setTargetCompany(e.target.value)} placeholder="Юридична фірма Лекс" />
            </div>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Збереження..." : "Зберегти зміни"}
            </button>
          </form>
        </div>

        {/* Workspace Quick Info */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {team && (
             <>
               <div className="stat-card">
                 <div className="stat-label">Воркспейс ID</div>
                 <div className="stat-value" style={{ fontSize: 16 }}>{team.workspace_id}</div>
               </div>
               <div className="stat-card">
                 <div className="stat-label">Ваша роль</div>
                 <div className="stat-value" style={{ fontSize: 16 }}>{roleLabel(team.actor_role)}</div>
               </div>
               <div className="stat-card">
                 <div className="stat-label">Учасників</div>
                 <div className="stat-value" style={{ fontSize: 16 }}>{team.total}</div>
               </div>
             </>
          )}
        </div>
      </div>

      {/* Users List */}
      {team && (
        <div className="card-elevated" style={{ padding: 24, marginTop: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: "var(--text-primary)" }}>👥 Учасники команди</h2>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 8px" }}>
              <thead>
                <tr style={{ color: "var(--text-muted)", fontSize: 12, textTransform: "uppercase" }}>
                  <th style={{ textAlign: "left", padding: "0 12px" }}>Користувач</th>
                  <th style={{ textAlign: "left", padding: "0 12px" }}>Контакти</th>
                  <th style={{ textAlign: "left", padding: "0 12px" }}>Компанія</th>
                  <th style={{ textAlign: "center", padding: "0 12px" }}>Роль</th>
                </tr>
              </thead>
              <tbody>
                {team.items.map((item) => (
                  <tr key={item.user_id} className="card-elevated">
                    <td style={{ padding: "14px 12px", borderTopLeftRadius: 8, borderBottomLeftRadius: 8 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>{item.full_name || item.user_id.slice(0, 8) + "..."}</div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{item.user_id}</div>
                    </td>
                    <td style={{ padding: "14px 12px" }}>
                      <div style={{ fontSize: 12 }}>{item.email}</div>
                    </td>
                    <td style={{ padding: "14px 12px" }}>
                      <div style={{ fontSize: 12 }}>{item.company || "—"}</div>
                    </td>
                    <td style={{ padding: "14px 12px", borderTopRightRadius: 8, borderBottomRightRadius: 8, textAlign: "center" }}>
                      <span className={`badge ${roleBadge(item.role)}`}>{roleLabel(item.role)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
