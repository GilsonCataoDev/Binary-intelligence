# API e dashboard — Fase 9

## API

A API NestJS usa o prefixo `/api`. `/api/health` é público e informa estado degradado enquanto fontes reais não estiverem configuradas. Todos os endpoints `/api/v1` exigem `x-api-key`, comparado em tempo constante com `API_KEY` do servidor.

A chave precisa ter pelo menos 32 caracteres e não pode ser o valor de exemplo. A API aceita somente origem local nesta versão, aplica headers de segurança, limita requisições e recusa inicialização fora do modo de simulação.

Endpoints implementados:

- `GET /api/v1/status`, `/assets`, `/predictions`, `/news`, `/metrics`, `/paper-trades`, `/models` e `/integrations`;
- `POST /api/v1/analysis/:asset`;
- `POST /api/v1/control/start`, `/pause`, `/stop` e `/emergency-stop`.

`POST /api/v1/analysis/:asset` busca 100 candles M5 públicos e transitórios da Deriv, descarta explicitamente o candle ainda em formação (informado em `input.openCandlesDiscarded`) e envia a série ao motor Python. O motor valida qualidade, calcula indicadores e regime e devolve `result_type: "analysis_only"`. A decisão é sempre `ABSTAIN` nesta versão, com motivos: dados públicos transitórios não são aprovados para inferência e nenhum modelo passou pela promoção controlada. A API também rejeita qualquer resposta do motor que não seja `ABSTAIN`.

Sem `ENGINE_TOKEN` configurado, ou com o motor inacessível, a análise retorna HTTP 503 e `ABSTAIN`. A API não fabrica resultados. `GET /api/v1/predictions` lista as últimas 20 análises mantidas em memória. Identificadores de requisição e logs estruturados são emitidos para auditoria.

## Motor Python (serviço HTTP local)

`python -m binary_intelligence_ai.service` expõe `GET /health` (público) e `POST /v1/analysis` (exige `x-engine-token`, comparado em tempo constante). Usa apenas a biblioteca padrão, recusa host fora do loopback, token com menos de 32 caracteres, `EXECUTION_MODE` diferente de `simulation` e `REAL_EXECUTION_ENABLED` diferente de `false`. Corpo limitado a 512 KB e 1000 candles; campos desconhecidos são rejeitados.

## Dashboard

O painel React/Vite exibe estado, decisão com motivos, regime e volatilidade, qualidade dos dados, estado do motor, notícias, risco, versão do modelo, análises recentes e execução real desabilitada. Um campo permite analisar um símbolo Deriv (ex.: `frxEURUSD`). A URL da API pode ser alterada com `VITE_API_URL`. A chave local é digitada pelo usuário e fica apenas em `sessionStorage`; ela não é incluída no bundle.

Os controles afetam somente o estado de paper trading. A parada de emergência fica travada e não possui botão de liberação nesta fase.

## Executar no Windows PowerShell

Gere uma vez, no mesmo terminal, segredos aleatórios para a API e para o motor:

```powershell
$env:API_KEY = -join ((1..48) | ForEach-Object { [char](Get-Random -Minimum 65 -Maximum 91) })
$env:ENGINE_TOKEN = -join ((1..48) | ForEach-Object { [char](Get-Random -Minimum 65 -Maximum 91) })
```

Terminal 1 (motor; precisa do mesmo `ENGINE_TOKEN`):

```powershell
cd services/ai-engine
.\.venv\Scripts\python.exe -m binary_intelligence_ai.service
```

Terminal 2 (API; mesmos `API_KEY` e `ENGINE_TOKEN`):

```powershell
cd apps/api
npm ci
npm run build
npm run start
```

Terminal 3:

```powershell
cd apps/dashboard
npm ci
npm run dev
```

Abra `http://127.0.0.1:5173` e informe a mesma chave. Credenciais de provedores e banco nunca devem ser colocadas no navegador.

## Limitações

- O estado operacional e as análises recentes ainda são mantidos em memória pela API e reiniciam com o processo; não há reconciliação com o PostgreSQL.
- O motor analisa qualidade e regime, mas não executa modelo: o registro de modelos do serviço começa vazio e não há caminho de inferência revisado ligado à decisão.
- Dados públicos da Deriv são transitórios (cache máximo de 24 h pelos termos); não são persistidos nem usados para treino.
- Não há modelo promovido, payout validado nem execução real.
- Perfis de usuário, sessões persistentes e controle granular de papéis ficam pendentes para produção.
