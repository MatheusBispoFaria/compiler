# Publicar o Compiler-AI no Render

A interface React e a API Flask são publicadas em **um único Web Service**. O endereço do serviço entrega o dashboard e as rotas `/api`; não é necessário publicar o frontend separadamente nem configurar CORS.

## Opção 1 — demonstração gratuita

1. Envie os arquivos atualizados deste projeto ao seu repositório no GitHub. A raiz do repositório deve conter `api.py`, `render.yaml`, `requirements.txt`, `frontend/` e `Data.json/dicionario.json`.
2. No Render, escolha **New → Blueprint** e conecte o repositório.
3. Use o caminho padrão `render.yaml`, revise o serviço `compiler-ai` e confirme a criação no Render.
4. Espere o build e o health check terminarem. Abra o endereço `onrender.com` informado pelo Render.
5. Use **Preencher exemplo fictício**, analise a conversa e faça uma pergunta ao assistente. Para conferir a API, abra `/api/health`; a resposta deve indicar `status: ok`.

O Blueprint usa o plano gratuito e grava o SQLite em `/tmp/compiler-ai/reunioes.db`. O histórico permanece disponível enquanto os arquivos da instância existirem, mas **pode ser apagado quando o serviço reiniciar ou for publicado novamente**. Isso também se aplica ao reinício após a suspensão por inatividade do plano gratuito. Não use esse histórico como armazenamento permanente.

## Opção 2 — histórico persistente

Se quiser preservar as reuniões na hospedagem, selecione `deploy/render.persistent.yaml` no campo **Blueprint Path**, em vez de `render.yaml`. Essa configuração utiliza um serviço pago e um disco de 1 GB; confira o custo apresentado pelo Render antes de confirmar.

- Caminho montado: `/var/data`.
- Banco: `/var/data/compiler-ai/reunioes.db`.
- O disco só está disponível durante a execução, não durante o build.
- A aplicação cria a pasta e o schema automaticamente na primeira inicialização.
- O serviço usa uma instância e um worker com threads. Não configure múltiplas instâncias para compartilhar esse SQLite.

Utilize apenas um dos Blueprints para o serviço. O banco local da sua máquina não é enviado nem importado automaticamente; a hospedagem começa com um histórico vazio. Para transferir dados existentes no futuro, use um procedimento explícito de backup e restauração.

## Configuração manual de um Web Service

Se preferir o formulário **New → Web Service**, use:

| Campo | Valor |
| --- | --- |
| Language / Runtime | Python 3 |
| Root Directory | Vazio, se os arquivos estiverem na raiz do repositório |
| Build Command | `bash scripts/render-build.sh` |
| Start Command | `gunicorn --config gunicorn.conf.py api:app` |
| Health Check Path | `/api/health` |
| `COMPILER_ENV` | `production` |
| `COMPILER_DB_PATH` | `/tmp/compiler-ai/reunioes.db`, ou `/var/data/compiler-ai/reunioes.db` com disco persistente |
| `PYTHONUNBUFFERED` | `1` |

As versões são selecionadas por `.python-version` (Python 3.13) e `.node-version` (Node 24.18.0). O Render fornece Node e npm no runtime Python. O Gunicorn utiliza automaticamente a variável `PORT` fornecida pelo Render e escuta em `0.0.0.0`.

Se o projeto estiver dentro de uma pasta de um repositório maior, use essa pasta no campo **Root Directory** e ajuste `rootDir` no Blueprint. A configuração incluída considera este projeto na raiz.

## O que acontece no build

O script `scripts/render-build.sh` instala as dependências Python, instala as dependências JavaScript com `npm ci`, compila a interface e executa os testes. Os testes usam bancos temporários e não precisam do disco persistente ou de uma chave de IA. Se alguma etapa falhar, o build termina com erro.

O frontend não inclui `frontend/public/data.json`. As transcrições e análises são recebidas pela API, e as respostas dessas rotas não devem ser armazenadas em cache.

## Resumo externo opcional

O dashboard, os scores e o assistente local funcionam sem credenciais. Para ativar a integração de resumo externo já existente, cadastre **ambas** as variáveis no painel Environment do Render:

- `OPENAI_API_KEY`: sua chave, cadastrada como segredo no Render.
- `OPENAI_MODEL`: um modelo disponível na sua conta e compatível com a integração existente.

Não coloque essas informações no YAML, no frontend ou no GitHub. Se ativar a integração, a transcrição será enviada ao provedor para gerar o resumo. Essa integração externa não faz parte da validação automatizada do deploy.

## Dados e acesso

Esta aplicação usa um workspace compartilhado e ainda não possui contas ou isolamento de histórico por usuário. Quem acessar a instância poderá consultar as reuniões salvas nela. Para uma demonstração pública de portfólio, utilize conversas fictícias.

O `.gitignore` exclui credenciais, bancos e arquivos de transcrição gerados. Se algum desses arquivos já estiver versionado no seu repositório, o Git continuará rastreando-o até que ele seja removido do índice; apenas editar o `.gitignore` não remove arquivos já enviados.

## Se algo falhar

- **Build falhou:** consulte a etapa indicada nos logs. Confirme que `frontend/package-lock.json` e `Data.json/dicionario.json` foram enviados ao GitHub.
- **Interface indisponível / `frontend_missing`:** confira se o build compilou `frontend/dist/index.html` e se o diretório raiz está correto.
- **`database_unavailable`:** confira `COMPILER_DB_PATH` e, na opção persistente, o disco montado em `/var/data`.
- **Porta não detectada:** use o comando Gunicorn informado acima; `start.bat` e `python api.py` são para desenvolvimento local.
- **Histórico apagou:** confira se usou a opção gratuita sem disco. Dados do SQLite temporário não são recuperados pelo código.

## Referências

- [Flask no Render](https://render.com/docs/deploy-flask)
- [Web Services e porta do serviço](https://render.com/docs/web-services)
- [Discos persistentes](https://render.com/docs/disks)
- [Referência de Blueprints](https://render.com/docs/blueprint-spec)
- [Versão do Python](https://render.com/docs/python-version)
- [Versão do Node.js](https://render.com/docs/node-version)
- [Ferramentas disponíveis no runtime](https://render.com/docs/native-runtimes)
