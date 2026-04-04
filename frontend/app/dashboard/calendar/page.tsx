"use client";

import { useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import { getDeadlines, getECourtHearings, searchPublicCourtCase, type DeadlineItem, type ECourtHearingItem } from "@/lib/api";

type DayInfo = {
  day: number;
  date: Date;
  isCurrentMonth: boolean;
  hearings: ECourtHearingItem[];
  deadlines: DeadlineItem[];
};

export default function CalendarPage() {
  const [hearings, setHearings] = useState<ECourtHearingItem[]>([]);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [selectedHearing, setSelectedHearing] = useState<ECourtHearingItem | null>(null);
  const [selectedDeadline, setSelectedDeadline] = useState<DeadlineItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [searchCaseNumber, setSearchCaseNumber] = useState("");

  useEffect(() => {
    void fetchHearings();
  }, []);

  async function fetchHearings() {
    setLoading(true);
    setError("");
    try {
      const token = getToken();
      const userId = getUserId();
      const [hearingsResponse, deadlinesResponse] = await Promise.all([
        getECourtHearings(token),
        getDeadlines(token, userId),
      ]);
      setHearings(hearingsResponse.items);
      setDeadlines(deadlinesResponse.items);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handlePublicSearch() {
    if (!searchCaseNumber.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await searchPublicCourtCase(searchCaseNumber.trim(), getToken());
      
      const newHearings = [...hearings];
      response.assignments.forEach(a => {
        const h: ECourtHearingItem = {
          id: `search_${Math.random().toString(36).substr(2, 9)}`,
          case_number: response.case_number,
          court_name: a.court_name || "Невідомий суд",
          date: a.date.substring(0, 10),
          time: a.date.substring(11, 16) || a.time || "00:00",
          subject: a.subject || "Судове засідання",
          judge: a.judge || "Не вказано",
          status: "scheduled"
        };
        newHearings.push(h);
      });
      
      setHearings(newHearings);
      setSelectedDeadline(null);
      setSearchCaseNumber("");
      
      if (response.assignments.length > 0) {
        // Switch calendar to the month of the first found hearing
        const d = new Date(response.assignments[0].date);
        if (!isNaN(d.getTime())) {
          setCurrentDate(d);
        }
      } else {
        setError(`Засідань по справі ${searchCaseNumber} не знайдено`);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  const daysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate();
  const firstDayOfMonth = (year: number, month: number) => new Date(year, month, 1).getDay();

  const getCalendarDays = (): DayInfo[] => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const days: DayInfo[] = [];
    const firstDay = (firstDayOfMonth(year, month) + 6) % 7;
    const prevMonthDays = daysInMonth(year, month - 1);
    for (let i = firstDay - 1; i >= 0; i--) {
      const d = new Date(year, month - 1, prevMonthDays - i);
      days.push({ day: prevMonthDays - i, date: d, isCurrentMonth: false, hearings: getHearingsForDate(d), deadlines: getDeadlinesForDate(d) });
    }
    const totalDays = daysInMonth(year, month);
    for (let i = 1; i <= totalDays; i++) {
      const d = new Date(year, month, i);
      days.push({ day: i, date: d, isCurrentMonth: true, hearings: getHearingsForDate(d), deadlines: getDeadlinesForDate(d) });
    }
    const remaining = 42 - days.length;
    for (let i = 1; i <= remaining; i++) {
      const d = new Date(year, month + 1, i);
      days.push({ day: i, date: d, isCurrentMonth: false, hearings: getHearingsForDate(d), deadlines: getDeadlinesForDate(d) });
    }
    return days;
  };

  const getHearingsForDate = (date: Date) => {
    const iso = date.toISOString().split("T")[0];
    return hearings.filter(h => h.date === iso);
  };

  const getDeadlinesForDate = (date: Date) => {
    const iso = date.toISOString().split("T")[0];
    return deadlines.filter((item) => item.end_date === iso || item.start_date === iso);
  };

  const changeMonth = (offset: number) => {
    const next = new Date(currentDate);
    next.setMonth(next.getMonth() + offset);
    setCurrentDate(next);
  };

  const monthName = currentDate.toLocaleString("uk-UA", { month: "long" });
  const year = currentDate.getFullYear();
  const isToday = (date: Date) => {
    const today = new Date();
    return date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getFullYear() === today.getFullYear();
  };

  return (
    <div className="animate-fade-in">
      <div className="section-header">
        <div>
          <h1 className="section-title">Календар подій справ</h1>
          <p className="section-subtitle">Засідання з Е-Суду та збережені строки по справах в одному календарі</p>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setCurrentDate(new Date())}>Сьогодні</button>
          <button className="btn btn-primary btn-sm" onClick={fetchHearings} disabled={loading}>
            {loading ? "Синхронізація..." : "↻ Оновити з Е-Суд"}
          </button>
        </div>
      </div>

      {/* Public Search Bar */}
      <div className="card-elevated" style={{ padding: "20px", marginBottom: "32px", display: "flex", gap: "16px", alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          <label className="form-label">Публічний пошук за номером справи</label>
          <input 
            className="form-input" 
            placeholder="Напр. 757/12345/23-ц" 
            value={searchCaseNumber}
            onChange={(e) => setSearchCaseNumber(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handlePublicSearch()}
          />
        </div>
        <button className="btn btn-secondary" onClick={handlePublicSearch} disabled={loading || !searchCaseNumber.trim()}>
          {loading ? "Пошук..." : "🔍 Знайти засідання"}
        </button>
      </div>

      {error && <div className="preflight-block" style={{ marginBottom: "20px" }}><span style={{ color: "var(--danger)" }}>⚠ {error}</span></div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: "32px", alignItems: "start" }}>
        {/* Calendar Card */}
        <div className="card-elevated" style={{ padding: "32px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px" }}>
            <h2 style={{ fontSize: "24px", fontWeight: 800, color: "#fff", textTransform: "capitalize" }}>
              {monthName} <span style={{ color: "var(--gold-400)" }}>{year}</span>
            </h2>
            <div style={{ display: "flex", gap: "10px" }}>
              <button className="btn-nav" onClick={() => changeMonth(-1)}>←</button>
              <button className="btn-nav" onClick={() => changeMonth(1)}>→</button>
            </div>
          </div>

          <div style={{ 
            display: "grid", gridTemplateColumns: "repeat(7, 1fr)", 
            gap: "1px", background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.05)", borderRadius: "16px", overflow: "hidden" 
          }}>
            {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"].map(d => (
              <div key={d} style={{ padding: "12px", textAlign: "center", fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", background: "rgba(0,0,0,0.2)" }}>{d}</div>
            ))}
            {getCalendarDays().map((info, idx) => (
              <div key={idx} style={{ 
                minHeight: "120px", padding: "12px", 
                background: info.isCurrentMonth ? "rgba(11,22,40,0.3)" : "rgba(0,0,0,0.2)",
                opacity: info.isCurrentMonth ? 1 : 0.4,
                border: isToday(info.date) ? "1px solid var(--gold-500)" : "1px solid rgba(255,255,255,0.02)",
                position: "relative"
              }}>
                <div style={{ 
                  fontSize: "14px", fontWeight: 700, 
                  color: isToday(info.date) ? "var(--gold-400)" : "#fff",
                  marginBottom: "8px"
                }}>{info.day}</div>
                
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  {info.hearings.map(h => (
                    <div 
                      key={h.id} 
                      onClick={() => { setSelectedHearing(h); setSelectedDeadline(null); }}
                      className="hearing-pill"
                      style={{
                        padding: "4px 8px", fontSize: "10px", borderRadius: "4px",
                        background: h.status === 'completed' ? "rgba(255,255,255,0.05)" : "rgba(212,168,67,0.15)",
                        borderLeft: `2px solid ${h.status === 'completed' ? 'var(--text-muted)' : 'var(--gold-500)'}`,
                        cursor: "pointer", color: "#fff", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
                      }}
                    >
                      <span style={{ fontWeight: 800, marginRight: "4px" }}>{h.time}</span> {h.case_number}
                    </div>
                  ))}
                  {info.deadlines.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => { setSelectedDeadline(item); setSelectedHearing(null); }}
                      className="deadline-pill"
                      style={{
                        padding: "4px 8px", fontSize: "10px", borderRadius: "4px",
                        background: "rgba(96,165,250,0.14)",
                        borderLeft: "2px solid #60a5fa",
                        cursor: "pointer", color: "#fff", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
                      }}
                    >
                      <span style={{ fontWeight: 800, marginRight: "4px" }}>строк</span> {item.title}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Details Panel */}
        <div style={{ position: "sticky", top: "24px" }}>
          {selectedHearing ? (
            <div className="card-elevated animate-slide-up" style={{ padding: "32px", border: "1px solid rgba(212,168,67,0.2)" }}>
              <div style={{ marginBottom: "24px" }}>
                <span className="badge badge-gold" style={{ marginBottom: "12px" }}>Засідання</span>
                <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#fff" }}>{selectedHearing.case_number}</h3>
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div className="info-item">
                  <div className="info-label">Суд</div>
                  <div className="info-value">{selectedHearing.court_name}</div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  <div className="info-item">
                    <div className="info-label">Дата</div>
                    <div className="info-value">{selectedHearing.date}</div>
                  </div>
                  <div className="info-item">
                    <div className="info-label">Час</div>
                    <div className="info-value">{selectedHearing.time}</div>
                  </div>
                </div>
                <div className="info-item">
                  <div className="info-label">Предмет</div>
                  <div className="info-value" style={{ fontSize: "13px", fontWeight: 400, opacity: 0.8 }}>{selectedHearing.subject}</div>
                </div>
                <div className="info-item">
                  <div className="info-label">Суддя</div>
                  <div className="info-value">{selectedHearing.judge}</div>
                </div>
              </div>

              <div style={{ marginTop: "32px", display: "flex", gap: "12px" }}>
                <button className="btn btn-primary w-full">Картка справи</button>
                <button className="btn btn-secondary">PDF</button>
              </div>
            </div>
          ) : selectedDeadline ? (
            <div className="card-elevated animate-slide-up" style={{ padding: "32px", border: "1px solid rgba(96,165,250,0.22)" }}>
              <div style={{ marginBottom: "24px" }}>
                <span className="badge" style={{ marginBottom: "12px", background: "rgba(96,165,250,0.14)", color: "#93c5fd" }}>Строк</span>
                <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#fff" }}>{selectedDeadline.title}</h3>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  <div className="info-item">
                    <div className="info-label">Початок</div>
                    <div className="info-value">{selectedDeadline.start_date || "—"}</div>
                  </div>
                  <div className="info-item">
                    <div className="info-label">Кінець</div>
                    <div className="info-value">{selectedDeadline.end_date || "—"}</div>
                  </div>
                </div>
                <div className="info-item">
                  <div className="info-label">Тип</div>
                  <div className="info-value">{selectedDeadline.deadline_type || "other"}</div>
                </div>
                <div className="info-item">
                  <div className="info-label">Нотатки</div>
                  <div className="info-value" style={{ fontSize: "13px", fontWeight: 400, opacity: 0.8 }}>
                    {selectedDeadline.notes || "Без додаткових нотаток"}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card-elevated" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
              <div style={{ fontSize: "40px", marginBottom: "16px" }}>🕒</div>
              <p style={{ fontSize: "14px", lineHeight: 1.6 }}>Оберіть засідання або строк у календарі, щоб переглянути деталі події.</p>
            </div>
          )}

          <div className="card-elevated" style={{ marginTop: "24px", padding: "24px", background: "rgba(212,168,67,0.05)", border: "1px solid rgba(212,168,67,0.1)" }}>
             <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--gold-400)", marginBottom: "8px" }}>💡 Розумні повідомлення</h4>
             <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
               Система автоматично надішле вам нагадування за 24 години та за 2 години до початку засідання.
             </p>
          </div>
        </div>
      </div>

      <style jsx>{`
        .btn-nav {
          width: 36px; height: 36px; borderRadius: 8px;
          background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
          color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center;
          transition: all 0.2s;
        }
        .btn-nav:hover { background: var(--gold-500); color: #000; border-color: var(--gold-500); }
        .info-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; font-weight: 700; }
        .info-value { font-size: 15px; color: #fff; fontWeight: 700; }
        .hearing-pill:hover { background: var(--gold-500) !important; color: #000 !important; }
        .deadline-pill:hover { background: #60a5fa !important; color: #08111f !important; }
      `}</style>
    </div>
  );
}
