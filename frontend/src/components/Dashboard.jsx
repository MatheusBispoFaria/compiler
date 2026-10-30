import { useState } from 'react';
import Icon from './Icon';
import MeetingChat from './MeetingChat';
import { dateLabel, SIGNALS, tone } from '../lib/analysis';

function Evidence({ items = [] }) {
  if (!items.length) return <p className="no-evidence">Sem trechos específicos para este sinal.</p>;
  return <details className="evidence"><summary>Ver evidências <span>{items.length}</span></summary><ul>{items.map((text, i) => <li key={i}>{text}</li>)}</ul></details>;
}

function Approaches({ items }) {
  const [all, setAll] = useState(false);
  return <section className="panel approaches-panel"><div className="panel-heading"><div><span className="eyebrow">CONTEXTO ANTES DA AÇÃO</span><h2>Abordagens recomendadas</h2></div><span className="square-icon"><Icon name="spark" size={18} /></span></div><p className="panel-description">Possíveis posturas para conduzir a próxima conversa, com base no que foi identificado.</p>
    <div className="approach-list">{(all ? items : items.slice(0, 3)).map((item, index) => <article className={`approach approach-${item.tom}`} key={item.id}><div className="approach-heading"><span className="approach-index">{String(index + 1).padStart(2, '0')}</span><h3>{item.titulo}</h3></div><p>{item.abordagem}</p><details className="approach-context"><summary>Por que esta abordagem?</summary><p>{item.motivo}</p><p className="approach-condition">{item.condicao}</p></details><Evidence items={item.evidencias} /></article>)}</div>
    {items.length > 3 && <button className="button button-light full-width" onClick={() => setAll(!all)}>{all ? 'Mostrar principais' : `Ver todas as ${items.length} abordagens`}<Icon name="chevron" size={14} /></button>}
    <p className="aside-footnote">Orientações de leitura, sujeitas à avaliação de quem acompanha o cliente.</p>
  </section>;
}

export default function Dashboard({ active, title, setTitle, save, saving, edit, error }) {
  const analysis = active.analysis;
  const insights = analysis.insights_ia || {};
  const signals = insights.sinais_negocio || {};
  const satisfaction = Math.min(100, Math.max(0, signals.satisfacao?.score ?? 0));
  const products = insights.produtos_identificados || [];
  const areas = insights.areas_detectadas || [];
  const issues = insights.problemas_detectados || [];
  const approaches = insights.abordagens_recomendadas || [];
  return <>
    <div className="page-heading"><div><span className="eyebrow">LEITURA DA REUNIÃO</span><h1>{analysis.EMPRESA || 'Dashboard da conversa'}</h1><p><span className="inline-dot" />{dateLabel(analysis.analisado_em || active.date)}<span className="meta-divider">/</span>{analysis.cliente_recorrente ? 'Cliente com histórico' : 'Conversa em análise'}</p></div><div className="heading-actions"><button className="button button-light" onClick={edit}><Icon name="file" size={16} />Revisar transcrição</button><span className={`status-pill ${active.savedId ? 'status-saved' : ''}`}><span className="online-dot" />{active.savedId ? 'Salva no histórico' : 'Análise concluída'}</span></div></div>
    <div className="kpi-grid">{SIGNALS.slice(0, 4).map(item => { const signal = signals[item.key] || {}; return <article className={`kpi-card tone-${tone(item.key, signal)}`} key={item.key}><div className="kpi-label"><span className="square-icon"><Icon name={item.icon} size={17} /></span>{item.label}</div><div className="kpi-value">{signal.score ?? 0}<small>/100</small><span className="level-pill">{signal.nivel || 'N/D'}</span></div><p>{signal.evidencias?.length ? `${signal.evidencias.length} trecho(s) associado(s)` : 'Sem evidência específica'}</p></article>; })}</div>
    <p className="score-note">Scores indicativos baseados em regras contextuais. Os valores não representam probabilidades estatísticas.</p>
    {error && <p className="error-message" role="alert">{error}</p>}
    <div className="dashboard-grid"><div className="dashboard-main">
      <div className="charts-grid"><section className="panel signal-overview"><div className="panel-heading"><div><h2>Panorama da conversa</h2><p>Sinais de relacionamento e oportunidade</p></div><span className="subtle-pill">Escala 0–100</span></div><div className="bar-chart">{SIGNALS.map(item => { const signal = signals[item.key] || {}; return <div className={`bar-row tone-${tone(item.key, signal)}`} key={item.key}><span>{item.label}</span><div className="bar-track"><span style={{ width: `${Math.min(100, Math.max(0, signal.score ?? 0))}%` }} /></div><strong>{signal.score ?? 0}</strong></div>; })}</div><div className="chart-legend"><span><i />Índice contextual da conversa</span></div></section>
      <section className="panel perception-panel"><div className="panel-heading"><div><h2>Percepção do cliente</h2><p>Índice de satisfação</p></div></div><div className={`donut-wrap tone-${tone('satisfacao', signals.satisfacao)}`}><svg viewBox="0 0 180 180" role="img" aria-label={`Índice de satisfação: ${satisfaction} de 100`}><circle cx="90" cy="90" r="68" className="donut-track" /><circle cx="90" cy="90" r="68" className="donut-fill" pathLength="100" strokeDasharray={`${satisfaction} ${100 - satisfaction}`} transform="rotate(-90 90 90)" /></svg><div className="donut-value"><strong>{satisfaction}<small>/100</small></strong><span>{signals.satisfacao?.nivel || 'N/D'}</span></div></div><p className="donut-caption">{signals.satisfacao?.motivo}</p></section></div>
      <section className="panel summary-panel"><div className="panel-heading"><div><span className="eyebrow">A CONVERSA EM PERSPECTIVA</span><h2>Resumo executivo</h2></div><span className="subtle-pill">{insights.resumo_fonte === 'openai' ? 'Resumo com IA' : 'Resumo local'}</span></div><p className="executive-summary">{insights.resumo || 'Resumo não disponível para esta reunião salva.'}</p>{insights.leitura_principal?.length > 0 && <div className="reading-list">{insights.leitura_principal.map((item, i) => <p key={i}><span className={`reading-dot reading-${item.tipo}`} />{item.texto}</p>)}</div>}</section>
      <MeetingChat key={active.key} transcript={active.transcript} />
      <section className="panel details-panel"><div className="panel-heading"><div><h2>O contexto por trás dos sinais</h2><p>Informações e evidências identificadas na transcrição</p></div></div><details><summary>Detalhes dos sete indicadores</summary><div className="signal-details-grid">{SIGNALS.map(item => <article key={item.key}><h3>{item.label}<span>{signals[item.key]?.score ?? 0}/100</span></h3><p>{signals[item.key]?.motivo}</p><Evidence items={signals[item.key]?.evidencias} /></article>)}</div></details>
      <details><summary>Produtos, áreas e dificuldades</summary><div className="context-columns"><div><h3>Produtos mencionados</h3>{products.length ? <ul>{products.map((p, i) => <li key={i}>{p.produto}<small>Índice lexical: {p.pontuacao} · {p.confianca}</small></li>)}</ul> : <p>Nenhum produto identificado pelo catálogo.</p>}</div><div><h3>Áreas identificadas</h3>{areas.length ? <ul>{areas.map((a, i) => <li key={i}>{a.area}</li>)}</ul> : <p>Nenhuma área identificada.</p>}<h3>Dificuldades mencionadas</h3><p>{issues.length ? issues.join(' · ') : 'Nenhuma dificuldade detectada pelo catálogo.'}</p></div></div><small className="muted">As menções lexicais dão contexto. As intenções comerciais são analisadas separadamente.</small></details>
      <details><summary>Transcrição utilizada nesta análise</summary><pre className="transcript-view">{active.transcript}</pre></details></section>
      <section className="panel save-panel"><div><h2>Guardar esta perspectiva</h2><p>A transcrição e a análise ficam disponíveis no histórico.</p></div><label className="save-title">Título da reunião<input value={title} onChange={e => setTitle(e.target.value)} maxLength={250} disabled={!!active.savedId} /></label><button className="button button-primary" onClick={save} disabled={saving || !!active.savedId}><Icon name={active.savedId ? 'check' : 'save'} size={16} />{active.savedId ? 'Reunião salva' : saving ? 'Salvando…' : 'Salvar reunião'}</button></section>
    </div><aside className="dashboard-aside"><Approaches key={active.key} items={approaches} /></aside></div>
  </>;
}
