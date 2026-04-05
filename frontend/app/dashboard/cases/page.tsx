"use client";

import { useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import {
  createCase,
  deleteCase,
  getCase,
  getCases,
  syncCaseDecisions,
  updateCase,
  type Case,
  type CaseDetail,
} from "@/lib/services/cases.service";

type TimelineItem =
  | {
      id: string;
      type: "document";
      date: Date;
      document_type: string;
      document_category: string;
    }
  | {
      id: string;
      type: "post";
      date: Date;
      title: string;
    };

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [syncingDecisions, setSyncingDecisions] = useState(false);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  const [title, setTitle] = useState("");
  const [caseNumber, setCaseNumber] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await getCases(getToken(), getUserId());
      setCases(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleOpenCase(id: string) {
    setDetailLoading(true);
    try {
      const data = await getCase(id, getToken(), getUserId());
      setSelectedCase(data);
    } catch (err) {
      console.error(err);
      alert("Не вдалося завантажити деталі справи.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleCreate() {
    if (!title.trim()) return;
    try {
      await createCase(
        {
          title: title.trim(),
          case_number: caseNumber.trim(),
          description: description.trim(),
        },
        getToken(),
        getUserId(),
      );
      setShowCreateModal(false);
      setTitle("");
      setCaseNumber("");
      setDescription("");
      await load();
    } catch (err) {
      console.error(err);
      alert("Не вдалося створити справу.");
    }
  }

  async function handleUpdate() {
    if (!selectedCase || !title.trim()) return;
    try {
      await updateCase(
        selectedCase.id,
        {
          title: title.trim(),
          case_number: caseNumber.trim(),
          description: description.trim(),
        },
        getToken(),
        getUserId(),
      );
      setShowEditModal(false);
      await handleOpenCase(selectedCase.id);
      await load();
    } catch (err) {
      console.error(err);
      alert("Не вдалося оновити справу.");
    }
  }

  async function handleDelete(id: string) {
    const confirmed = window.confirm(
      "Видалити цю справу? Зв'язки з документами та обговореннями буде розірвано.",
    );
    if (!confirmed) return;
    try {
      await deleteCase(id, getToken(), getUserId());
      if (selectedCase?.id === id) {
        setSelectedCase(null);
      }
      await load();
    } catch (err) {
      console.error(err);
      alert("Не вдалося видалити справу.");
    }
  }

  function openEditModal() {
    if (!selectedCase) return;
    setTitle(selectedCase.title);
    setCaseNumber(selectedCase.case_number || "");
    setDescription(selectedCase.description || "");
    setShowEditModal(true);
  }

  function openCaseTool(path: string, caseId: string) {
    window.location.href = `${path}?case_id=${caseId}`;
  }

  async function handleSyncDecisions() {
    if (!selectedCase) return;
    const confirmed = window.confirm(
      "Оновити рішення для цієї справи через OpenDataBot? Це виконає один зовнішній запит.",
    );
    if (!confirmed) return;

    setSyncingDecisions(true);
    try {
      const result = await syncCaseDecisions(selectedCase.id, getToken(), getUserId());
      await handleOpenCase(selectedCase.id);
      alert(
        result.total > 0
          ? `Рішення оновлено. Додано або оновлено записів: ${result.total}.`
          : "Запит виконано, але нових рішень для імпорту не знайдено.",
      );
    } catch (err) {
      console.error(err);
      alert("Не вдалося оновити рішення для цієї справи.");
    } finally {
      setSyncingDecisions(false);
    }
  }

  if (selectedCase) {
    const timelineItems: TimelineItem[] = [
      ...selectedCase.documents.map((item) => ({
        id: item.id,
        type: "document" as const,
        date: new Date(item.created_at),
        document_type: item.document_type,
        document_category: item.document_category,
      })),
      ...selectedCase.forum_posts.map((item) => ({
        id: item.id,
        type: "post" as const,
        date: new Date(item.created_at),
        title: item.title,
      })),
    ].sort((a, b) => b.date.getTime() - a.date.getTime());

    const caseLawItems = selectedCase.case_law_items || [];

    return (
      <div className="animate-fade-in">
        <div className="section-header">
          <div className="flex items-center gap-4">
            <button
              className="btn btn-secondary p-2"
              style={{ borderRadius: "50%", width: "40px", height: "40px" }}
              onClick={() => setSelectedCase(null)}
            >
              ←
            </button>
            <div>
              <h1 className="section-title">{selectedCase.title}</h1>
              <div className="flex gap-2 items-center mt-1">
                <span className="text-xs text-muted">
                  № справи: {selectedCase.case_number || "не вказано"}
                </span>
                <span className="badge badge-success">{selectedCase.status}</span>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <button className="btn btn-secondary" onClick={openEditModal}>
              Редагувати
            </button>
            <button
              className="btn btn-secondary"
              style={{ color: "var(--status-error)" }}
              onClick={() => handleDelete(selectedCase.id)}
            >
              Видалити
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          <div className="lg:col-span-2 space-y-8">
            <div className="card-elevated" style={{ padding: "32px" }}>
              <h2 className="text-xl font-bold mb-4">Опис справи</h2>
              <p className="text-secondary leading-relaxed">
                {selectedCase.description || "Детальний опис для цієї справи поки відсутній."}
              </p>
            </div>

            <div className="card-elevated" style={{ padding: "32px" }}>
              <div className="flex items-center justify-between gap-4 mb-6">
                <div>
                  <h2 className="text-xl font-bold">Рішення з бази</h2>
                  <p className="text-sm text-secondary mt-2">
                    Локальні рішення з бази практики, підібрані за номером цієї справи.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    className="btn btn-secondary text-xs"
                    onClick={() => void handleSyncDecisions()}
                    disabled={syncingDecisions || detailLoading}
                  >
                    {syncingDecisions ? "Оновлення..." : "Оновити рішення"}
                  </button>
                  <span className="badge badge-success">{caseLawItems.length}</span>
                </div>
              </div>

              {caseLawItems.length > 0 ? (
                <div className="space-y-4">
                  {caseLawItems.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-2xl border"
                      style={{
                        borderColor: "rgba(255,255,255,0.08)",
                        background: "rgba(255,255,255,0.02)",
                        padding: "20px",
                      }}
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-bold text-gold uppercase tracking-wider">
                              {item.court_name || "Суд не вказано"}
                            </span>
                            {item.court_type ? (
                              <span className="badge badge-secondary">{item.court_type}</span>
                            ) : null}
                          </div>
                          <div className="text-sm text-muted mt-2">
                            № справи: {item.case_number || selectedCase.case_number || "н/д"}
                          </div>
                          <div className="text-sm text-muted mt-1">ID рішення: {item.decision_id}</div>
                        </div>
                        <div className="text-sm text-muted whitespace-nowrap">
                          {item.decision_date
                            ? new Date(item.decision_date).toLocaleDateString()
                            : "Дата не вказана"}
                        </div>
                      </div>

                      <p className="text-secondary leading-relaxed mt-4">
                        {item.summary || "Короткий зміст рішення поки відсутній у локальній базі."}
                      </p>

                      <div className="flex flex-wrap gap-2 mt-4">
                        <span className="badge badge-secondary">Джерело: {item.source}</span>
                        <span className="badge badge-secondary">Згадок: {item.reference_count}</span>
                        {item.subject_categories.slice(0, 3).map((tag) => (
                          <span key={`${item.id}-${tag}`} className="badge badge-secondary">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-muted italic">
                  Для цієї справи рішень у локальній базі поки не знайдено.
                </div>
              )}
            </div>

            <div className="card-elevated" style={{ padding: "32px" }}>
              <h2 className="text-xl font-bold mb-6">Хронологія подій</h2>
              <div className="timeline-container">
                {timelineItems.length > 0 ? (
                  timelineItems.map((item) => (
                    <div key={`${item.type}-${item.id}`} className="timeline-event">
                      <div className="timeline-marker"></div>
                      <div className="timeline-content-inner">
                        <div className="flex justify-between items-start gap-4">
                          <div>
                            <div className="text-xs font-bold text-gold uppercase tracking-wider mb-1">
                              {item.type === "document" ? "Документ" : "Обговорення"}
                            </div>
                            <div className="font-bold text-sm">
                              {item.type === "document" ? item.document_type : item.title}
                            </div>
                            {item.type === "document" ? (
                              <div className="text-xs text-muted mt-1">{item.document_category}</div>
                            ) : null}
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-muted">{item.date.toLocaleDateString()}</div>
                            <button
                              className="text-xs text-gold hover:underline mt-2 block"
                              onClick={() =>
                                (window.location.href =
                                  item.type === "document"
                                    ? `/dashboard/documents?id=${item.id}`
                                    : `/dashboard/forum/post/${item.id}`)
                              }
                            >
                              Відкрити →
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-muted italic">
                    Події для цієї справи ще не зафіксовані.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-8">
            <div
              className="card-elevated"
              style={{
                padding: "32px",
                background: "linear-gradient(135deg, rgba(255,215,0,0.05) 0%, rgba(0,0,0,0) 100%)",
              }}
            >
              <h2 className="text-lg font-bold mb-3">Розумний помічник</h2>
              <p className="text-xs text-secondary mb-4">
                Швидкий запуск інструментів з уже підв'язаним контекстом цієї справи.
              </p>
              <div className="grid grid-cols-1 gap-2">
                <button
                  className="btn btn-secondary text-xs justify-start"
                  onClick={() => openCaseTool("/dashboard/decision-analysis", selectedCase.id)}
                >
                  Аналіз судового рішення
                </button>
                <button
                  className="btn btn-secondary text-xs justify-start"
                  onClick={() => openCaseTool("/dashboard/full-lawyer", selectedCase.id)}
                >
                  Full Lawyer Analysis
                </button>
                <button
                  className="btn btn-secondary text-xs justify-start"
                  onClick={() => openCaseTool("/dashboard/generate", selectedCase.id)}
                >
                  Новий документ
                </button>
                <button
                  className="btn btn-secondary text-xs justify-start"
                  onClick={() => openCaseTool("/dashboard/forum", selectedCase.id)}
                >
                  Нове питання
                </button>
              </div>
            </div>

            <div className="card-elevated" style={{ padding: "32px" }}>
              <h2 className="text-lg font-bold mb-4">Статистика справи</h2>
              <div className="space-y-4">
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Документів:</span>
                  <span className="font-bold">{selectedCase.documents.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Обговорень:</span>
                  <span className="font-bold">{selectedCase.forum_posts.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Рішень з бази:</span>
                  <span className="font-bold">{caseLawItems.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Створено:</span>
                  <span className="font-bold">{new Date(selectedCase.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {showEditModal ? (
          <div className="modal-overlay">
            <div className="modal-content card-elevated" style={{ maxWidth: "500px", width: "90%" }}>
              <h2>Редагувати справу</h2>
              <div className="mt-6">
                <label className="form-label">Назва справи</label>
                <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div className="mt-4">
                <label className="form-label">Номер справи</label>
                <input className="form-input" value={caseNumber} onChange={(e) => setCaseNumber(e.target.value)} />
              </div>
              <div className="mt-4">
                <label className="form-label">Опис</label>
                <textarea
                  className="form-input"
                  style={{ height: "100px" }}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="modal-actions mt-8">
                <button className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                  Скасувати
                </button>
                <button className="btn btn-primary" onClick={handleUpdate}>
                  Зберегти зміни
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="animate-fade-in text-white">
      <div className="section-header">
        <div>
          <h1 className="section-title">Мої справи</h1>
          <p className="section-subtitle">
            Керуй робочими картками справ, документами, обговореннями та судовою практикою в одному місці.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          + Нова справа
        </button>
      </div>

      {detailLoading ? (
        <div className="card-elevated mt-8" style={{ padding: "32px" }}>
          Завантажуємо деталі справи...
        </div>
      ) : null}

      <div className="grid-3 mt-8">
        {cases.map((item) => (
          <div
            key={item.id}
            className="card-elevated card-hover flex flex-col"
            style={{ padding: "32px", border: "1px solid rgba(255,255,255,0.05)" }}
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 800 }}>{item.title}</h3>
                <div className="text-xs text-muted mt-1">{item.case_number || "Без номера справи"}</div>
              </div>
              <span className="badge badge-success">{item.status}</span>
            </div>

            <p className="text-sm text-secondary mb-6 flex-grow" style={{ minHeight: "60px" }}>
              {item.description || "Опис поки не додано."}
            </p>

            <div className="flex justify-between items-center mt-auto">
              <span className="text-xs text-muted">
                Створено: {new Date(item.created_at).toLocaleDateString()}
              </span>
              <div className="flex gap-4">
                <button className="text-xs text-secondary hover:text-white" onClick={() => handleDelete(item.id)}>
                  Видалити
                </button>
                <button className="text-xs text-gold font-bold hover:underline" onClick={() => void handleOpenCase(item.id)}>
                  Деталі →
                </button>
              </div>
            </div>
          </div>
        ))}

        {cases.length === 0 && !loading ? (
          <div className="card-elevated" style={{ gridColumn: "1 / -1", padding: "80px", textAlign: "center" }}>
            <div style={{ fontSize: "60px", marginBottom: "24px" }}>Справ ще немає</div>
            <h2 className="text-2xl font-black">Почнемо з першої картки справи</h2>
            <p className="text-muted mt-2 max-w-md mx-auto">
              Тут будуть збиратися документи, строки, обговорення та практика по кожній справі.
            </p>
            <button className="btn btn-primary mt-8" onClick={() => setShowCreateModal(true)}>
              Створити першу справу
            </button>
          </div>
        ) : null}
      </div>

      {showCreateModal ? (
        <div className="modal-overlay">
          <div className="modal-content card-elevated" style={{ maxWidth: "500px", width: "90%" }}>
            <h2>Нова судова справа</h2>
            <div className="mt-6">
              <label className="form-label">Назва справи</label>
              <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="mt-4">
              <label className="form-label">Номер справи</label>
              <input className="form-input" value={caseNumber} onChange={(e) => setCaseNumber(e.target.value)} />
            </div>
            <div className="mt-4">
              <label className="form-label">Короткий опис</label>
              <textarea
                className="form-input"
                style={{ height: "100px" }}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="modal-actions mt-8">
              <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                Скасувати
              </button>
              <button className="btn btn-primary" onClick={handleCreate}>
                Створити справу
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
