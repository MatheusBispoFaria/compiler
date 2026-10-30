# Compiler-AI

Aplicação independente para transformar transcrições de reuniões em uma leitura de negócio. Reaproveita a análise lexical, os sinais contextuais e o histórico SQLite do projeto anterior, com uma nova interface inspirada na referência visual Workly.

## Usar a aplicação

1. Execute `python api.py` em um terminal.
2. Abra <http://127.0.0.1:5000> no navegador. A interface compilada já está em `frontend/dist`.
3. Cole a transcrição ou importe um arquivo TXT, VTT ou SRT. Também há um exemplo fictício para experimentar.
4. Clique em **Analisar reunião** para abrir o dashboard.
5. Explore os scores, as evidências e as abordagens sugeridas na coluna lateral. O menu lateral inicia recolhido e pode ser expandido pela seta.
6. Use o assistente para perguntar sobre os sinais e os trechos da reunião atual.
7. Se desejar guardar a reunião, preencha o título e clique em **Salvar reunião**. O histórico permite pesquisar, filtrar e reabrir análises.

Esta versão recebe texto já transcrito; não faz reconhecimento de áudio nem se conecta diretamente ao Teams. Analisar uma reunião não a salva automaticamente. A transcrição usada no dashboard permanece vinculada à sua análise, mesmo que o rascunho seja editado depois.

## Sinais e recomendações

O dashboard apresenta sete indicadores de 0 a 100: churn, satisfação, upsell, cross-sell, concorrência, urgência e risco da oportunidade. Eles são índices calculados por regras contextuais, não probabilidades estatísticas nem previsões calibradas. Os trechos de apoio permitem revisar cada interpretação. A ausência de um sinal não comprova a ausência de risco ou de oportunidade.

As recomendações descrevem posturas adequadas aos sinais encontrados: cautelosa, empática, consultiva, exploratória, entre outras. Cada abordagem tem uma justificativa, condições de aplicação e, quando disponíveis, evidências. Quando expansão e insatisfação aparecem juntas, a exploração comercial fica condicionada à recuperação do relacionamento. Apenas citar um produto não é suficiente para recomendar cross-sell.

## Assistente da reunião

O chat funciona localmente, sem chave de serviço. Ele usa regras para explicar os scores, identificar produtos, mostrar evidências e comentar as abordagens da reunião atual. Também entende perguntas de continuidade, como “por quê?”, dentro dos tópicos suportados. Não é um chatbot generativo de uso geral: perguntas fora do contexto recebem uma resposta de limitação. Ele não consulta outras reuniões para responder.

O resumo executivo mantém a integração opcional com o provedor externo que já existia no projeto. Sem chave configurada, há um resumo local. As credenciais permanecem no `.env` do backend. O chat local não usa essa integração. Caso ative o resumo externo, configure no `.env` a chave e um modelo disponível na sua conta; a transcrição será enviada ao provedor para gerar o resumo.

## Instalação e desenvolvimento

Requisitos: Python 3.10+ e, para alterar ou recompilar a interface, Node.js compatível com o Vite instalado no projeto.

```powershell
python -m pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python api.py
```

Para desenvolver com atualização automática, mantenha `python api.py` em um terminal e execute `npm run dev` em `frontend` em outro. Abra o endereço local informado pelo Vite, normalmente <http://localhost:5173>. As chamadas `/api` são encaminhadas ao backend na porta 5000. A variável `COMPILER_PORT` altera a porta do backend; nesse caso, ajuste também o proxy de desenvolvimento.

O servidor de uso local escuta apenas em `127.0.0.1`. O banco existente `reunioes.db` continua sendo utilizado. Registros antigos recebem sinais e abordagens ao serem consultados, sem uma migração destrutiva. `COMPILER_DB_PATH` permite selecionar outro banco, por exemplo para testes.

## Organização

- `api.py`: rotas HTTP, validação e entrega da interface compilada.
- `analysis_service.py`: reúne a análise, os sinais, as abordagens e o resumo.
- `analysis_engine.py`: análise lexical original isolada por requisição.
- `business_signals.py`: regras contextuais para os sete indicadores.
- `approaches.py`: recomendações de abordagem com justificativas e evidências.
- `conversation_assistant.py`: assistente local da reunião.
- `database.py`: persistência e leitura do histórico SQLite.
- `ai_summary.py`: resumo local e integração externa opcional anterior.
- `frontend/src/components`: entrada, dashboard, menu, histórico e chat.
- `frontend/src/lib`: cliente HTTP e apresentação dos sinais.
- `tests/test_compiler.py`: testes de análise, recomendações, chat e persistência.

O fluxo interativo não escreve em arquivos compartilhados de transcrição ou de análise. O comando legado `python script.py` continua disponível para ler `data/transcricao.txt` e gerar `Data.json/dados.json`. O antigo `frontend/public/data.json` não é usado nem incluído na nova compilação.

## Verificação

Na raiz:

```powershell
python -m unittest discover -s tests -v
```

Na pasta `frontend`:

```powershell
npm run lint
npm run build
```

Os testes usam bancos temporários, desativam o resumo externo e não gravam reuniões no histórico real.
