"use client";

import { useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import { 
  getForumPosts, 
  createForumPost, 
  getForumPostDetail, 
  createForumComment,
  getCases,
  type ForumPost,
  type ForumComment,
  type Case
} from "@/lib/api";

export default function ForumPage() {
  const [posts, setPosts] = useState<ForumPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [viewingPost, setViewingPost] = useState<string | null>(null);
  const [postDetail, setPostDetail] = useState<any>(null);
  
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [commentContent, setCommentContent] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [filterCaseId, setFilterCaseId] = useState("");

  useEffect(() => {
    void loadPosts();
    void loadCases();
  }, []);

  useEffect(() => {
    void loadPosts();
  }, [filterCaseId]);

  async function loadCases() {
    try {
      const data = await getCases(getToken(), getUserId());
      setCases(data);
    } catch (err) { console.error(err); }
  }

  async function loadPosts() {
    setLoading(true);
    try {
      const data = await getForumPosts({ case_id: filterCaseId || undefined }, getToken(), getUserId());
      setPosts(data);
    } catch (err) {
      setError("Не вдалося завантажити форум.");
    } finally {
      setLoading(false);
    }
  }

  async function loadPostDetail(id: string) {
    try {
      const data = await getForumPostDetail(id, getToken(), getUserId());
      setPostDetail(data);
    } catch (err) {
      setError("Не вдалося завантажити пост.");
    }
  }

  async function handleCreatePost(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createForumPost({ 
        title: newTitle, 
        content: newContent, 
        case_id: selectedCaseId || undefined 
      }, getToken(), getUserId());
      setNewTitle("");
      setNewContent("");
      setSelectedCaseId("");
      setShowCreate(false);
      await loadPosts();
    } catch (err) {
      setError("Помилка при створенні посту.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAddComment(e: React.FormEvent) {
    e.preventDefault();
    if (!viewingPost || !commentContent.trim()) return;
    setSubmitting(true);
    try {
      await createForumComment(viewingPost, { content: commentContent }, getToken(), getUserId());
      setCommentContent("");
      await loadPostDetail(viewingPost);
      await loadPosts(); // Refresh comment count
    } catch (err) {
      setError("Помилка при коментуванні.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="forum-container animate-fade-in">
      <div className="section-header">
        <div>
          <h1 className="section-title">Форум юристів</h1>
          <p className="section-subtitle">Обмінюйтеся досвідом та обговорюйте складні справи з колегами</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select 
            className="form-select" 
            style={{ width: '220px', background: 'rgba(255,255,255,0.05)', fontSize: '13px' }}
            value={filterCaseId}
            onChange={e => setFilterCaseId(e.target.value)}
          >
            <option value="">Всі обговорення</option>
            {cases.map(c => (
              <option key={c.id} value={c.id}>📁 {c.title}</option>
            ))}
          </select>
          {!viewingPost && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              + Нове обговорення
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 24 }}>{error}</div>}

      <div className="forum-layout">
        {viewingPost && postDetail ? (
          <div className="post-view card-elevated animate-slide-up">
            <button className="btn-back" onClick={() => setViewingPost(null)}>← Назад до списку</button>
            <div className="post-header">
              <h2>{postDetail.title}</h2>
              <div className="post-meta">
                <span>👤 {postDetail.user_name}</span>
                <span>📅 {new Date(postDetail.created_at).toLocaleString('uk-UA')}</span>
              </div>
            </div>
            <div className="post-content">
              {postDetail.content}
            </div>
            
            <div className="comments-section">
              <h3>Коментарі ({postDetail.comments.length})</h3>
              <div className="comments-list">
                {postDetail.comments.map((c: any) => (
                  <div key={c.id} className="comment-item">
                    <div className="comment-meta">
                      <strong>{c.user_name}</strong> · {new Date(c.created_at).toLocaleString('uk-UA')}
                    </div>
                    <div className="comment-body">{c.content}</div>
                  </div>
                ))}
              </div>
              
              <form onSubmit={handleAddComment} className="comment-form">
                <textarea 
                  placeholder="Напишіть свою думку..." 
                  value={commentContent}
                  onChange={e => setCommentContent(e.target.value)}
                  required
                />
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Надсилання..." : "Відповісти"}
                </button>
              </form>
            </div>
          </div>
        ) : (
          <div className="posts-list">
            {loading ? (
              <div className="loading-state">Завантаження...</div>
            ) : posts.length === 0 ? (
              <div className="empty-state">Поки немає обговорень. Станьте першим!</div>
            ) : (
              posts.map(p => (
                <div key={p.id} className="post-card card-elevated card-hover" onClick={() => { setViewingPost(p.id); loadPostDetail(p.id); }}>
                  <h3 className="post-card-title">{p.title}</h3>
                  <div className="post-card-preview">{p.content.substring(0, 150)}...</div>
                  <div className="post-card-footer">
                    <span>👤 {p.user_name}</span>
                    <span>💬 {p.comment_count} коментарів</span>
                    <span>📅 {new Date(p.created_at).toLocaleDateString('uk-UA')}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {showCreate && (
        <div className="modal-overlay">
          <div className="modal-content card-elevated">
            <h2>Нове обговорення</h2>
            <form onSubmit={handleCreatePost}>
              <div className="form-group">
                <label className="form-label">Заголовок</label>
                <input className="form-input" value={newTitle} onChange={e => setNewTitle(e.target.value)} required />
              </div>
              <div className="form-group">
                <label className="form-label">Повідомлення</label>
                <textarea 
                  className="forum-textarea" 
                  value={newContent} 
                  onChange={e => setNewContent(e.target.value)} 
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Прив'язати до справи (опціонально)</label>
                <select 
                  className="form-select" 
                  value={selectedCaseId} 
                  onChange={e => setSelectedCaseId(e.target.value)}
                >
                  <option value="">Без прив'язки</option>
                  {cases.map(c => (
                    <option key={c.id} value={c.id}>{c.title} ({c.case_number || "No #" })</option>
                  ))}
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Скасувати</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? "Створення..." : "Опублікувати"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .forum-container { max-width: 1000px; margin: 0 auto; }
        .post-card { padding: 24px; margin-bottom: 20px; cursor: pointer; transition: transform 0.2s; }
        .post-card-title { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 12px; }
        .post-card-preview { color: var(--text-secondary); font-size: 14px; margin-bottom: 16px; line-height: 1.5; }
        .post-card-footer { display: flex; gap: 20px; font-size: 12px; color: var(--text-muted); }
        
        .btn-back { background: none; border: none; color: var(--gold-500); cursor: pointer; margin-bottom: 20px; font-weight: 600; }
        .post-header h2 { font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 8px; }
        .post-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); margin-bottom: 32px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }
        .post-content { font-size: 16px; line-height: 1.6; color: rgba(255,255,255,0.9); margin-bottom: 48px; white-space: pre-wrap; }
        
        .comments-section h3 { font-size: 18px; font-weight: 700; margin-bottom: 24px; }
        .comment-item { padding: 16px; background: rgba(255,255,255,0.02); border-radius: 12px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.05); }
        .comment-meta { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }
        .comment-body { font-size: 14px; color: #fff; line-height: 1.5; }
        
        .comment-form { margin-top: 32px; display: flex; flex-direction: column; gap: 16px; }
        .comment-form textarea { background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; color: #fff; height: 100px; resize: none; }
        
        .forum-textarea { width: 100%; height: 250px; background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; color: #fff; resize: none; margin-top: 8px; }
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .modal-content { width: 90%; max-width: 600px; padding: 32px; background: var(--navy-900); }
      `}</style>
    </div>
  );
}
