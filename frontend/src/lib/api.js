export async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error('Não foi possível acessar o serviço de análise. Verifique se ele está em execução.');
  }
  if (!response.ok) throw new Error(data.erro || 'Não foi possível concluir a solicitação.');
  return data;
}

export function post(path, body) {
  return request(path, { method: 'POST', body: JSON.stringify(body) });
}
