# API e dashboard — Fase 9

## API

A API NestJS usa o prefixo `/api`. `/api/health` é público e informa estado degradado enquanto fontes reais não estiverem configuradas. Todos os endpoints `/api/v1` exigem `x-api-key`, comparado em tempo constante com `API_KEY` do servidor.

A chave precisa ter pelo menos 32 caracteres e não pode ser o valor de exemplo. A API aceita somente origem local nesta versão, aplica headers de segurança, limita requisições e recusa inicialização fora do modo de simulação.

Endpoints implementados:

- `GET /api/v1/status`, `/assets`, `/predictions`, `/news`, `/metrics`, `/paper-trades`, `/models` e `/integrations`;
- `POST /api/v1/analysis/:asset`;
- `POST /api/v1/control/start`, `/pause`, `/stop` e `/emergency-stop`.

Sem fonte autorizada e modelo promovido, análise retorna HTTP 503, decisão `ABSTAIN` e motivos. A API não fabrica resultados. Identificadores de requisição e logs estruturados são emitidos para auditoria.

## Dashboard

O painel React/Vite exibe estado, decisão, qualidade dos dados, notícias, risco, versão do modelo, conexão e execução real desabilitada. A chave local é digitada pelo usuário e fica apenas em `sessionStorage`; ela não é incluída no bundle.

Os controles afetam somente o estado de paper trading. A parada de emergência fica travada e não possui botão de liberação nesta fase.

## Executar no Windows PowerShell

Terminal 1:

```powershell
cd apps/api
$env:API_KEY="uma-chave-local-longa"
npm ci
npm run build
npm run start
```

Terminal 2:

```powershell
cd apps/dashboard
npm ci
npm run dev
```

Abra `http://127.0.0.1:5173` e informe a mesma chave. Credenciais de provedores e banco nunca devem ser colocadas no navegador.

## Limitações

- O estado operacional ainda é mantido em memória pela API e reinicia com o processo.
- A comunicação HTTP com o motor Python será implantada após seu serviço de inferência existir.
- Não há dados ao vivo, modelo promovido ou execução real.
- Perfis de usuário, sessões persistentes e controle granular de papéis ficam pendentes para produção.
