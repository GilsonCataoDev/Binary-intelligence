# Binary Intelligence AI

Projeto experimental para estudar decisões de opções binárias de 5 minutos. **Fase 3: contratos, validação e persistência de dados.** Nenhuma fonte ao vivo, previsão, conta de corretora ou execução real está conectada. Não há evidência de rentabilidade.

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
```

Se `py -3.11` não estiver disponível, substitua por `python` após conferir `python --version`.

## Instalar e verificar a API Node

```powershell
cd apps/api
npm ci
npm run build
npm run start
```

Em outro terminal: `Invoke-RestMethod http://127.0.0.1:3000/health`. A resposta `{"status":"ok","phase":2}` apenas confirma que o esqueleto da API está ativo.

## Arquitetura nesta fase

`services/ai-engine` contém os contratos Pydantic, validadores, provedores CSV/simulado e repositório SQLAlchemy. `apps/api` é o servidor HTTP em NestJS e não calcula sinais. `packages/contracts` contém os esquemas JSON versionados. `docs` registra a pesquisa, convenções e limites de uso. O painel entra em fase posterior.

O arquivo `.env.example` documenta futuras configurações; não contém credenciais ativas. Qualquer execução real permanece fora desta implementação.

## Estado das fases

1. Pesquisa de plataformas: documentação inicial concluída, com verificações contratuais pendentes.
2. Estrutura e ambientes: verificados localmente com importação do pacote, compilação da API e resposta HTTP de saúde.
3. Contratos, validação e persistência: implementados para dados CSV/simulados; veja `docs/DATA_CONTRACTS.md`.
4. Próxima fase: indicadores técnicos e classificação de regimes, usando somente candles encerrados e validados.

## PostgreSQL local opcional

```powershell
cd infrastructure
docker compose up -d
docker compose ps
```

O banco local aplica `postgres/001_market_data.sql` apenas na primeira criação do volume. Os testes automatizados usam banco temporário em memória e não exigem Docker.
