export const themeCSS = `
:root {
  --navy-950: #040811;
  --navy-900: #070e1b;
  --navy-800: #0b162a;
  --navy-700: #102142;
  --navy-600: #1a3466;
  --navy-500: #254a8e;
  --gold-500: #c19b3a;
  --gold-400: #d4a843;
  --gold-300: #e8bf60;
  --accent: #3b82f6;
  --accent-glow: rgba(59, 130, 246, 0.4);
  --gold-glow: rgba(212, 168, 67, 0.3);
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #64748b;
  --surface: rgba(255, 255, 255, 0.03);
  --surface-glass: rgba(15, 23, 42, 0.6);
  --surface-hover: rgba(255, 255, 255, 0.06);
  --border: rgba(255, 255, 255, 0.06);
  --border-strong: rgba(255, 255, 255, 0.12);
  --sidebar-w: 260px;
  --topbar-h: 72px;
  --radius: 16px;
  --radius-sm: 10px;
  --radius-lg: 24px;
  --shadow: 0 10px 40px -10px rgba(0,0,0,0.5);
  --shadow-gold: 0 0 20px var(--gold-glow);
  --transition: 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
a { color: inherit; text-decoration: none; }
html { scroll-behavior: smooth; }
body {
  background: var(--navy-950);
  background: radial-gradient(circle at 50% 0%, #0b1a30 0%, #060d1a 100%);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

.app-shell { display: flex; min-height: 100vh; }
.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: var(--sidebar-w); 
  background: var(--navy-900);
  border-right: 1px solid var(--border); display: flex;
  flex-direction: column; z-index: 100;
}
.sidebar-logo { 
  display: flex; align-items: center; gap: 14px; padding: 24px 20px; 
  background: linear-gradient(to bottom, rgba(212, 168, 67, 0.05), transparent);
}
.sidebar-logo-icon {
  width: 42px; height: 42px;
  background: linear-gradient(135deg, var(--gold-500), var(--gold-300));
  border-radius: 14px; display: flex; align-items: center; justify-content: center;
  font-size: 22px; box-shadow: 0 4px 20px rgba(212,168,67,0.4);
  color: var(--navy-950);
  position: relative;
}
.sidebar-logo-icon::after {
  content: ''; position: absolute; inset: -2px; 
  border-radius: 16px; border: 1px solid rgba(212, 168, 67, 0.3);
  opacity: 0.5;
}
.sidebar-logo-text { font-size: 18px; font-weight: 900; color: #fff; letter-spacing: -0.03em; }
.sidebar-logo-sub { font-size: 10px; color: var(--gold-400); font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; margin-top: -2px; }
.sidebar-nav { flex: 1; overflow-y: auto; padding: 24px 0; }
.nav-section-label { font-size: 11px; font-weight: 800; text-transform: uppercase; color: var(--text-muted); padding: 16px 28px 10px; letter-spacing: 0.1em; opacity: 0.7; }
.nav-link { display: flex; align-items: center; gap: 12px; padding: 12px 28px; font-size: 14px; color: var(--text-secondary); transition: all var(--transition); text-decoration: none; position: relative; }
.nav-link:hover { color: #fff; background: rgba(255,255,255,0.03); }
.nav-link.active { 
  color: #fff; 
  background: linear-gradient(90deg, rgba(212,168,67,0.08), transparent); 
}
.nav-link.active::before {
  content: ''; position: absolute; left: 0; top: 20%; bottom: 20%; width: 3px; 
  background: var(--gold-500); border-radius: 0 4px 4px 0;
  box-shadow: 4px 0 15px var(--gold-glow);
}
.nav-link-icon { font-size: 18px; width: 24px; opacity: 0.6; transition: inherit; }
.nav-link:hover .nav-link-icon, .nav-link.active .nav-link-icon { opacity: 1; transform: scale(1.1); }
.nav-badge { margin-left: auto; background: var(--gold-500); color: var(--navy-950); font-size: 10px; font-weight: 900; padding: 2px 8px; border-radius: 100px; box-shadow: 0 4px 12px var(--gold-glow); }

.sidebar-footer { padding: 24px; border-top: 1px solid var(--border); }
.sidebar-user { 
  display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: var(--radius); 
  background: rgba(255,255,255,0.02); border: 1px solid var(--border);
  cursor: pointer; transition: all var(--transition); 
}
.sidebar-user:hover { 
  background: rgba(255,255,255,0.05); transform: translateY(-2px);
  border-color: var(--border-strong);
}
.sidebar-avatar { 
  width: 40px; height: 40px; border-radius: 12px; 
  background: linear-gradient(135deg, var(--gold-500), var(--gold-300)); 
  display: flex; align-items: center; justify-content: center; 
  font-size: 15px; font-weight: 800; color: var(--navy-950); 
  box-shadow: 0 6px 15px rgba(212,168,67,0.3); 
}
.sidebar-user-name { font-size: 14px; font-weight: 700; color: #fff; }
.sidebar-user-plan { font-size: 11px; color: var(--gold-400); font-weight: 600; }

.main-content { margin-left: var(--sidebar-w); min-height: 100vh; display: flex; flex-direction: column; flex: 1; background: var(--navy-950); position: relative; }
.main-content::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 400px;
  background: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 70%);
  pointer-events: none;
}
.page-content { padding: 48px; position: relative; z-index: 1; }

.section-header { margin-bottom: 48px; display: flex; justify-content: space-between; align-items: flex-start; }
.section-title { font-size: 36px; font-weight: 900; color: #fff; letter-spacing: -0.04em; margin-bottom: 8px; }
.section-subtitle { font-size: 16px; color: var(--text-secondary); opacity: 0.8; }

.card-elevated { 
  background: var(--surface-glass); 
  backdrop-filter: blur(12px);
  border: 1px solid var(--border); 
  border-radius: var(--radius); 
  box-shadow: var(--shadow);
  transition: all var(--transition);
  position: relative;
  overflow: hidden;
}
.card-elevated:hover { transform: translateY(-4px); border-color: var(--border-strong); box-shadow: 0 20px 50px -12px rgba(0,0,0,0.6); }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 14px 28px; font-size: 15px; font-weight: 800; border: none; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); text-decoration: none; position: relative; overflow: hidden; }
.btn-primary { 
  background: linear-gradient(135deg, var(--gold-500), var(--gold-300)); 
  color: var(--navy-950); 
  box-shadow: 0 8px 24px rgba(212,168,67,0.3); 
}
.btn-primary:active { transform: scale(0.96); }
.btn-primary::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(to right, transparent, rgba(255,255,255,0.2), transparent);
  transform: translateX(-100%); transition: 0.6s;
}
.btn-primary:hover::after { transform: translateX(100%); }
.btn-primary:hover { transform: scale(1.02); box-shadow: 0 6px 20px rgba(212,168,67,0.4); }
.btn-secondary { background: rgba(255,255,255,0.05); color: #fff; border: 1px solid var(--border-strong); }
.btn-secondary:hover { background: rgba(255,255,255,0.1); border-color: #fff; }

.badge { padding: 4px 10px; border-radius: 100px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
.badge-gold { background: rgba(212,168,67,0.1); color: var(--gold-400); border: 1px solid rgba(212,168,67,0.3); }
.badge-success { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }

/* Custom Animations */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.animate-fade-in { animation: fadeIn 0.6s ease forwards; }

@media (max-width: 1024px) {
  .sidebar { transform: translateX(-100%); transition: transform 0.3s; }
  .sidebar.open { transform: translateX(0); }
  .main-content { margin-left: 0; }
}

/* Document History Page Extra Styles */
.document-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  margin-top: 30px;
}

.document-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  overflow: hidden;
}

.doc-type-badge {
  display: inline-block;
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  background: rgba(212, 168, 67, 0.1);
  color: var(--gold-400);
}

.doc-card-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.doc-card-preview {
  font-size: 13px;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 60px;
}

.doc-card-footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.doc-date {
  font-size: 12px;
  color: var(--text-muted);
}

.filter-bar {
  display: flex;
  gap: 16px;
  padding: 20px;
  margin-top: 24px;
  align-items: center;
  backdrop-filter: blur(10px);
}

.filter-group {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0 12px;
}

.filter-group input, .filter-group select {
  background: transparent;
  border: none;
  color: #fff;
  padding: 10px 0;
  width: 100%;
  outline: none;
  font-size: 14px;
}

.filter-group select option {
  background: var(--navy-900);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

/* Utilities */
.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }

.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-grow { flex-grow: 1; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.mt-auto { margin-top: auto; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mt-8 { margin-top: 32px; }
.mt-4 { margin-top: 16px; }
.p-2 { padding: 8px; }
.mx-auto { margin-left: auto; margin-right: auto; }
.max-w-md { max-width: 448px; }

.text-xs { font-size: 12px; }
.text-sm { font-size: 14px; }
.text-lg { font-size: 18px; }
.text-xl { font-size: 20px; }
.text-2xl { font-size: 24px; }
.font-bold { font-weight: 700; }
.font-black { font-weight: 900; }
.leading-relaxed { line-height: 1.625; }
.italic { font-style: italic; }
.text-center { text-align: center; }

.text-gold { color: var(--gold-400); }
.text-secondary { color: var(--text-secondary); }
.text-muted { color: var(--text-muted); }
.hover\:underline:hover { text-decoration: underline; }
.hover\:text-gold:hover { color: var(--gold-400); }
.hover\:text-white:hover { color: #fff; }
.cursor-pointer { cursor: pointer; }

/* Forms */
.form-label { display: block; font-size: 13px; font-weight: 700; color: var(--text-secondary); margin-bottom: 8px; }
.form-input {
  width: 100%;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 16px;
  color: #fff;
  font-size: 14px;
  transition: all 0.2s;
  outline: none;
}
.form-input:focus { border-color: var(--gold-500); background: rgba(255,255,255,0.05); }

/* Modals */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.8);
  backdrop-filter: blur(8px); display: flex; align-items: center;
  justify-content: center; z-index: 1000;
  animation: fadeIn 0.3s ease;
}
.modal-content {
  padding: 40px;
  width: 100%;
  max-width: 600px;
  position: relative;
  box-shadow: 0 32px 64px rgba(0,0,0,0.5);
}
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; }

/* Global helper for spacing */
.space-y-4 > * + * { margin-top: 16px; }
.space-y-8 > * + * { margin-top: 32px; }

/* Timeline */
.timeline-container { position: relative; }
.timeline-container::before {
  content: ''; position: absolute; left: 7px; top: 0; bottom: 0;
  width: 2px; background: rgba(255,255,255,0.05);
}
.timeline-event { position: relative; padding-left: 32px; margin-bottom: 32px; }
.timeline-event:last-child { margin-bottom: 0; }
.timeline-marker {
  position: absolute; left: 0; top: 4px;
  width: 16px; height: 16px; border-radius: 50%;
  background: #0b1628; border: 3px solid #d4a843;
  z-index: 1; box-shadow: 0 0 10px rgba(212,168,67,0.3);
}
.timeline-content-inner {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 16px; padding: 20px;
  transition: all 0.2s;
}
.timeline-content-inner:hover {
  transform: translateX(4px);
  border-color: rgba(212,168,67,0.2);
  background: rgba(255,255,255,0.04);
}


`;