import { useEffect, useRef, useState } from 'react';
import { post } from '../lib/api';
import Icon from './Icon';

const PROMPTS = ['Qual abordagem combina com esta conversa?', 'Explique o risco de churn', 'Quais são as evidências?'];

export default function MeetingChat({ transcript }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef(null);
  useEffect(() => { if (messages.length) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [messages]);

  async function send(text = question) {
    if (!text.trim() || pending) return;
    setPending(true); setError(''); setQuestion('');
    const history = messages.slice(-12);
    setMessages(current => [...current, { role: 'user', content: text.trim() }]);
    try {
      const answer = await post('/api/chat', { pergunta: text.trim(), transcricao: transcript, historico: history });
      setMessages(current => [...current, { role: 'assistant', content: answer.resposta, evidencias: answer.evidencias, topico: answer.topico }]);
    } catch (err) { setError(err.message); setQuestion(text); }
    finally { setPending(false); }
  }
  return <section className="panel chat-panel" id="meeting-assistant"><div className="panel-heading"><div className="chat-title"><span className="assistant-avatar"><Icon name="spark" size={18} /></span><div><h2>Assistente da reunião</h2><p>Explore os sinais e as evidências da reunião.</p></div></div><span className="status-pill"><span className="online-dot" />Assistente local</span></div>
    <div className="chat-conversation" aria-live="polite" aria-label="Conversa com o assistente">
      {!messages.length && <div className="chat-welcome"><h3>O que você gostaria de explorar?</h3><p>Posso explicar os scores, mostrar trechos da transcrição e comentar as abordagens sugeridas.</p></div>}
      {messages.map((message, index) => <div key={index} className={`chat-message message-${message.role}`}><span className="message-author">{message.role === 'user' ? 'Você' : 'Compiler Assistente'}</span><p>{message.content}</p>{message.evidencias?.length > 0 && <details><summary>Trechos que sustentam a resposta</summary><ul>{message.evidencias.map((text, i) => <li key={i}>{text}</li>)}</ul></details>}</div>)}
      {pending && <div className="chat-pending"><span className="spinner" />Consultando a análise da reunião…</div>}<div ref={endRef} />
    </div>
    <div className="chat-suggestions">{PROMPTS.map(prompt => <button key={prompt} onClick={() => send(prompt)} disabled={pending}>{prompt}<Icon name="arrow" size={12} /></button>)}</div>
    {error && <p role="alert" className="error-message">{error}</p>}
    <form className="chat-input" onSubmit={e => { e.preventDefault(); send(); }}><input value={question} onChange={e => setQuestion(e.target.value)} maxLength={2000} placeholder="Pergunte sobre esta reunião…" aria-label="Pergunta ao assistente" disabled={pending} /><button type="submit" className="button button-primary" disabled={pending || !question.trim()} aria-label="Enviar pergunta"><Icon name="send" size={17} /></button></form>
    <p className="chat-footnote">Consulta local baseada nos dados e nas regras da análise. Respostas limitadas a esta reunião.</p>
  </section>;
}
