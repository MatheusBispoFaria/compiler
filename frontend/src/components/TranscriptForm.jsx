import { useRef } from 'react';
import Icon from './Icon';
import { cleanSubtitle, EXAMPLE } from '../lib/analysis';

export default function TranscriptForm({ draft, setDraft, analyze, busy, error, setError }) {
  const fileRef = useRef(null);
  async function importFile(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!/\.(txt|vtt|srt)$/i.test(file.name) || file.size > 1024 * 1024) {
      setError('Escolha uma transcrição TXT, VTT ou SRT com até 1 MB.');
      return;
    }
    try {
      const text = cleanSubtitle(await file.text());
      if (text.length > 200000) throw new Error('A transcrição deve ter até 200.000 caracteres.');
      setDraft(text);
      setError('');
    } catch (err) { setError(err.message || 'Não foi possível ler o arquivo.'); }
  }
  return <>
    <div className="page-heading"><div><span className="eyebrow">CADA CONVERSA, UMA NOVA PERSPECTIVA</span><h1>Vamos entender sua reunião.</h1><p>Transforme a transcrição em sinais, contexto e uma abordagem mais adequada.</p></div><span className="step-pill">01 <span>/</span> Transcrição</span></div>
    <div className="entry-grid">
      <section className="panel transcript-panel"><div className="panel-heading"><div><h2>Transcrição da conversa</h2><p>Cole o texto da reunião ou importe uma transcrição.</p></div><button className="button button-light" onClick={() => fileRef.current?.click()} disabled={busy}><Icon name="upload" size={16} />Importar arquivo</button></div>
        <input ref={fileRef} type="file" accept=".txt,.vtt,.srt" onChange={importFile} className="visually-hidden" aria-label="Importar transcrição" />
        <label htmlFor="transcript-input" className="visually-hidden">Transcrição da reunião</label>
        <textarea id="transcript-input" value={draft} onChange={e => setDraft(e.target.value)} maxLength={200000} disabled={busy} placeholder={'Empresa: nome da empresa\n\nParticipante: Cole aqui as falas da conversa…'} />
        <div className="transcript-footer"><span>{draft.length.toLocaleString('pt-BR')} caracteres · TXT, VTT ou SRT</span><button className="text-button" disabled={busy} onClick={() => { setDraft(EXAMPLE); setError(''); }}>Testar com exemplo fictício</button></div>
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="entry-actions"><button className="button button-primary" onClick={analyze} disabled={busy || !draft.trim()}>{busy ? <><span className="spinner" />Analisando conversa…</> : <><Icon name="spark" size={17} />Analisar reunião<Icon name="arrow" size={16} /></>}</button><small>A análise abre o dashboard. Você escolhe quando salvar no histórico.</small></div>
      </section>
      <aside className="entry-guide"><div className="guide-mark"><Icon name="spark" size={27} /></div><span className="eyebrow">DO TEXTO À LEITURA DE NEGÓCIO</span><h2>Mais contexto.<br />Melhores conversas.</h2><p>Uma leitura dos sinais de relacionamento e das oportunidades presentes no diálogo.</p><div className="process-list">{[['01', 'Sinais da conversa', 'Churn, satisfação, expansão, concorrência e urgência.'], ['02', 'Abordagens possíveis', 'Posturas sugeridas a partir do que foi identificado.'], ['03', 'Um assistente ao lado', 'Pergunte sobre os scores e consulte as evidências.']].map(([n, title, copy]) => <div key={n}><span>{n}</span><div><strong>{title}</strong><p>{copy}</p></div></div>)}</div><div className="guide-note"><Icon name="file" size={16} />O aplicativo analisa texto. Áudio e vídeo devem ser transcritos antes da importação.</div></aside>
    </div>
  </>;
}
