export const SIGNALS = [
  { key: 'churn', label: 'Risco de churn', icon: 'shield' },
  { key: 'satisfacao', label: 'Satisfação', icon: 'heart' },
  { key: 'upsell', label: 'Upsell', icon: 'trend' },
  { key: 'cross_sell', label: 'Cross-sell', icon: 'layers' },
  { key: 'concorrencia', label: 'Concorrência', icon: 'compare' },
  { key: 'urgencia', label: 'Urgência', icon: 'clock' },
  { key: 'risco_oportunidade', label: 'Risco da oportunidade', icon: 'flag' },
];

export function tone(key, signal) {
  const score = signal?.score ?? 0;
  if (key === 'satisfacao') return score >= 70 ? 'positive' : score < 40 ? 'risk' : 'neutral';
  if (['churn', 'concorrencia', 'risco_oportunidade'].includes(key)) return score >= 65 ? 'risk' : score >= 35 ? 'attention' : 'neutral';
  if (key === 'urgencia') return score >= 35 ? 'attention' : 'neutral';
  return score >= 35 ? 'positive' : 'neutral';
}

export function dateLabel(value) {
  if (!value) return 'Reunião atual';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Data não informada' : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(date);
}

export function cleanSubtitle(text) {
  return text.replace(/^\uFEFF/, '').split(/\r?\n/).filter(line =>
    !/^WEBVTT|^\d+$|-->/.test(line.trim())
  ).join('\n').trim();
}

export const EXAMPLE = `Empresa: Grupo Aurora (exemplo fictício)
Consultora: Como está o uso do TOTVS RM na operação?
Cliente: Utilizamos o RM e estamos satisfeitos. O sistema atende bem ao nosso dia a dia.
Consultora: Vocês pretendem ampliar a operação?
Cliente: Vamos abrir duas novas filiais e queremos ampliar as licenças do RM para as novas equipes.
Consultora: E sobre os processos de documentos?
Cliente: Ainda não utilizamos o Fluig. Temos interesse em uma demonstração do Fluig para entender a integração.
Cliente: Antes de decidir, precisamos de respostas sobre os requisitos de integração. Queremos retorno até sexta.
Consultora: Essa avaliação envolve alguma outra solução?
Cliente: Estamos avaliando uma proposta da Senior, mas queremos continuar com a TOTVS se houver aderência aos requisitos.`;
