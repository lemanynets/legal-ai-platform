"use client";

import { useState, useEffect } from "react";
import { getToken, getUserId } from "@/lib/auth";
import {
  bulkDeleteDocuments,
  cloneDocument,
  deleteDocument,
  exportDocument,
  getDocumentDetail,
  getDocumentsHistory,
  updateDocument,
  getCases,
  submitToECourt,
  getECourtCourts,
  type DocumentsHistoryResponse,
  type Case
} from "@/lib/api";

const PLAN_RANK: Record<string, number> = {
  FREE: 0,
  START: 1,
  PRO: 2,
  PRO_PLUS: 3,
  TEAM: 4
};

function getPlanRank(plan: string | null | undefined): number {
  return PLAN_RANK[(plan || "").toUpperCase()] ?? -1;
}

export default function DocumentsHistoryPage() {
  const [history, setHistory] = useState<DocumentsHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [docType, setDocType] = useState("");
  const [sortBy, setSortBy] = useState<"created_at" | "document_type" | "document_category">("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [pageSize] = useState(12);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [courtList, setCourtList] = useState<string[]>([]);
  const [selectedCourt, setSelectedCourt] = useState("");
  const [signerMethod, setSignerMethod] = useState<"file_key" | "hardware_token" | "remote_id">("file_key");
  const [submissionNote, setSubmissionNote] = useState("");

  useEffect(() => {
    loadHistory(1);
    loadCases();
  }, []);

  useEffect(() => {
    loadHistory(1);
  }, [selectedCaseId]);

  async function loadCases() {
    try {
      const data = await getCases(getToken(), getUserId());
      setCases(data);
    } catch (err) { console.error(err); }
  }

  async function loadHistory(page: number = 1): Promise<void> {
    setLoading(true);
    setError("");
    try {
      const result = await getDocumentsHistory(
        {
          page,
          page_size: pageSize,
          query: query.trim() || undefined,
          doc_type: docType.trim() || undefined,
          case_id: selectedCaseId || undefined,
          sort_by: sortBy,
          sort_dir: sortDir
        },
        getToken(),
        getUserId()
      );
      setHistory(result);
    } catch (err) {
      setError("Не вдалося завантажити документи. Перевірте з'єднання з сервером.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function onExport(documentId: string, format: "docx" | "pdf"): Promise<void> {
    setActionLoadingId(`${documentId}-${format}`);
    try {
      const blob = await exportDocument(documentId, format, false, getToken(), getUserId());
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `document-${documentId}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError("Помилка при експорті документа.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function onDelete(documentId: string): Promise<void> {
    if (!confirm("Ви впевнені, що хочете видалити цей документ?")) return;
    setActionLoadingId(`${documentId}-delete`);
    try {
      await deleteDocument(documentId, getToken(), getUserId());
      await loadHistory(history?.page ?? 1);
    } catch (err) {
      setError("Не вдалося видалити документ.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function onClone(documentId: string): Promise<void> {
    setActionLoadingId(`${documentId}-clone`);
    try {
      await cloneDocument(documentId, getToken(), getUserId());
      await loadHistory(1);
    } catch (err) {
      setError("Не вдалося клонувати документ.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function onEditStart(documentId: string): Promise<void> {
    setActionLoadingId(`${documentId}-edit`);
    try {
      const detail = await getDocumentDetail(documentId, getToken(), getUserId());
      setEditingId(documentId);
      setEditingText(detail.generated_text || "");
      setSelectedCaseId(detail.case_id || "");
    } catch (err) {
      setError("Не вдалося завантажити текст для редагування.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function onSaveEdit(): Promise<void> {
    if (!editingId) return;
    setSaving(true);
    try {
      await updateDocument(editingId, editingText, getToken(), getUserId(), selectedCaseId || undefined);
      setEditingId(null);
      await loadHistory(history?.page ?? 1);
    } catch (err) {
      setError("Помилка при збереженні.");
    } finally {
      setSaving(false);
    }
  }

  async function onOpenSubmitModal(documentId: string): Promise<void> {
    setSubmittingId(documentId);
    setSubmissionNote("");
    try {
      const data = await getECourtCourts(getToken(), getUserId());
      setCourtList(data.courts);
      if (data.courts.length > 0) setSelectedCourt(data.courts[0]);
    } catch (err) {
      console.error(err);
      setError("Не вдалося завантажити список судів.");
    }
  }

  async function onFinalSubmitToECourt(): Promise<void> {
    if (!submittingId || !selectedCourt) return;
    setSaving(true);
    try {
      await submitToECourt(
        {
          document_id: submittingId,
          court_name: selectedCourt,
          signer_method: signerMethod,
          note: submissionNote,
        },
        getToken(),
        getUserId()
      );
      setSubmittingId(null);
      alert("Документ успішно подано до Е-Суду!");
      await loadHistory(history?.page ?? 1);
    } catch (err: any) {
      setError(`Помилка при подачі: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="documents-container animate-fade-in">
      <div className="section-header">
        <div>
          <h1 className="section-title">Архів документів</h1>
          <p className="section-subtitle">Інтелектуальне сховище ваших юридичних напрацювань.</p>
        </div>
        <button className="btn btn-primary btn-glow" onClick={() => window.location.href = '/dashboard/generate'}>
          <span>+</span> Новий документ
        </button>
      </div>

      <div className="filter-bar glass-morphism">
        <div className="filter-group-premium">
          <span className="premium-icon">🔍</span>
          <input 
            type="text" 
            placeholder="Пошук у назвах та категоріях..." 
            value={query} 
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadHistory(1)}
          />
        </div>
        <div className="filter-group-premium" style={{ maxWidth: '200px' }}>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
            <option value="document_category">За категорією</option>
          </select>
        </div>
        <div className="filter-group-premium" style={{ maxWidth: '250px' }}>
          <select value={selectedCaseId} onChange={(e) => setSelectedCaseId(e.target.value)}>
            <option value="">Всі справи</option>
            {cases.map(c => (
              <option key={c.id} value={c.id}>📁 {c.title}</option>
            ))}
          </select>
        </div>
        <button className="btn btn-glow-subtle" onClick={() => loadHistory(1)}>
          Оновити
        </button>
      </div>

      {error && <div className="error-toast-float">{error}</div>}

      {loading ? (
        <div className="loading-state-premium">
          <div className="premium-spinner"></div>
          <p>Завантажуємо історію...</p>
        </div>
      ) : (
        <div className="document-grid-premium">
          {history?.items.length === 0 ? (
            <div className="empty-state-luxury card-elevated">
              <div className="luxury-icon-ring">📄</div>
              <h3>Ваш архів поки що порожній</h3>
              <p>Створіть свій перший юридичний шедевр за допомогою нашого інтелектуального AI.</p>
              <button className="btn btn-primary" onClick={() => window.location.href = '/dashboard/generate'}>
                Створити документ
              </button>
            </div>
          ) : (
            history?.items.map((doc) => (
              <div key={doc.id} className="document-card-luxury">
                <div className="card-top">
                  <span className="luxury-badge">{doc.document_category || "Документ"}</span>
                  <div className="doc-date-luxury">{new Date(doc.created_at).toLocaleDateString('uk-UA')}</div>
                </div>
                
                <h3 className="luxury-doc-title">{doc.title}</h3>
                <p className="luxury-doc-preview">{doc.preview_text || "Попередній перегляд недоступний..."}</p>

                <div className="luxury-card-actions">
                  <div className="action-main-buttons">
                    <button 
                      className="btn-lux btn-lux-docx" 
                      onClick={() => onExport(doc.id, "docx")}
                      disabled={actionLoadingId === `${doc.id}-docx`}
                    >
                      {actionLoadingId === `${doc.id}-docx` ? "..." : "DOCX"}
                    </button>
                    <button 
                      className="btn-lux btn-lux-pdf" 
                      onClick={() => onExport(doc.id, "pdf")}
                      disabled={actionLoadingId === `${doc.id}-pdf`}
                    >
                      {actionLoadingId === `${doc.id}-pdf` ? "..." : "PDF"}
                    </button>
                  </div>
                  <div className="action-utility-buttons">
                    <button onClick={() => onEditStart(doc.id)} className="btn-icon-link" title="Редагувати">✎</button>
                    <button onClick={() => onClone(doc.id)} className="btn-icon-link" title="Копіювати">📋</button>
                    <button onClick={() => onOpenSubmitModal(doc.id)} className="btn-icon-link" title="Подати в Е-Суд" style={{ color: 'var(--gold-400)' }}>🏛</button>
                    <button onClick={() => onDelete(doc.id)} className="btn-icon-link danger" title="Видалити">🗑</button>
                  </div>
                </div>
                
                {doc.used_ai && <div className="ai-tag">AI Powered</div>}
              </div>
            ))
          )}
        </div>
      )}

      {history && history.pages > 1 && (
        <div className="pagination-luxury">
          <button disabled={history.page <= 1} onClick={() => loadHistory(history.page - 1)}>← Previous</button>
          <div className="page-dots">
            {[...Array(history.pages)].map((_, i) => (
              <span key={i} className={`page-dot ${history.page === i + 1 ? 'active' : ''}`} onClick={() => loadHistory(i + 1)}></span>
            ))}
          </div>
          <button disabled={history.page >= history.pages} onClick={() => loadHistory(history.page + 1)}>Next →</button>
        </div>
      )}

      {editingId && (
        <div className="modal-overlay-blur">
          <div className="modal-content-luxury card-elevated" style={{ animation: 'fadeIn 0.3s ease-out' }}>
            <div className="modal-header flex justify-between items-center mb-6">
              <div>
                <h2 className="text-xl font-black">Редагування документа</h2>
                <div className="text-xs text-muted mt-1 uppercase tracking-tighter">Платформа Legal AI — Інтелектуальний редактор</div>
              </div>
              <button className="btn btn-secondary p-2" style={{ borderRadius: '50%', width: 40, height: 40 }} onClick={() => setEditingId(null)}>&times;</button>
            </div>
            
            <div className="flex gap-4 items-center mb-4 p-4 rounded-xl bg-black bg-opacity-30 border border-white border-opacity-5">
               <div className="flex-grow">
                  <label className="form-label text-xs">Прив'язка до справи</label>
                  <select 
                    className="form-input text-xs p-2 h-10" 
                    value={selectedCaseId} 
                    onChange={(e) => setSelectedCaseId(e.target.value)}
                  >
                    <option value="">Без справи</option>
                    {cases.map(c => <option key={c.id} value={c.id}>📁 {c.title}</option>)}
                  </select>
               </div>
               <div className="flex gap-2">
                  <div className="text-center px-4 py-2 bg-white bg-opacity-5 rounded-lg">
                     <div className="text-xl font-bold">{editingText.split(/\s+/).filter(Boolean).length}</div>
                     <div className="text-muted" style={{ fontSize: 9, textTransform: 'uppercase' }}>Слів</div>
                  </div>
                  <div className="text-center px-4 py-2 bg-white bg-opacity-5 rounded-lg">
                     <div className="text-xl font-bold">{editingText.length}</div>
                     <div className="text-muted" style={{ fontSize: 9, textTransform: 'uppercase' }}>Символів</div>
                  </div>
               </div>
            </div>

            <div className="editor-toolbar flex gap-2 mb-2">
               <button className="btn btn-xs btn-secondary" onClick={() => setEditingText(prev => prev.toUpperCase())}>ВЕРХНІЙ РЕГІСТР</button>
               <button className="btn btn-xs btn-secondary" onClick={() => setEditingText(prev => prev.toLowerCase())}>нижній регістр</button>
               <button className="btn btn-xs btn-secondary" onClick={() => setEditingText(prev => prev.trim())}>Видалити зайві пробіли</button>
            </div>

            <textarea 
              value={editingText} 
              onChange={(e) => setEditingText(e.target.value)}
              className="luxury-textarea"
              placeholder="Почніть писати ваш юридичний документ тут..."
            />
            
            <div className="modal-footer flex justify-between items-center mt-6">
              <div className="text-xs text-muted flex items-center gap-2">
                 <span className="w-2 h-2 rounded-full bg-success"></span>
                 Автозбереження активне
              </div>
              <div className="flex gap-4">
                <button className="btn btn-secondary" onClick={() => setEditingId(null)}>Скасувати</button>
                <button className="btn btn-primary btn-glow" onClick={onSaveEdit} disabled={saving}>
                  {saving ? "Збереження..." : "Зберегти зміни"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {submittingId && (
        <div className="modal-overlay-blur">
          <div className="modal-content-luxury card-elevated" style={{ maxWidth: '500px' }}>
            <h2 className="text-xl font-black mb-6">Подача до Е-Суду</h2>
            
            <div className="form-group mb-4">
              <label className="form-label">Виберіть суд</label>
              <select className="form-select" value={selectedCourt} onChange={(e) => setSelectedCourt(e.target.value)}>
                {courtList.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div className="form-group mb-4">
              <label className="form-label">Метод підпису</label>
              <select className="form-select" value={signerMethod} onChange={(e) => setSignerMethod(e.target.value as any)}>
                <option value="file_key">Файловий ключ (КЕП)</option>
                <option value="hardware_token">Апаратний токен</option>
                <option value="remote_id">Дія.Підпис / Cloud ID</option>
              </select>
            </div>

            <div className="form-group mb-6">
              <label className="form-label">Примітка (необов'язково)</label>
              <textarea 
                className="form-input" 
                style={{ height: '80px', padding: '12px' }}
                value={submissionNote}
                onChange={(e) => setSubmissionNote(e.target.value)}
                placeholder="Додаткова інформація для суду..."
              />
            </div>

            <div className="flex gap-4">
              <button className="btn btn-secondary w-full" onClick={() => setSubmittingId(null)}>Скасувати</button>
              <button 
                className="btn btn-primary btn-glow w-full" 
                onClick={onFinalSubmitToECourt}
                disabled={saving || !selectedCourt}
              >
                {saving ? "Подаємо..." : "Підтвердити подачу"}
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .documents-container { padding: 0 10px; }
        .btn-glow {
          box-shadow: 0 0 20px rgba(212, 168, 67, 0.4);
          border: 1px solid rgba(212, 168, 67, 0.5);
        }
        .btn-glow:hover {
          box-shadow: 0 0 30px rgba(212, 168, 67, 0.6);
        }
        
        .glass-morphism {
          background: rgba(255, 255, 255, 0.03);
          backdrop-filter: blur(15px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 16px 24px;
          display: flex;
          gap: 16px;
          margin-bottom: 40px;
        }

        .filter-group-premium {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 12px;
          background: rgba(0, 0, 0, 0.2);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 10px;
          padding: 0 16px;
        }
        .filter-group-premium input, .filter-group-premium select {
          background: transparent;
          border: none;
          color: #fff;
          width: 100%;
          padding: 12px 0;
          font-size: 14px;
          outline: none;
        }
        
        .document-grid-premium {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 30px;
        }

        .document-card-luxury {
          background: linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 24px;
          padding: 30px;
          display: flex;
          flex-direction: column;
          gap: 20px;
          position: relative;
          transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
          overflow: hidden;
        }
        
        .document-card-luxury::before {
          content: '';
          position: absolute;
          top: -50%;
          left: -50%;
          width: 200%;
          height: 200%;
          background: radial-gradient(circle at center, rgba(212,168,67,0.05) 0%, transparent 70%);
          opacity: 0;
          transition: opacity 0.4s;
          pointer-events: none;
        }

        .document-card-luxury:hover {
          transform: translateY(-10px) scale(1.02);
          border-color: rgba(212, 168, 67, 0.3);
          box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5);
        }
        
        .document-card-luxury:hover::before {
          opacity: 1;
        }

        .card-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .luxury-badge {
          background: rgba(212, 168, 67, 0.1);
          color: var(--gold-400);
          font-size: 10px;
          font-weight: 800;
          padding: 4px 12px;
          border-radius: 20px;
          text-transform: uppercase;
          letter-spacing: 1px;
          border: 1px solid rgba(212, 168, 67, 0.2);
        }

        .doc-date-luxury {
          font-size: 12px;
          color: var(--text-muted);
          font-weight: 500;
        }

        .luxury-doc-title {
          font-size: 20px;
          font-weight: 800;
          color: #fff;
          line-height: 1.3;
          margin: 0;
        }

        .luxury-doc-preview {
          font-size: 14px;
          color: var(--text-secondary);
          line-height: 1.6;
          height: 70px;
          overflow: hidden;
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          margin: 0;
        }

        .luxury-card-actions {
          margin-top: auto;
          display: flex;
          flex-direction: column;
          gap: 16px;
          padding-top: 20px;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
        }

        .action-main-buttons {
          display: flex;
          gap: 10px;
        }

        .btn-lux {
          flex: 1;
          padding: 10px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.3s;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .btn-lux-docx {
          background: rgba(59, 130, 246, 0.1);
          color: #60a5fa;
          border: 1px solid rgba(59, 130, 246, 0.2);
        }
        .btn-lux-docx:hover { background: rgba(59, 130, 246, 0.2); border-color: #60a5fa; }

        .btn-lux-pdf {
          background: rgba(239, 68, 68, 0.1);
          color: #f87171;
          border: 1px solid rgba(239, 68, 68, 0.2);
        }
        .btn-lux-pdf:hover { background: rgba(239, 68, 68, 0.2); border-color: #f87171; }

        .action-utility-buttons {
          display: flex;
          gap: 20px;
          justify-content: center;
        }

        .btn-icon-link {
          background: none;
          border: none;
          color: var(--text-secondary);
          cursor: pointer;
          font-size: 18px;
          transition: color 0.2s;
        }
        .btn-icon-link:hover { color: #fff; }
        .btn-icon-link.danger:hover { color: #ef4444; }

        .ai-tag {
          position: absolute;
          bottom: 15px;
          right: 30px;
          font-size: 9px;
          background: rgba(255, 255, 255, 0.05);
          padding: 2px 8px;
          border-radius: 4px;
          color: var(--text-muted);
          font-weight: 600;
        }

        .loading-state-premium {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 100px 0;
          color: var(--text-muted);
        }

        .premium-spinner {
          width: 50px; height: 50px;
          border: 2px solid transparent;
          border-top: 2px solid var(--gold-500);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 20px;
          box-shadow: 0 -4px 10px rgba(212, 168, 67, 0.2);
        }

        .pagination-luxury {
          margin-top: 60px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 30px;
        }
        .pagination-luxury button {
          background: none;
          border: none;
          color: var(--gold-400);
          font-weight: 700;
          cursor: pointer;
          opacity: 0.7;
        }
        .pagination-luxury button:disabled { opacity: 0.2; cursor: not-allowed; }
        
        .page-dots { display: flex; gap: 10px; }
        .page-dot {
          width: 8px; height: 8px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          cursor: pointer;
          transition: all 0.3s;
        }
        .page-dot.active {
          background: var(--gold-500);
          transform: scale(1.5);
          box-shadow: 0 0 10px var(--gold-500);
        }

        .modal-overlay-blur {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.85);
          backdrop-filter: blur(12px);
          display: flex; align-items: center; justify-content: center;
          z-index: 2000;
        }
        
        .modal-content-luxury {
          width: 95%; max-width: 900px;
          padding: 40px;
          background: #0b1628;
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 32px;
        }

        .luxury-textarea {
          width: 100%; height: 500px;
          background: rgba(0, 0, 0, 0.3);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 24px;
          color: rgba(255, 255, 255, 0.9);
          font-family: 'Inter', sans-serif;
          font-size: 15px;
          line-height: 1.6;
          margin: 24px 0;
          resize: none;
        }
      `}</style>
    </div>
  );
}
