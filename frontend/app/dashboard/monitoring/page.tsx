"use client";

import { FormEvent, useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import {
  checkRegistryWatchItem,
  createRegistryWatchItem,
  deleteRegistryWatchItem,
  getCurrentSubscription,
  getRegistryMonitorEvents,
  getRegistryMonitoringStatus,
  getRegistryWatchItems,
  runRegistryCheckDue,
  type RegistryMonitorEventsResponse,
  type RegistryMonitoringStatusResponse,
  type RegistryWatchListResponse
} from "@/lib/api";

const PLAN_RANK: Record<string, number> = {
  FREE: 0, PRO: 1, PRO_PLUS: 2,
};

function getPlanRank(plan: string | null | undefined): number {
  if ((plan || "").toUpperCase() === "PRO_PLUS") return 2;
  if ((plan || "").toUpperCase() === "PRO") return 1;
  return 0;
}

export default function MonitoringPage() {
  const [currentPlan, setCurrentPlan] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);
  const [accessLoading, setAccessLoading] = useState(false);

  const [source, setSource] = useState("opendatabot");
  const [registryType, setRegistryType] = useState("edr");
  const [identifier, setIdentifier] = useState("");
  const [entityName, setEntityName] = useState("");
  const [checkIntervalHours, setCheckIntervalHours] = useState("24");
  const [notes, setNotes] = useState("");

  const [watchItems, setWatchItems] = useState<RegistryWatchListResponse | null>(null);
  const [events, setEvents] = useState<RegistryMonitorEventsResponse | null>(null);
  const [monitoringStatus, setMonitoringStatus] = useState<RegistryMonitoringStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const activeSubscription = (currentStatus || "").toLowerCase() === "active";
  const canUseMonitoring = activeSubscription && getPlanRank(currentPlan) >= getPlanRank("PRO_PLUS");

  useEffect(() => {
    async function init() {
      setLoading(true);
      await refreshEntitlements();
      if (canUseMonitoring) {
        await Promise.all([loadStatus(), loadWatchItems(), loadEvents()]);
      }
      setLoading(false);
    }
    init();
  }, [canUseMonitoring]);

  async function refreshEntitlements(): Promise<void> {
    try {
      const subscription = await getCurrentSubscription(getToken(), getUserId());
      setCurrentPlan(subscription.plan);
      setCurrentStatus(subscription.status);
    } catch (err) { setError(String(err)); }
  }

  async function loadWatchItems(page: number = 1): Promise<void> {
    try {
      const result = await getRegistryWatchItems({ page, page_size: 20 }, getToken(), getUserId());
      setWatchItems(result);
    } catch (err) { setError(String(err)); }
  }

  async function loadStatus(): Promise<void> {
    try {
      const result = await getRegistryMonitoringStatus(getToken(), getUserId());
      setMonitoringStatus(result);
    } catch (err) { setError(String(err)); }
  }

  async function loadEvents(page: number = 1): Promise<void> {
    try {
      const result = await getRegistryMonitorEvents({ page, page_size: 20 }, getToken(), getUserId());
      setEvents(result);
    } catch (err) { setError(String(err)); }
  }

  async function onCreateWatch(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setCreating(true);
    try {
      await createRegistryWatchItem(
        { source, registry_type: registryType, identifier, entity_name: entityName, check_interval_hours: 24, notes },
        getToken(), getUserId()
      );
      setIdentifier(""); setEntityName("");
      setInfo("✅ Об'єкт успішно доданий до моніторингу.");
      await Promise.all([loadStatus(), loadWatchItems(), loadEvents()]);
    } catch (err) { setError(String(err)); }
    finally { setCreating(false); }
  }

  if (loading && !accessLoading) return (
    <div className="flex items-center justify-center p-40">
       <div className="scanning-animation">
          <div className="radar"></div>
          <p className="mt-8 text-gold font-bold uppercase tracking-widest text-xs">Сканування мережі реєстрів...</p>
       </div>
    </div>
  );

  return (
    <div className="monitoring-luxury-container animate-fade-in">
      <div className="section-header-centered mb-12">
        <div className="badge-luxury mb-4">Risk Intelligence Center</div>
        <h1 className="luxury-title">Моніторинг Ризиків</h1>
        <p className="luxury-subtitle">Автоматичне відстеження змін у ЄДР та судових реєстрах через Opendatabot API</p>
      </div>

      {info && <div className="alert-premium success mb-8">{info}</div>}
      {error && <div className="alert-premium danger mb-8">{error}</div>}

      <div className="monitoring-grid">
        {/* Statistics Widgets */}
        <div className="stats-row mb-12">
          {[
            { label: "Під наглядом", value: monitoringStatus?.total_watch_items ?? 0, color: "var(--accent)" },
            { label: "Критичні зміни", value: monitoringStatus?.warning_watch_items ?? 0, color: "#ef4444" },
            { label: "Черга перевірки", value: monitoringStatus?.due_watch_items ?? 0, color: "var(--gold-400)" },
            { label: "Status", value: "ОК", color: "var(--success)" },
          ].map(s => (
            <div key={s.label} className="card-elevated glass-card stat-widget">
               <div className="stat-glow" style={{ background: s.color }}></div>
               <label>{s.label}</label>
               <div className="value" style={{ color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>

        <div className="main-monitor-layout">
          {/* Watch List Section */}
          <div className="watch-section">
            <div className="flex justify-between items-center mb-8">
               <h2 className="luxury-section-title">Об'єкти спостереження</h2>
               <div className="flex gap-4">
                  <div className="search-pill">
                     <span className="icon">🔍</span>
                     <input placeholder="Швидкий фільтр..." />
                  </div>
               </div>
            </div>

            <div className="watch-items-cards-grid">
              {(watchItems?.items || []).map(item => (
                <div key={item.id} className="watch-card card-elevated">
                   <div className="card-top">
                      <span className="registry-tag">{item.registry_type.toUpperCase()}</span>
                      <div className="card-actions">
                         <button className="icon-btn">🔄</button>
                         <button className="icon-btn danger text-xs">🗑</button>
                      </div>
                   </div>
                   <h3 className="entity-title">{item.entity_name}</h3>
                   <div className="entity-id">{item.identifier}</div>
                   
                   <div className="card-status-footer mt-6">
                      <div className="last-check">
                         <span className="dot"></span> Останній скан: сьогодні
                      </div>
                      <div className="health-bar"><div className="fill"></div></div>
                   </div>
                </div>
              ))}
              
              <div className="add-watch-placeholder card-elevated" onClick={() => (document.getElementById('add-form') as any)?.scrollIntoView({behavior: 'smooth'})}>
                 <div className="plus">+</div>
                 <p>Додати новий об'єкт</p>
              </div>
            </div>
          </div>

          {/* Activity/Alerts Sidebar */}
          <div className="alerts-sidebar">
             <div className="card-elevated p-8 mb-8" id="add-form">
                <h3 className="luxury-title-sm mb-6">➕ Новий запит</h3>
                <form onSubmit={onCreateWatch} className="flex-col gap-5">
                   <div className="form-group">
                      <label>Реєстр</label>
                      <select className="form-input-luxury" value={registryType} onChange={e => setRegistryType(e.target.value)}>
                         <option value="edr">ЄДР (Компанії)</option>
                         <option value="court">Судові справи</option>
                      </select>
                   </div>
                   <div className="form-group">
                      <label>Ідентифікатор (Код/Номер)</label>
                      <input className="form-input-luxury" value={identifier} onChange={e => setIdentifier(e.target.value)} required />
                   </div>
                   <div className="form-group">
                      <label>Найменування</label>
                      <input className="form-input-luxury" value={entityName} onChange={e => setEntityName(e.target.value)} required />
                   </div>
                   <button type="submit" className="btn-luxury btn-featured w-full mt-2" disabled={creating || !canUseMonitoring}>
                      {creating ? "Запуск..." : "Бути в курсі змін"}
                   </button>
                </form>
             </div>

             <div className="card-elevated p-8">
                <h3 className="luxury-title-sm mb-6">🔔 Стрічка змін</h3>
                <div className="events-luxury-list">
                   {(events?.items || []).map(ev => (
                      <div key={ev.id} className={`event-luxury-item ${ev.severity}`}>
                         <div className="act-dot"></div>
                         <div className="act-content">
                            <strong>{ev.title}</strong>
                            <p>{ev.created_at}</p>
                         </div>
                      </div>
                   ))}
                   {(!events || events.items.length === 0) && (
                      <div className="text-center py-10 text-muted italic">Сповіщень не виявлено</div>
                   )}
                </div>
             </div>
          </div>
        </div>
      </div>

      {!canUseMonitoring && (
        <div className="premium-lock-overlay">
           <div className="lock-content card-elevated p-12 text-center border-gold">
              <div className="lock-icon-large">🏛️</div>
              <h2 className="luxury-title-sm mt-6">Моніторинг реєстрів PRO+</h2>
              <p className="text-secondary mt-4 mb-8 max-w-sm mx-auto">
                 Ця функція доступна лише в **Enterprise** версії. Відстежуйте зміни автоматично кожну годину.
              </p>
              <button className="btn-luxury btn-featured px-12" onClick={() => window.location.href='/dashboard/billing'}>ПЕРЕЙТИ НА PRO+</button>
           </div>
        </div>
      )}

      <style jsx>{`
        .monitoring-luxury-container { position: relative; padding-bottom: 100px; }
        .section-header-centered { text-align: center; }
        .luxury-title { font-size: 44px; font-weight: 950; letter-spacing: -0.04em; background: linear-gradient(to right, #fff, var(--gold-400)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .luxury-subtitle { font-size: 16px; color: var(--text-muted); max-width: 600px; margin: 8px auto 0; }
        
        .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
        .stat-widget { padding: 32px; border-radius: 28px; position: relative; overflow: hidden; text-align: center; }
        .stat-glow { position: absolute; top: -50px; left: 50%; width: 100px; height: 100px; transform: translateX(-50%); opacity: 0.1; filter: blur(40px); border-radius: 50%; }
        .stat-widget label { display: block; font-size: 11px; font-weight: 800; text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; letter-spacing: 1px; }
        .stat-widget .value { font-size: 36px; font-weight: 950; }

        .main-monitor-layout { display: grid; grid-template-columns: 2fr 450px; gap: 40px; }
        .luxury-section-title { font-size: 24px; font-weight: 900; }
        
        .search-pill { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); padding: 8px 16px; border-radius: 100px; display: flex; align-items: center; gap: 10px; }
        .search-pill input { background: transparent; border: none; outline: none; color: #fff; font-size: 13px; width: 150px; }

        .watch-items-cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 24px; margin-top: 32px; }
        .watch-card { padding: 32px; border-radius: 32px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); border: 1px solid rgba(255,255,255,0.04); }
        .watch-card:hover { transform: translateY(-8px); border-color: rgba(212,168,67,0.3); box-shadow: 0 20px 40px rgba(0,0,0,0.4); }
        
        .card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .registry-tag { font-size: 10px; font-weight: 900; color: var(--gold-400); background: rgba(212,168,67,0.1); padding: 4px 10px; border-radius: 6px; }
        .card-actions { display: flex; gap: 8px; opacity: 0; transition: opacity 0.3s; }
        .watch-card:hover .card-actions { opacity: 1; }
        .icon-btn { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.05); width: 32px; height: 32px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .icon-btn:hover { background: rgba(255,255,255,0.1); }
        
        .entity-title { font-size: 16px; font-weight: 800; color: #fff; margin-bottom: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 48px; }
        .entity-id { font-size: 12px; color: var(--text-muted); font-family: monospace; }
        
        .card-status-footer { border-top: 1px solid rgba(255,255,255,0.05); padding-top: 16px; }
        .last-check { font-size: 10px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
        .last-check .dot { width: 6px; height: 6px; background: var(--success); border-radius: 50%; box-shadow: 0 0 6px var(--success); }
        .health-bar { height: 4px; background: rgba(255,255,255,0.03); border-radius: 2px; margin-top: 10px; overflow: hidden; }
        .health-bar .fill { width: 100%; height: 100%; background: var(--gold-500); opacity: 0.5; }

        .add-watch-placeholder { min-height: 200px; border: 2px dashed rgba(255,255,255,0.05); border-radius: 32px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; transition: all 0.3s; }
        .add-watch-placeholder:hover { background: rgba(255,255,255,0.02); border-color: var(--gold-500); }
        .add-watch-placeholder .plus { font-size: 40px; color: var(--gold-400); margin-bottom: 12px; opacity: 0.5; }
        .add-watch-placeholder p { font-size: 12px; font-weight: 700; color: var(--text-muted); }

        .luxury-title-sm { font-size: 18px; font-weight: 800; color: #fff; }
        .form-input-luxury { width: 100%; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 16px; color: #fff; font-size: 14px; outline: none; transition: all 0.2s; }
        .form-input-luxury:focus { border-color: var(--gold-500); background: rgba(255,255,255,0.05); }

        .events-luxury-list { display: flex; flex-direction: column; gap: 20px; }
        .event-luxury-item { display: flex; gap: 16px; position: relative; padding-left: 16px; }
        .event-luxury-item::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px; background: rgba(255,255,255,0.05); }
        .event-luxury-item.high::before { background: #ef4444; }
        .act-dot { width: 8px; height: 8px; background: var(--gold-500); border-radius: 50%; margin-top: 6px; }
        .act-content strong { display: block; font-size: 13px; margin-bottom: 2px; }
        .act-content p { font-size: 11px; color: var(--text-muted); }

        .premium-lock-overlay { position: fixed; inset: 0; background: rgba(6,13,26,0.7); backdrop-filter: blur(12px); z-index: 1000; display: flex; align-items: center; justify-content: center; }
        .lock-icon-large { font-size: 80px; filter: drop-shadow(0 0 20px var(--gold-500)); }

        .scanning-animation { text-align: center; }
        .radar { width: 100px; height: 100px; border: 2px solid var(--gold-500); border-radius: 50%; position: relative; animation: radar 2s linear infinite; margin: 0 auto; }
        .radar::after { content: ''; position: absolute; top: 50%; left: 50%; width: 50%; height: 2px; background: var(--gold-500); transform-origin: 0 50%; animation: sweep 2s linear infinite; }
        @keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes radar { 0% { box-shadow: 0 0 0 0 rgba(212,168,67,0.4); } 100% { box-shadow: 0 0 0 40px rgba(212,168,67,0); } }
      `}</style>
    </div>
  );
}
