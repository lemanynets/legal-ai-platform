"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  getKnowledgeEntries, 
  createKnowledgeEntry, 
  deleteKnowledgeEntry,
  type KnowledgeEntry 
} from "@/lib/api";
import { getToken, getUserId } from "@/lib/auth";

export default function KnowledgeBasePage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEntry, setNewEntry] = useState({ title: "", content: "", category: "Шаблон", tags: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadEntries();
  }, [category]);

  async function loadEntries() {
    setLoading(true);
    try {
      const data = await getKnowledgeEntries({ category: category || undefined }, getToken(), getUserId());
      setEntries(data);
    } catch (err) {
      setError("Не вдалося завантажити базу знань.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAddEntry(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await createKnowledgeEntry({
        ...newEntry,
        tags: newEntry.tags.split(",").map(t => t.trim()).filter(Boolean)
      }, getToken(), getUserId());
      setNewEntry({ title: "", content: "", category: "Шаблон", tags: "" });
      setShowAddForm(false);
      await loadEntries();
    } catch (err) {
      setError("Не вдалося зберегти запис.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Ви впевнені, що хочете видалити цей зразок?")) return;
    try {
      await deleteKnowledgeEntry(id, getToken(), getUserId());
      await loadEntries();
    } catch (err) {
      setError("Не вдалося видалити запис.");
    }
  }

  return (
    <div className="animate-fade-in knowledge-base-v2">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-black white mb-2">Бібліотека прецедентів</h1>
          <p className="text-sm text-muted">Ваша приватна база "золотих стандартів" та успішних зразків документів.</p>
        </div>
        <button 
          onClick={() => setShowAddForm(true)}
          className="btn btn-gold btn-elevated"
        >
          + Додати зразок
        </button>
      </div>

      <div className="filter-bar card-elevated mb-8">
        <div className="flex gap-4">
          {["", "Шаблон", "Позовна заява", "Договір", "Клопотання", "Рішення"].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`filter-pill ${category === cat ? "active" : ""}`}
            >
              {cat || "Всі категорії"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Завантаження бібліотеки...</div>
      ) : (
        <div className="grid-3">
          {entries.map((entry) => (
            <div key={entry.id} className="kb-card card-elevated card-hover">
              <div className="flex justify-between items-start mb-4">
                <span className="badge badge-gold-outline">{entry.category || "Загальне"}</span>
                <button onClick={() => handleDelete(entry.id)} className="delete-btn-mini">×</button>
              </div>
              <h3 className="kb-title">{entry.title}</h3>
              <p className="kb-preview">{entry.content.substring(0, 150)}...</p>
              <div className="kb-footer">
                <div className="tags-row">
                  {entry.tags.map(tag => (
                    <span key={tag} className="tag-pill">#{tag}</span>
                  ))}
                </div>
                <div className="kb-date">{new Date(entry.created_at).toLocaleDateString("uk-UA")}</div>
              </div>
            </div>
          ))}
          {entries.length === 0 && (
            <div className="empty-kb">
              <div className="empty-icon-kb">📚</div>
              <p>Ваша бібліотека поки що порожня.</p>
              <button onClick={() => setShowAddForm(true)} className="text-link-premium mt-4">Додати перший прецедент →</button>
            </div>
          )}
        </div>
      )}

      {/* Add Modal */}
      {showAddForm && (
        <div className="modal-overlay">
          <div className="modal-content card-elevated animate-slide-up" style={{ maxWidth: "600px" }}>
            <h2 className="text-xl font-bold white mb-6">Новий прецедент у базу</h2>
            <form onSubmit={handleAddEntry} className="flex flex-col gap-4">
              <div className="input-group">
                <label>Назва зразка</label>
                <input 
                  required 
                  value={newEntry.title} 
                  onChange={e => setNewEntry({...newEntry, title: e.target.value})}
                  placeholder="Наприклад: Позовна заява про стягнення боргу (ідеальна)"
                />
              </div>
              <div className="grid-2">
                <div className="input-group">
                  <label>Категорія</label>
                  <select value={newEntry.category} onChange={e => setNewEntry({...newEntry, category: e.target.value})}>
                    <option>Шаблон</option>
                    <option>Позовна заява</option>
                    <option>Договір</option>
                    <option>Клопотання</option>
                    <option>Рішення</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Теги (через кому)</label>
                  <input 
                    value={newEntry.tags} 
                    onChange={e => setNewEntry({...newEntry, tags: e.target.value})}
                    placeholder="цивільне, дпп, борг"
                  />
                </div>
              </div>
              <div className="input-group">
                <label>Текст документу</label>
                <textarea 
                  required 
                  rows={8}
                  value={newEntry.content} 
                  onChange={e => setNewEntry({...newEntry, content: e.target.value})}
                  placeholder="Вставте сюди текст позову або ключові тези..."
                />
              </div>
              <div className="flex gap-4 mt-4">
                <button type="button" onClick={() => setShowAddForm(false)} className="btn btn-secondary flex-grow">Скасувати</button>
                <button type="submit" disabled={saving} className="btn btn-gold flex-grow">
                  {saving ? "Збереження..." : "Зберегти в бібліотеку"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .knowledge-base-v2 { max-width: 1200px; margin: 0 auto; padding-bottom: 60px; }
        .filter-pill { padding: 8px 20px; border-radius: 30px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); color: #94a3b8; font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.2s; }
        .filter-pill:hover { background: rgba(255,255,255,0.06); color: #fff; }
        .filter-pill.active { background: var(--gold-500); color: #000; border-color: var(--gold-400); box-shadow: 0 4px 15px rgba(212,168,67,0.3); }
        
        .kb-card { padding: 28px; border-radius: 24px; display: flex; flex-direction: column; background: rgba(15,23,42,0.3); border: 1px solid rgba(255,255,255,0.03); min-height: 280px; }
        .kb-title { font-size: 18px; font-weight: 800; color: #f1f5f9; margin-bottom: 12px; line-height: 1.3; }
        .kb-preview { font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; flex-grow: 1; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
        
        .tag-pill { font-size: 10px; color: var(--gold-400); font-weight: 700; background: rgba(212,168,67,0.1); padding: 2px 8px; border-radius: 4px; margin-right: 6px; }
        .kb-date { font-size: 11px; color: #475569; font-weight: 600; margin-top: 12px; }
        
        .empty-kb { grid-column: 1 / -1; text-align: center; padding: 100px 0; }
        .empty-icon-kb { font-size: 64px; opacity: 0.1; margin-bottom: 20px; }
        
        .delete-btn-mini { background: none; border: none; color: #475569; font-size: 20px; cursor: pointer; line-height: 1; transition: color 0.2s; }
        .delete-btn-mini:hover { color: #ef4444; }
        
        .badge-gold-outline { font-size: 10px; padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(212,168,67,0.3); color: var(--gold-400); font-weight: 800; text-transform: uppercase; }
        
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); z-index: 1000; display: flex; items-center: center; justify-content: center; padding: 20px; }
        .modal-content { width: 100%; padding: 40px; border-radius: 32px; background: #0f172a; border: 1px solid rgba(255,255,255,0.05); }
        
        .input-group label { display: block; font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px; }
        .input-group input, .input-group select, .input-group textarea { width: 100%; padding: 12px 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; color: #fff; outline: none; font-size: 14px; }
        .input-group input:focus, .input-group textarea:focus { border-color: var(--gold-500); background: rgba(255,255,255,0.06); }
      `}</style>
    </div>
  );
}
