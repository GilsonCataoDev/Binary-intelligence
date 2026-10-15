# Binary Intelligence AI

Projeto experimental para estudar decisões de opções binárias de 5 minutos. **Fase 9: API e dashboard locais.** Nenhuma fonte ao vivo, conta de corretora ou execução real está conectada. Não há evidência de rentabilidade.

Leia [a pesquisa de plataformas](docs/PLATFORM_RESEARCH.md) antes de escolher uma fonte. O desenho admite Forex, cripto e B3, mas a disponibilidade e o direito de uso dos dados são avaliados por ativo.

## Requisitos no Windows

- Python 3.11 ou posterior, Node.js 20 ou posterior e npm.
- PowerShell no diretório deste projeto.

## Instalar e verificar o motor Python

```powershell
cd services/ai-engine
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m binary_intelligence_ai
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m binary_intelligence_ai.backtesting.demo
.\.venv\Scripts\python.exe -m binary_intelligence_ai.models.demo
```

Se `py -3.11` não estiver disponível, substitua por `python` após conferir `python --version`.

## Instalar e verificar a API Node

```powershell
cd apps/api
npm ci
npm run build
npm run start
```

Defina `API_KEY` conforme `.env.example`. Em outro terminal, `Invoke-RestMethod http://127.0.0.1:3000/api/health` confirma a API; os endpoints `/api/v1` exigem o cabeçalho `x-api-key`.

## Executar o dashboard

```powershell
cd apps/dashboard
npm ci
npm run dev
```

Abra `http://127.0.0.1:5173`; veja `docs/API_AND_DASHBOARD.md`.

## Arquitetura nesta fase

`services/ai-engine` contém o motor quantitativo e de risco. `apps/api` expõe controle e consultas sem duplicar cálculos. `apps/dashboard` é o painel React. `packages/contracts` contém esquemas JSON versionados. PostgreSQL mantém dados e resultados auditáveis.

O arquivo `.env.example` documenta futuras configurações; não contém credenciais ativas. Qualquer execução real permanece fora desta implementação.

## Estado das fases

1. Pesquisa de plataformas: documentação inicial concluída, com verificações contratuais pendentes.
2. Estrutura e ambientes: verificados localmente com importação do pacote, compilação da API e resposta HTTP de saúde.
3. Contratos, validação e persistência: implementados para dados CSV/simulados; veja `docs/DATA_CONTRACTS.md`.
4. Indicadores e regimes: implementados com teste de ausência de vazamento temporal; veja `docs/MARKET_ANALYSIS.md`.
5. Baselines e backtesting: implementados com gap temporal, payout hipotético e métricas; veja `docs/BACKTESTING.md`.
6. Modelos tabulares e calibração: regressão logística, floresta aleatória e boosting avaliados contra o baseline; veja `docs/ML_MODELS.md`.
7. Notícias e eventos: contratos auditáveis, cobertura indisponível explícita e janelas de segurança; veja `docs/NEWS_CONTEXT.md`.
8. Paper trading e risco: decisão determinística, operações idempotentes e limites independentes; veja `docs/PAPER_TRADING_AND_RISK.md`.
9. API e dashboard: endpoints autenticados, estado seguro, logs e painel local; veja `docs/API_AND_DASHBOARD.md`.
10. Próxima fase: monitoramento, testes de falhas e documentação operacional.

## PostgreSQL local opcional

```powershell
cd infrastructure
docker compose up -d
docker compose ps
```

O banco local aplica `postgres/001_market_data.sql` apenas na primeira criação do volume. Os testes automatizados usam banco temporário em memória e não exigem Docker.
