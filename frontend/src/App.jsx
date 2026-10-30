import { useState } from 'react';
import Sidebar from './components/Sidebar';
import TranscriptForm from './components/TranscriptForm';
import Dashboard from './components/Dashboard';
import History from './components/History';
import Icon from './components/Icon';
import { post, request } from './lib/api';
import './App.css';

export default function App() {
  const [expanded, setExpanded] = useState(false);
  const [view, setView] = useState('entrada');
  const [draft, setDraft] = useState('');
  const [active, setActive] = useState(null);
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [meetings, setMeetings] = useState([]);
  const [search, setSearch] = useState('');
  const [historyBusy, setHistoryBusy] = useState(false);
  const [historyError, setHistoryError] = useState('');

  async function analyze() {
    const transcript = draft.trim();
    if (!transcript || busy) return;
    setBusy(true); setError('');
    try {
      const analysis = await post('/api/analisar', { transcricao: transcript });
      setActive({ analysis, transcript, key: `${analysis.analysis_id}-${Date.now()}`, savedId: null });
      setTitle(`Reunião · ${analysis.EMPRESA}`);
      setView('dashboard');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function save() {
    if (!active || saving || active.savedId) return;
    const current = active;
    setSaving(true); setError('');
    try {
      const meeting = await post('/api/reunioes', { titulo: title, transcricao: current.transcript, analise: current.analysis });
      setActive(previous => previous?.key === current.key ? { ...previous, savedId: meeting.id } : previous);
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  }

  async function loadMeetings(term = search) {
    setHistoryBusy(true); setHistoryError('');
    try {
      const data = await request(`/api/reunioes?${new URLSearchParams({ busca: term })}`);
      setMeetings(data.reunioes || []);
    } catch (err) { setHistoryError(err.message); }
    finally { setHistoryBusy(false); }
  }

  async function openMeeting(id) {
    setHistoryBusy(true); setHistoryError('');
    try {
      const meeting = await request(`/api/reunioes/${id}`);
      setActive({ analysis: meeting.analise, transcript: meeting.transcricao, key: `meeting-${meeting.id}-${Date.now()}`, savedId: meeting.id, date: meeting.data_reuniao });
      setDraft(meeting.transcricao); setTitle(meeting.titulo); setError(''); setView('dashboard');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) { setHistoryError(err.message); }
    finally { setHistoryBusy(false); }
  }

  function navigate(next) {
    if (['dashboard', 'assistente'].includes(next) && !active) return;
    setView(next); setError('');
    if (next === 'historico') loadMeetings();
    if (next === 'assistente') requestAnimationFrame(() => document.getElementById('meeting-assistant')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    else window.scrollTo({ top: 0, behavior: 'smooth' });
    if (window.innerWidth < 800) setExpanded(false);
  }

  function newMeeting() {
    setDraft(''); setActive(null); setTitle(''); setError(''); setView('entrada');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  const names = { entrada: 'Nova reunião', dashboard: 'Dashboard', historico: 'Histórico', assistente: 'Assistente' };
  return <div className={`app-shell ${expanded ? 'menu-expanded' : ''}`}>
    <Sidebar expanded={expanded} toggle={() => setExpanded(!expanded)} view={view} navigate={navigate} hasAnalysis={!!active} />
    <div className="workspace"><header className="topbar"><div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={13} /><strong>{names[view]}</strong></div><div className="topbar-actions"><span className="workspace-status"><span className="online-dot" />Inteligência de conversas</span><button className="button button-primary button-small" onClick={newMeeting} disabled={busy}><Icon name="plus" size={15} /><span>Nova reunião</span></button><div className="top-avatar">C</div></div></header>
      <main className="main-content">
        {view === 'entrada' && <TranscriptForm draft={draft} setDraft={setDraft} analyze={analyze} busy={busy} error={error} setError={setError} />}
        {['dashboard', 'assistente'].includes(view) && active && <Dashboard active={active} title={title} setTitle={setTitle} save={save} saving={saving} edit={() => { setDraft(active.transcript); setView('entrada'); }} error={error} />}
        {view === 'historico' && <History meetings={meetings} search={search} setSearch={setSearch} refresh={() => loadMeetings()} open={openMeeting} busy={historyBusy} error={historyError} newMeeting={newMeeting} />}
      </main><footer className="workspace-footer"><span>COMPILER-AI</span><span>Contexto para conversas melhores.</span></footer>
    </div>
  </div>;
}
