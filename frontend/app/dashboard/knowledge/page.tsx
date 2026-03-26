"use client";

import { useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import { getKnowledgeEntries, createKnowledgeEntry, deleteKnowledgeEntry, type KnowledgeEntry } from "@/lib/api";

export default function KnowledgeBasePage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("Pleading");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await getKnowledgeEntries(undefined, getToken(), getUserId());
      setEntries(data);
    } catch (err) { setError(String(err)); }
    finally { setLoading(false); }
  }

  async function handleAdd() {
    if (!newTitle || !newContent) return;
    try {
      await createKnowledgeEntry({ title: newTitle, content: newContent, category: newCategory }, getToken(), getUserId());
      setShowModal(false);
      setNewTitle(""); setNewContent("");
      load();
    } catch (err) { setError(String(err)); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Видалити цей прецедент?")) return;
    try {
      await deleteKnowledgeEntry(id, getToken(), getUserId());
      load();
    } catch (err) { setError(String(err)); }
  }

  return (
    <div className="animate-fade-in">
      <div className="section-header">
        <div>
          <h1 className="section-title">База знань & Прецеденти</h1>
          <p className="section-subtitle">Зберігайте ваші найкращі зразки та "золоті стандарти" для навчання AI.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ Додати прецедент</button>
      </div>

      {loading ? <div className="spinner" /> : (
        <div className="grid-3">
          {entries.map(e => (
            <div key={e.id} className="card-elevated card-hover" style={{ padding: "24px" }}>
              <div className="badge badge-gold mb-3">{e.category}</div>
              <h3 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>{e.title}</h3>
              <p style={{ 
                fontSize: "13px", color: "var(--text-secondary)", 
                display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" 
              }}>
                {e.content}
              </p>
              <div className="flex justify-between items-center mt-6">
                <span className="text-xs text-muted">{new Date(e.created_at).toLocaleDateString()}</span>
                <button className="text-xs text-danger hover:underline" onClick={() => handleDelete(e.id)}>Видалити</button>
              </div>
            </div>
          ))}

          {entries.length === 0 && (
            <div className="card-elevated" style={{ gridColumn: "1 / -1", padding: "60px", textAlign: "center" }}>
               <div style={{ fontSize: "40px", marginBottom: "16px" }}>📚</div>
               <h3 className="text-xl font-bold">Ваша база поки порожня</h3>
               <p className="text-muted mt-2">Додайте перші зразки документів, щоб AI міг використовувати їх як референс.</p>
            </div>
          )}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content card-elevated" style={{ maxWidth: "600px", width: "90%" }}>
            <h2>Новий прецедент</h2>
            <div className="mt-4">
              <label className="form-label">Назва (напр. "Заперечення на позов про стягнення боргу")</label>
              <input className="form-input" value={newTitle} onChange={e => setNewTitle(e.target.value)} />
            </div>
            <div className="mt-4">
              <label className="form-label">Категорія</label>
              <select className="form-input" value={newCategory} onChange={e => setNewCategory(e.target.value)}>
                <option value="Pleading">Процесуальний документ</option>
                <option value="Contract">Контракт / Угода</option>
                <option value="Research">Правовий висновок</option>
              </select>
            </div>
            <div className="mt-4">
              <label className="form-label">Текст "Золотого стандарту"</label>
              <textarea className="form-input" style={{ height: "200px" }} value={newContent} onChange={e => setNewContent(e.target.value)} />
            </div>
            <div className="modal-actions mt-6">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Скасувати</button>
              <button className="btn btn-primary" onClick={handleAdd}>Зберегти в базу</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
