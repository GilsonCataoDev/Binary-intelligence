# Contratos e persistência de dados — Fase 3

## Convenções

- Todos os horários incluem fuso e são normalizados para UTC.
- O candle representa `[open_time, close_time)` e sua duração deve corresponder ao timeframe.
- Apenas candles encerrados podem ser considerados válidos para análise.
- OHLC usa decimal positivo. `high` contém abertura e fechamento; `low` não os excede.
- `volume` é opcional. Ausência permanece `null`; nenhum volume é inventado.
- A identidade persistida é `(source, asset, timeframe, open_time)`; reingestão é idempotente.

## Qualidade e decisão

O validador não ordena, preenche ou corrige silenciosamente a série. Duplicata, lacuna, ordem inválida, mistura de séries ou candle aberto produzem `invalid`. Série vazia ou último candle além do limite configurado produz `stale`. Qualquer estado diferente de `valid` deve resultar em **ABSTER-SE** nas fases de decisão.

Validações de tipo, preço, duração e timezone acontecem ao criar cada candle. O relatório de lote verifica relações temporais entre candles.

## Fontes disponíveis nesta fase

- `CsvCandleProvider`: lê arquivo histórico reproduzível com colunas explícitas.
- `SimulatedCandleProvider`: gera uma série determinística para desenvolvimento. A fonte é marcada `SIMULATED` e não pode ser apresentada como mercado real.
- Nenhum adaptador de corretora ou mercado ao vivo está implementado.

## Persistência e retenção

PostgreSQL armazena candles normalizados para reprodução de previsões. O SQL inicial está em `infrastructure/postgres/001_market_data.sql`. A aplicação também tem um repositório SQLAlchemy, testável sem servidor externo.

Antes de persistir dados de uma fonte real, registrar licença, finalidade autorizada, prazo de retenção e política de exclusão. Dados B3 permanecem bloqueados para treino até confirmação contratual. Dados brutos volumosos deverão usar armazenamento próprio em fase posterior; o banco relacional não será depósito indiscriminado.
